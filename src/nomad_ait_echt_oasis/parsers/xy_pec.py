import os
import re
from datetime import datetime
from typing import TYPE_CHECKING

import h5py
import numpy as np
from nomad.datamodel.metainfo.basesections import (
    CompositeSystemReference,
)
from nomad.parsing.parser import MatchingParser
from nomad.units import ureg
from nomad_measurements.mapping.schema import RectangularSampleAlignment

from nomad_ait_echt_oasis.normalizers.electrochemical_characterization import (
    STANDARD_REFERENCE_POTENTIALS_VS_RHE,
    normalize_cv_result,
    normalize_ecsa_result,
)
from nomad_ait_echt_oasis.schema_packages.electrochemical_characterization import (
    CVMappingResult,
    CVResult,
    ECSAMappingResult,
    ElectrochemicalMapping,
    Electrolyte,
    ReferenceElectrode,
    ThreeElectrodeCell,
    WorkingElectrode,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger


def _decode_val(val):
    """Safely decode byte strings and numpy scalars to Python types."""
    if isinstance(val, bytes):
        return val.decode('utf-8', errors='ignore')
    if hasattr(val, 'item') and hasattr(val, 'shape') and val.shape == ():
        val = val.item()
    if isinstance(val, bytes):
        return val.decode('utf-8', errors='ignore')
    return val


def _extract_legacy_var(grp, candidate_keys):
    """Extract variable from signal group with fallback candidate keys."""
    if grp is None:
        return None
    for key in candidate_keys:
        if key in grp:
            item = grp[key]
            if item.size > 0:
                val = item[0]
                return _decode_val(val)
    return None


class XYPECParser(MatchingParser):
    """
    Parser for NOMAD CAMELS measurement files from the XY-PEC instrument.
    Parses spatial screening loop procedures comprising cyclic voltammetry (CV)
    and electrochemically active surface area (ECSA) scan rate series at mapped points.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._mainfile_name_re = re.compile(r'^.*\.(h5|hdf5|nxs)$')

    def is_mainfile(
        self,
        filename: str,
        mime: str,
        buffer: bytes,
        decoded_buffer: str,
        compression: str = None,
    ) -> bool:
        if not filename.endswith(('.h5', '.hdf5')):
            return False
        try:
            with h5py.File(filename, 'r') as f:
                if 'CAMELS_entry' not in f:
                    return False
                entry = f['CAMELS_entry']
                has_inst = 'instruments' in entry and 'xy_pec' in entry['instruments']
                has_pn = False
                has_po = False
                if 'measurement_details' in entry:
                    md = entry['measurement_details']
                    if 'plan_name' in md:
                        pn = _decode_val(md['plan_name'][()]) or ''
                        has_pn = 'xy_pec' in pn.lower() or 'screeningloop' in pn.lower()
                    if 'protocol_overview' in md:
                        po = _decode_val(md['protocol_overview'][()]) or ''
                        has_po = 'xy_pec' in po
                return has_inst or has_pn or has_po
        except Exception:
            return False

    def _parse_metadata(
        self, entry: h5py.Group, data: ElectrochemicalMapping
    ) -> CompositeSystemReference | None:
        """Parse datetime, description, and sample reference."""
        if 'measurement_details' in entry:
            md = entry['measurement_details']
            if 'start_time' in md:
                st_str = _decode_val(md['start_time'][()])
                try:
                    data.datetime = datetime.fromisoformat(st_str)
                except Exception:
                    pass
            if 'measurement_description' in md:
                desc = _decode_val(md['measurement_description'][()])
                if desc:
                    data.description = str(desc)

        sample_name = None
        if 'sample' in entry:
            s_grp = entry['sample']
            if 'name' in s_grp:
                sample_name = _decode_val(s_grp['name'][()])
            elif 'sample_id' in s_grp:
                sample_name = _decode_val(s_grp['sample_id'][()])

        sample_ref = (
            CompositeSystemReference(name=str(sample_name)) if sample_name else None
        )
        if sample_ref:
            data.samples = [sample_ref]
        return sample_ref

    def _parse_cell_and_alignment(
        self,
        entry: h5py.Group,
        data: ElectrochemicalMapping,
        sample_ref: CompositeSystemReference | None,
    ) -> None:
        """Parse electrochemical cell, electrolyte, and sample geometry."""
        cell = data.cell if data.cell is not None else ThreeElectrodeCell()
        if cell.working_electrode is None:
            cell.working_electrode = WorkingElectrode(sample=sample_ref)
        elif sample_ref and cell.working_electrode.sample is None:
            cell.working_electrode.sample = sample_ref
        if cell.reference_electrode is None:
            cell.reference_electrode = ReferenceElectrode()

        sample_size_x = None
        sample_size_y = None
        if 'data' in entry and 'ScreeningLoop_variable_signal' in entry['data']:
            sl_sig = entry['data']['ScreeningLoop_variable_signal']
            if 'electrolyte' in sl_sig and sl_sig['electrolyte'].size > 0:
                el_desc = _decode_val(sl_sig['electrolyte'][0])
                if el_desc:
                    cell.electrolyte = cell.electrolyte or Electrolyte()
                    cell.electrolyte.description = str(el_desc)
            if 'ph_value' in sl_sig and sl_sig['ph_value'].size > 0:
                cell.electrolyte = cell.electrolyte or Electrolyte()
                cell.electrolyte.ph_value = float(sl_sig['ph_value'][0])
            if 'sample_size_x' in sl_sig and sl_sig['sample_size_x'].size > 0:
                sample_size_x = float(sl_sig['sample_size_x'][0])
            if 'sample_size_y' in sl_sig and sl_sig['sample_size_y'].size > 0:
                sample_size_y = float(sl_sig['sample_size_y'][0])

        if sample_size_x is not None and sample_size_y is not None:
            data.sample_alignment = RectangularSampleAlignment(
                width=sample_size_x * ureg.millimeter,
                height=sample_size_y * ureg.millimeter,
            )

        data.cell = cell

    def _parse_cv_step(
        self, sub: h5py.Group, result_cls: type[CVResult] = CVResult
    ) -> CVResult | None:
        """Parse single-point standard cyclic voltammetry dataset."""
        if 'Subprotocol_CyclicVoltammetry' not in sub:
            return None
        cv_grp = sub['Subprotocol_CyclicVoltammetry']
        if (
            'matterlab_potentiostat_read_potential' not in cv_grp
            or 'matterlab_potentiostat_read_current' not in cv_grp
        ):
            return None

        v_arr = np.asarray(
            cv_grp['matterlab_potentiostat_read_potential'][()], dtype=float
        )
        i_arr = np.asarray(
            cv_grp['matterlab_potentiostat_read_current'][()], dtype=float
        )
        t_arr = None
        if 'time' in cv_grp:
            t_arr = np.asarray(cv_grp['time'][()], dtype=float)
        elif 'ElapsedTime' in cv_grp:
            t_arr = np.asarray(cv_grp['ElapsedTime'][()], dtype=float)

        sr_mv = None
        if 'CyclicVoltammetryLegacy_variable_signal' in cv_grp:
            cv_sig = cv_grp['CyclicVoltammetryLegacy_variable_signal']
            if 'scan_rate_mvpers' in cv_sig and cv_sig['scan_rate_mvpers'].size > 0:
                sr_mv = float(cv_sig['scan_rate_mvpers'][0])

        cv_res = result_cls(
            name='Cyclic Voltammetry',
            potential=v_arr * ureg.volt,
            current=i_arr * ureg.ampere,
        )
        if t_arr is not None:
            cv_res.time = t_arr * ureg.second
        if sr_mv is not None:
            cv_res.scan_rate = sr_mv * (ureg.millivolt / ureg.second)

        return cv_res

    def _parse_ecsa_step(
        self, sub: h5py.Group, result_cls: type[ECSAMappingResult] = ECSAMappingResult
    ) -> ECSAMappingResult | None:
        """Parse ECSA scan rate series into an ECSAMappingResult."""
        if 'Subprotocol_ECSA' not in sub:
            return None
        ecsa_grp = sub['Subprotocol_ECSA']
        run_keys = [k for k in ecsa_grp.keys() if isinstance(ecsa_grp[k], h5py.Group)]
        run_keys.sort(
            key=lambda k: (
                int(re.search(r'\d+', k).group()) if re.search(r'\d+', k) else 0
            )
        )

        ecsa_res = result_cls(name='ECSA')
        for r_k in run_keys:
            r_grp = ecsa_grp[r_k]
            if (
                'matterlab_potentiostat_read_potential' not in r_grp
                or 'matterlab_potentiostat_read_current' not in r_grp
            ):
                continue

            v_r = np.asarray(
                r_grp['matterlab_potentiostat_read_potential'][()], dtype=float
            )
            i_r = np.asarray(
                r_grp['matterlab_potentiostat_read_current'][()], dtype=float
            )
            t_r = None
            if 'time' in r_grp:
                t_r = np.asarray(r_grp['time'][()], dtype=float)
            elif 'ElapsedTime' in r_grp:
                t_r = np.asarray(r_grp['ElapsedTime'][()], dtype=float)

            sr_r = None
            if 'CyclicVoltammetryLegacy_variable_signal' in r_grp:
                r_sig = r_grp['CyclicVoltammetryLegacy_variable_signal']
                if 'scan_rate_mvpers' in r_sig and r_sig['scan_rate_mvpers'].size > 0:
                    sr_r = float(r_sig['scan_rate_mvpers'][0])

            run_name = f'ECSA {sr_r:.0f} mV/s' if sr_r is not None else r_k
            run_cv = CVResult(
                name=run_name,
                potential=v_r * ureg.volt,
                current=i_r * ureg.ampere,
            )
            if t_r is not None:
                run_cv.time = t_r * ureg.second
            if sr_r is not None:
                run_cv.scan_rate = sr_r * (ureg.millivolt / ureg.second)

            ecsa_res.runs.append(run_cv)

        return ecsa_res

    def _check_signal_fallbacks(
        self,
        sub: h5py.Group,
        data: ElectrochemicalMapping,
        surface_area_found: bool,
        ref_type_found: bool,
    ) -> tuple[bool, bool]:
        """Check CV variable signal for electrode area and reference type fallbacks."""
        cv_sig = None
        if 'Subprotocol_CyclicVoltammetry' in sub:
            cv_grp = sub['Subprotocol_CyclicVoltammetry']
            if 'CyclicVoltammetryLegacy_variable_signal' in cv_grp:
                cv_sig = cv_grp['CyclicVoltammetryLegacy_variable_signal']

        if cv_sig is not None and data.cell:
            if not surface_area_found and data.cell.working_electrode:
                area_val = _extract_legacy_var(
                    cv_sig,
                    ['electrode_area', 'surface_area', 'droplet_area', 'area'],
                )
                if area_val is not None:
                    try:
                        data.cell.working_electrode.surface_area = float(area_val) * (
                            ureg.centimeter**2
                        )
                        surface_area_found = True
                    except Exception:
                        pass

            if not ref_type_found and data.cell.reference_electrode:
                ref_val = _extract_legacy_var(
                    cv_sig,
                    [
                        'reference_electrode',
                        'reference_type',
                        'ref_electrode',
                        'reference_standard',
                    ],
                )
                if ref_val is not None:
                    ref_str = str(ref_val)
                    data.cell.reference_electrode.reference_type = ref_str
                    if ref_str in STANDARD_REFERENCE_POTENTIALS_VS_RHE:
                        data.cell.reference_electrode.standard_potential_vs_rhe = (
                            STANDARD_REFERENCE_POTENTIALS_VS_RHE[ref_str] * ureg.volt
                        )
                    ref_type_found = True

        return surface_area_found, ref_type_found

    def parse(  # noqa: PLR0912, PLR0915
        self,
        mainfile: str,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
        child_archives: dict[str, 'EntryArchive'] = None,
    ) -> None:
        logger.info('Parsing XY-PEC CAMELS measurement file', mainfile=mainfile)

        if archive.metadata is None:
            from nomad.datamodel import EntryMetadata

            archive.metadata = EntryMetadata()

        data = (
            archive.data
            if isinstance(archive.data, ElectrochemicalMapping)
            else ElectrochemicalMapping()
        )
        if not data.name:
            data.name = os.path.splitext(os.path.basename(mainfile))[0]

        with h5py.File(mainfile, 'r') as hdf:
            if 'CAMELS_entry' not in hdf:
                logger.warning('No CAMELS_entry group found in HDF5 file.')
                archive.data = data
                return

            entry = hdf['CAMELS_entry']
            sample_ref = self._parse_metadata(entry, data)
            self._parse_cell_and_alignment(entry, data, sample_ref)

            if 'data' not in entry or 'primary' not in entry['data']:
                logger.warning('No primary data group found in CAMELS entry.')
                archive.data = data
                return

            primary_grp = entry['data']['primary']
            subprotocol_keys = [
                k
                for k in primary_grp.keys()
                if k.startswith('Subprotocol_RunSubprotocol_')
            ]
            subprotocol_keys.sort(
                key=lambda k: (
                    int(re.search(r'\d+', k).group()) if re.search(r'\d+', k) else 0
                )
            )

            surface_area_found = False
            ref_type_found = False

            surface_area_val = None
            if (
                data.cell
                and data.cell.working_electrode
                and data.cell.working_electrode.surface_area
            ):
                surface_area_val = data.cell.working_electrode.surface_area.to(
                    'centimeter ** 2'
                ).magnitude

            ref_potential_rhe = None
            if (
                data.cell
                and data.cell.reference_electrode
                and data.cell.reference_electrode.standard_potential_vs_rhe
            ):
                ref_potential_rhe = (
                    data.cell.reference_electrode.standard_potential_vs_rhe.to(
                        'volt'
                    ).magnitude
                )

            ph_val = None
            if (
                data.cell
                and data.cell.electrolyte
                and data.cell.electrolyte.ph_value is not None
            ):
                ph_val = float(data.cell.electrolyte.ph_value)

            for sub_key in subprotocol_keys:
                sub = primary_grp[sub_key]
                surface_area_found, ref_type_found = self._check_signal_fallbacks(
                    sub, data, surface_area_found, ref_type_found
                )
                if (
                    surface_area_val is None
                    and data.cell
                    and data.cell.working_electrode
                    and data.cell.working_electrode.surface_area
                ):
                    surface_area_val = data.cell.working_electrode.surface_area.to(
                        'centimeter ** 2'
                    ).magnitude
                if (
                    ref_potential_rhe is None
                    and data.cell
                    and data.cell.reference_electrode
                ):
                    ref = data.cell.reference_electrode
                    if ref.standard_potential_vs_rhe is not None:
                        ref_potential_rhe = ref.standard_potential_vs_rhe.to(
                            'volt'
                        ).magnitude
                    elif ref.reference_type in STANDARD_REFERENCE_POTENTIALS_VS_RHE:
                        ref_potential_rhe = STANDARD_REFERENCE_POTENTIALS_VS_RHE[
                            ref.reference_type
                        ]

                pos_x = 0.0
                pos_y = 0.0
                pos_idx = len(data.results)
                if 'SinglePointCVfromReservoir_variable_signal' in sub:
                    sp_sig = sub['SinglePointCVfromReservoir_variable_signal']
                    if 'position_x' in sp_sig and sp_sig['position_x'].size > 0:
                        pos_x = float(sp_sig['position_x'][0])
                    if 'position_y' in sp_sig and sp_sig['position_y'].size > 0:
                        pos_y = float(sp_sig['position_y'][0])
                    if 'position_index' in sp_sig and sp_sig['position_index'].size > 0:
                        pos_idx = int(sp_sig['position_index'][0])

                cv_mapping = self._parse_cv_step(sub, result_cls=CVMappingResult)
                if cv_mapping is not None:
                    cv_mapping.name = f'CV Point {pos_idx}'
                    cv_mapping.point_index = pos_idx
                    cv_mapping.x_absolute = pos_x * ureg.millimeter
                    cv_mapping.y_absolute = pos_y * ureg.millimeter
                    normalize_cv_result(
                        cv_mapping,
                        cell=data.cell,
                        surface_area_val=surface_area_val,
                        ref_potential_rhe=ref_potential_rhe,
                        ph_val=ph_val,
                    )
                    data.results.append(cv_mapping)

                ecsa_mapping = self._parse_ecsa_step(sub, result_cls=ECSAMappingResult)
                if ecsa_mapping is not None:
                    ecsa_mapping.name = f'ECSA Point {pos_idx}'
                    ecsa_mapping.point_index = pos_idx
                    ecsa_mapping.x_absolute = pos_x * ureg.millimeter
                    ecsa_mapping.y_absolute = pos_y * ureg.millimeter
                    normalize_ecsa_result(
                        ecsa_mapping,
                        cell=data.cell,
                        surface_area_val=surface_area_val,
                        ref_potential_rhe=ref_potential_rhe,
                        ph_val=ph_val,
                    )
                    data.results.append(ecsa_mapping)

        archive.data = data
        logger.info(
            'XY-PEC measurement parsed successfully',
            n_points=len(data.results),
        )
