import os
import re
from datetime import datetime
from typing import TYPE_CHECKING

import h5py
import numpy as np
from nomad.datamodel.metainfo.basesections import (
    CompositeSystemReference,
    InstrumentReference,
)
from nomad.parsing.parser import MatchingParser
from nomad.units import ureg
from nomad_measurements.mapping.schema import RectangularSampleAlignment

from nomad_ait_echt_oasis.schema_packages.electrochemical_characterization import (
    CounterElectrode,
    CVParameter,
    CVResult,
    CyclicVoltammetry,
    ECSAMeasurement,
    ECSAParameter,
    ECSAResult,
    ElectrochemicalMapping,
    ElectrochemicalMappingStep,
    ElectrochemicalMeasurement,
    Electrolyte,
    ReferenceElectrode,
    ThreeElectrodeCell,
    WorkingElectrode,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger


def _decode_val(val):
    """Safely decode byte strings, numpy scalars, and 1D arrays to Python types."""
    if isinstance(val, bytes):
        return val.decode('utf-8', errors='ignore')
    if hasattr(val, 'size') and val.size == 1:
        val = val.item()
        if isinstance(val, bytes):
            return val.decode('utf-8', errors='ignore')
        return val
    if isinstance(val, (np.ndarray, list)):
        return [_decode_val(v) for v in val]
    return val


def _decode_scalar(val, default=None):
    """Safely decode byte strings and numpy arrays/scalars to a single Python scalar."""
    if val is None:
        return default
    decoded = _decode_val(val)
    if isinstance(decoded, list):
        return decoded[0] if decoded else default
    return decoded if decoded is not None else default


def _extract_legacy_var(grp, candidate_keys):
    """Extract variable from signal group with fallback candidate keys."""
    if grp is None:
        return None
    for key in candidate_keys:
        if key in grp:
            item = grp[key]
            if item.size > 0:
                val = _decode_val(item[()])
                return val
    return None


class XYPECParser(MatchingParser):
    """
    Parser for NOMAD CAMELS measurement files from the XY-PEC instrument.
    Parses spatial screening loop procedures comprising cyclic voltammetry (CV)
    and electrochemically active surface area (ECSA) scan rate series at mapped points.
    """

    creates_children = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._mainfile_name_re = re.compile(r'^.*\.(h5|hdf5|nxs)$')
        self.child_archives = None

    def _get_subprotocol_keys(self, primary_grp: h5py.Group) -> list[str]:
        """
        Extract and numerically sort all subprotocol group keys from primary.
        """
        subprotocol_keys = [
            k for k in primary_grp.keys() if k.startswith('Subprotocol_RunSubprotocol_')
        ]
        subprotocol_keys.sort(
            key=lambda k: (
                int(re.search(r'\d+', k).group()) if re.search(r'\d+', k) else 0
            )
        )
        return subprotocol_keys

    def is_mainfile(
        self,
        filename: str,
        mime: str,
        buffer: bytes,
        decoded_buffer: str,
        compression: str = None,
    ) -> bool | list[str]:
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
                if not (has_inst or has_pn or has_po):
                    return False

                if 'data' not in entry or 'primary' not in entry['data']:
                    return True

                primary_grp = entry['data']['primary']
                subprotocol_keys = self._get_subprotocol_keys(primary_grp)

                child_keys = []
                for sub_key in subprotocol_keys:
                    sub = primary_grp[sub_key]
                    if not any(k.endswith('_variable_signal') for k in sub.keys()):
                        continue
                    if 'Subprotocol_CyclicVoltammetry' in sub:
                        child_keys.append(f'{sub_key}/CyclicVoltammetry')
                    if 'Subprotocol_ECSA' in sub:
                        child_keys.append(f'{sub_key}/ECSAMeasurement')

                return child_keys if child_keys else True
        except Exception:
            return False

    def _parse_metadata(  # noqa: PLR0912
        self,
        entry: h5py.Group,
        data: ElectrochemicalMapping,
    ) -> CompositeSystemReference | None:
        """
        Parse datetime, description, sample reference, and instruments.
        """
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

        if 'sample' in entry:
            s_grp = entry['sample']
            sample_ref = CompositeSystemReference()
            if 'name' in s_grp:
                sample_ref.name = _decode_scalar(s_grp['name'][()])
            if 'sample_id' in s_grp:
                sample_ref.lab_id = _decode_scalar(s_grp['sample_id'][()])
            if not sample_ref.name and sample_ref.lab_id:
                sample_ref.name = sample_ref.lab_id
            if sample_ref.name or sample_ref.lab_id:
                data.samples = [sample_ref]

        instruments = []
        if 'instruments' in entry:
            for inst_name in entry['instruments']:
                inst_grp = entry['instruments'][inst_name]
                inst_ref = InstrumentReference(name=inst_name)
                if 'name' in inst_grp:
                    inst_ref.name = _decode_val(inst_grp['name'][()])
                if 'ELN-instrument-id' in inst_grp:
                    inst_ref.lab_id = _decode_val(inst_grp['ELN-instrument-id'][()])

                instruments.append(inst_ref)
        data.instruments = instruments

    def _parse_alignment(
        self,
        sl_var: h5py.Group,
        data: ElectrochemicalMapping,
    ) -> None:
        """Parse sample geometry."""
        if 'sample_shape' not in sl_var:
            return

        sample_shape = _decode_scalar(sl_var['sample_shape'][()])

        if sample_shape == 'rectangle':
            sample_size_x = None
            sample_size_y = None
            if 'sample_size_x' in sl_var and sl_var['sample_size_x'].size > 0:
                sx = _decode_scalar(sl_var['sample_size_x'][()])
                if sx is not None:
                    sample_size_x = float(sx)
            if 'sample_size_y' in sl_var and sl_var['sample_size_y'].size > 0:
                sy = _decode_scalar(sl_var['sample_size_y'][()])
                if sy is not None:
                    sample_size_y = float(sy)

            if sample_size_x is not None and sample_size_y is not None:
                data.sample_alignment = RectangularSampleAlignment(
                    width=sample_size_x * ureg.millimeter,
                    height=sample_size_y * ureg.millimeter,
                )
        # TODO implement other sample shapes

    def _parse_cell(
        self,
        sub_var: h5py.Group,
    ) -> ThreeElectrodeCell:
        """Parse three electrode cell setup."""
        cell = ThreeElectrodeCell()
        cell.working_electrode = WorkingElectrode()
        cell.reference_electrode = ReferenceElectrode(
            reference_type='Reversible Hydrogen Electrode (RHE)',
        )
        cell.counter_electrode = CounterElectrode(
            geometry='Wire',
        )

        cell.electrolyte = Electrolyte()
        if 'electrolyte' in sub_var and sub_var['electrolyte'].size > 0:
            el_desc = _decode_scalar(sub_var['electrolyte'][()])
            if el_desc:
                cell.electrolyte.description = str(el_desc)
        if 'ph_value' in sub_var and sub_var['ph_value'].size > 0:
            ph = _decode_scalar(sub_var['ph_value'][()])
            if ph is not None:
                cell.electrolyte.ph_value = float(ph)

        cell.normalize(self.archive, self.logger)

        return cell

    def _parse_position(self, sub_var: h5py.Group) -> tuple[float, float]:
        """Parse position from sub_var."""
        pos_x = 0.0
        pos_y = 0.0
        if 'position_x' in sub_var and sub_var['position_x'].size > 0:
            px = _decode_scalar(sub_var['position_x'][()])
            if px is not None:
                pos_x = float(px)
        if 'position_y' in sub_var and sub_var['position_y'].size > 0:
            py = _decode_scalar(sub_var['position_y'][()])
            if py is not None:
                pos_y = float(py)
        return pos_x, pos_y

    def _parse_cv_parameters(  # noqa: PLR0912, PLR0915
        self,
        sig_grp: h5py.Group | None,
        v_arr: np.ndarray | None = None,
    ) -> CVParameter | None:
        """Parse CVParameter from a CyclicVoltammetryLegacy_variable_signal group."""
        if sig_grp is None:
            return None

        cv_param = CVParameter()
        has_any = False

        def _get_float(key: str) -> float | None:
            if key in sig_grp and sig_grp[key].size > 0:
                val = _decode_scalar(sig_grp[key][()])
                if val is not None:
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return None
            return None

        # start_v -> initial_potential
        val = _get_float('start_v')
        if val is not None:
            cv_param.initial_potential = val * ureg.volt
            has_any = True

        # stop_v -> final_potential
        val = _get_float('stop_v')
        if val is not None:
            cv_param.final_potential = val * ureg.volt
            has_any = True

        # min_v -> lower_switching_potential
        val = _get_float('min_v')
        if val is not None:
            cv_param.lower_switching_potential = val * ureg.volt
            has_any = True

        # max_v -> upper_switching_potential
        val = _get_float('max_v')
        if val is not None:
            cv_param.upper_switching_potential = val * ureg.volt
            has_any = True

        # num_cycles -> number_of_cycles
        val = _get_float('num_cycles')
        if val is not None:
            cv_param.number_of_cycles = int(round(val))
            has_any = True

        # scan_rate_mvpers -> scan_rate
        val = _get_float('scan_rate_mvpers')
        if val is not None:
            cv_param.scan_rate = val * (ureg.millivolt / ureg.second)
            has_any = True

        # step_v / step_potential -> step_potential
        val = _get_float('step_v')
        if val is None:
            val = _get_float('step_potential')
        if val is not None:
            cv_param.step_potential = val * ureg.volt
            has_any = True

        if not has_any:
            return None

        # Determine initial scan direction
        if v_arr is not None and len(v_arr) > 1:
            diffs = np.diff(v_arr)
            non_zero = diffs[diffs != 0]
            if len(non_zero) > 0:
                cv_param.initial_scan_direction = (
                    'positive' if non_zero[0] > 0 else 'negative'
                )
        elif (
            cv_param.initial_potential is not None
            and cv_param.upper_switching_potential is not None
        ):
            if np.isclose(
                cv_param.initial_potential.to('volt').magnitude,
                cv_param.upper_switching_potential.to('volt').magnitude,
            ):
                cv_param.initial_scan_direction = 'negative'
            else:
                cv_param.initial_scan_direction = 'positive'

        return cv_param

    def _parse_cv(
        self,
        sub: h5py.Group,
        cell: ThreeElectrodeCell,
        data: ElectrochemicalMapping,
        child_archive: 'EntryArchive' = None,
    ) -> CyclicVoltammetry | None:
        """Parse a single cyclic voltammetry measurement entry."""
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

        cv_param = None
        sig_key = (
            'CyclicVoltammetryLegacy_variable_signal'
            if 'CyclicVoltammetryLegacy_variable_signal' in cv_grp
            else next((k for k in cv_grp if k.endswith('_variable_signal')), None)
        )
        if sig_key:
            cv_sig = cv_grp[sig_key]
            cv_param = self._parse_cv_parameters(cv_sig, v_arr=v_arr)

        cv_res = CVResult(
            potential=v_arr * ureg.volt,
            current=i_arr * ureg.ampere,
        )
        if t_arr is not None:
            cv_res.time = t_arr * ureg.second

        cv_entry = CyclicVoltammetry(
            results=[cv_res],
            cell=cell,
            samples=data.samples if data.samples else None,
        )
        if cv_param is not None:
            cv_entry.parameters = cv_param

        target_archive = self.archive
        if child_archive is not None:
            child_archive.data = cv_entry
            target_archive = child_archive

        cv_entry.normalize(target_archive, self.logger)

        return cv_entry

    def _parse_ecsa(  # noqa PLR0912
        self,
        sub: h5py.Group,
        cell: ThreeElectrodeCell,
        data: ElectrochemicalMapping,
        child_archive: 'EntryArchive' = None,
    ) -> ECSAMeasurement | None:
        """Parse ECSA scan rate series into an ECSA measurement entry."""
        if 'Subprotocol_ECSA' not in sub:
            return None
        ecsa_grp = sub['Subprotocol_ECSA']
        run_keys = [k for k in ecsa_grp.keys() if isinstance(ecsa_grp[k], h5py.Group)]
        run_keys.sort(
            key=lambda k: (
                int(re.search(r'\d+', k).group()) if re.search(r'\d+', k) else 0
            )
        )

        ecsa_res = ECSAResult()
        ecsa_params = ECSAParameter()

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

            run_param = None
            sr_r = None
            sig_key = (
                'CyclicVoltammetryLegacy_variable_signal'
                if 'CyclicVoltammetryLegacy_variable_signal' in r_grp
                else next((k for k in r_grp if k.endswith('_variable_signal')), None)
            )
            if sig_key:
                r_sig = r_grp[sig_key]
                run_param = self._parse_cv_parameters(r_sig, v_arr=v_r)
                if run_param is not None:
                    ecsa_params.runs.append(run_param)
                    if run_param.scan_rate is not None:
                        sr_r = run_param.scan_rate.to('millivolt / second').magnitude
                elif 'scan_rate_mvpers' in r_sig and r_sig['scan_rate_mvpers'].size > 0:
                    sr = _decode_scalar(r_sig['scan_rate_mvpers'][()])
                    if sr is not None:
                        try:
                            sr_r = float(sr)
                        except (ValueError, TypeError):
                            sr_r = None

            run_name = f'ECSA {sr_r:.0f} mV/s' if sr_r is not None else r_k
            run_cv = CVResult(
                name=run_name,
                potential=v_r * ureg.volt,
                current=i_r * ureg.ampere,
            )
            if t_r is not None:
                run_cv.time = t_r * ureg.second

            ecsa_res.runs.append(run_cv)

        ecsa_entry = ECSAMeasurement(
            results=[ecsa_res],
            cell=cell,
            samples=data.samples if data.samples else None,
        )
        if len(ecsa_params.runs) > 0:
            ecsa_entry.parameters = ecsa_params

        target_archive = self.archive
        if child_archive is not None:
            child_archive.data = ecsa_entry
            target_archive = child_archive

        ecsa_entry.normalize(target_archive, self.logger)

        return ecsa_entry

    def _parse_mapping(
        self,
        entry: ElectrochemicalMeasurement,
        pos_x: float,
        pos_y: float,
        technique: str = 'Measurement',
    ) -> ElectrochemicalMappingStep:
        """
        Parse an electrochemical measurement into
        an electrochemical mapping step.
        """
        mapping = ElectrochemicalMappingStep()
        mapping.activity = entry
        mapping.name = f'{technique} at stage x = {pos_x:.1f} mm, y = {pos_y:.1f} mm'
        mapping.x_absolute = pos_x * ureg.millimeter
        mapping.y_absolute = pos_y * ureg.millimeter
        return mapping

    def parse(  # noqa: PLR0912, PLR0915
        self,
        mainfile: str,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
        child_archives: dict[str, 'EntryArchive'] = None,
    ) -> None:

        self.archive = archive
        self.logger = logger

        if child_archives is None:
            child_archives = {}
        self.child_archives = child_archives

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
        if not archive.metadata.entry_name:
            archive.metadata.entry_name = data.name

        with h5py.File(mainfile, 'r') as hdf:
            if 'CAMELS_entry' not in hdf:
                logger.warning('No CAMELS_entry group found in HDF5 file.')
                archive.data = data
                return

            entry = hdf['CAMELS_entry']
            self._parse_metadata(entry, data)

            if (
                'data' not in entry
                or 'ScreeningLoop_variable_signal' not in entry['data']
                or 'primary' not in entry['data']
            ):
                logger.warning('No screening data group found in CAMELS entry.')
                archive.data = data
                return

            self._parse_alignment(entry['data']['ScreeningLoop_variable_signal'], data)

            primary_grp = entry['data']['primary']
            subprotocol_keys = self._get_subprotocol_keys(primary_grp)

            for sub_key in subprotocol_keys:
                sub = primary_grp[sub_key]

                var_key = next((k for k in sub if k.endswith('_variable_signal')), None)
                if not var_key:
                    logger.warning(f'No variable signal found in {sub_key}')
                    continue
                sub_var = sub[var_key]

                try:
                    cell = self._parse_cell(sub_var)
                    pos_x, pos_y = self._parse_position(sub_var)

                    cv_key = f'{sub_key}/CyclicVoltammetry'
                    cv_child = None
                    if child_archives is not None:
                        cv_child = child_archives.get(cv_key) or child_archives.get(
                            f'{sub_key}/Subprotocol_CyclicVoltammetry'
                        )
                        if cv_child is None:
                            from nomad.datamodel import EntryArchive

                            cv_child = EntryArchive()
                            child_archives[cv_key] = cv_child

                        if cv_child.metadata is None:
                            from nomad.datamodel import EntryMetadata

                            cv_child.metadata = EntryMetadata()
                        if not cv_child.metadata.entry_name:
                            cv_child.metadata.entry_name = f'{data.name} {cv_key}'
                        if not cv_child.metadata.mainfile_key:
                            cv_child.metadata.mainfile_key = cv_key
                        if not cv_child.metadata.mainfile:
                            cv_child.metadata.mainfile = mainfile

                    cv_entry = self._parse_cv(sub, cell, data, child_archive=cv_child)
                    if cv_entry is not None:
                        cv_mapping = self._parse_mapping(
                            cv_entry, pos_x, pos_y, technique='Cyclic Voltammetry'
                        )
                        data.steps.append(cv_mapping)
                    elif (
                        cv_child is not None
                        and cv_key in child_archives
                        and cv_child.data is None
                    ):
                        child_archives.pop(cv_key, None)

                    ecsa_key = f'{sub_key}/ECSAMeasurement'
                    ecsa_child = None
                    if child_archives is not None:
                        ecsa_child = child_archives.get(ecsa_key) or child_archives.get(
                            f'{sub_key}/Subprotocol_ECSA'
                        )
                        if ecsa_child is None:
                            from nomad.datamodel import EntryArchive

                            ecsa_child = EntryArchive()
                            child_archives[ecsa_key] = ecsa_child

                        if ecsa_child.metadata is None:
                            from nomad.datamodel import EntryMetadata

                            ecsa_child.metadata = EntryMetadata()
                        if not ecsa_child.metadata.entry_name:
                            ecsa_child.metadata.entry_name = f'{data.name} {ecsa_key}'
                        if not ecsa_child.metadata.mainfile_key:
                            ecsa_child.metadata.mainfile_key = ecsa_key
                        if not ecsa_child.metadata.mainfile:
                            ecsa_child.metadata.mainfile = mainfile

                    ecsa_entry = self._parse_ecsa(
                        sub, cell, data, child_archive=ecsa_child
                    )
                    if ecsa_entry is not None:
                        ecsa_mapping = self._parse_mapping(
                            ecsa_entry, pos_x, pos_y, technique='ECSA Measurement'
                        )
                        data.steps.append(ecsa_mapping)
                    elif (
                        ecsa_child is not None
                        and ecsa_key in child_archives
                        and ecsa_child.data is None
                    ):
                        child_archives.pop(ecsa_key, None)
                except Exception as exc:
                    logger.warning(
                        f'Failed to parse subprotocol point, skipping {sub_key}: {exc}'
                    )

        archive.data = data
        logger.info(
            'XY-PEC measurement parsed successfully',
            n_points=len(data.results),
        )
