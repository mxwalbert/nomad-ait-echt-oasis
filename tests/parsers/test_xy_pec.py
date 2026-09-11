import logging
import os
import h5py
import numpy as np
import pytest
from nomad.datamodel import EntryArchive, EntryMetadata
from nomad.units import ureg

from nomad_ait_echt_oasis.parsers.xy_pec import (
    XYPECParser,
    _decode_val,
    _extract_legacy_var,
)
from nomad_ait_echt_oasis.schema_packages.electrochemical_characterization import (
    CVMappingResult,
    CVResult,
    ECSAMappingResult,
    ECSAResult,
    ElectrochemicalMapping,
    ElectrochemicalMappingResult,
)

EXPECTED_POINTS = 5
EXPECTED_TOTAL_RESULTS = 10
EXPECTED_FIGURES = 2
EXPECTED_ECSA_FIGURES = 1
EXPECTED_ECSA_RUNS = 8

TEST_FILE = os.path.join(
    '.local',
    'electrochemical_characterization',
    'xy_pec',
    'EASYHAc',
    'EasyHAC_NiMo_Comb03_ScreeningLoop_CyclicVoltammetry_2026-09-09T13-25-32+02-00.h5',
)


def test_xy_pec_parser():
    if not os.path.exists(TEST_FILE):
        return

    parser = XYPECParser()
    archive = EntryArchive(metadata=EntryMetadata(entry_name='test_xy_pec'))
    logger = logging.getLogger('test_xy_pec')

    assert parser.is_mainfile(TEST_FILE, 'application/x-hdf', b'', '')

    parser.parse(TEST_FILE, archive, logger)

    assert isinstance(archive.data, ElectrochemicalMapping)
    assert len(archive.data.results) == EXPECTED_TOTAL_RESULTS

    # Run normalizer
    archive.data.normalize(archive, logger)

    cv_results = [
        r for r in archive.data.results if isinstance(r, CVMappingResult)
    ]
    ecsa_results = [
        r for r in archive.data.results if isinstance(r, ECSAMappingResult)
    ]

    assert len(cv_results) == EXPECTED_POINTS
    assert len(ecsa_results) == EXPECTED_POINTS

    for cv_map in cv_results:
        assert isinstance(cv_map, CVMappingResult)
        assert isinstance(cv_map, CVResult)
        assert isinstance(cv_map, ElectrochemicalMappingResult)
        assert cv_map.name is not None and len(cv_map.name) > 0
        assert cv_map.x_absolute is not None
        assert cv_map.y_absolute is not None
        assert len(cv_map.cycles) > 0
        assert len(cv_map.figures) == EXPECTED_FIGURES

    for ecsa_map in ecsa_results:
        assert isinstance(ecsa_map, ECSAMappingResult)
        assert isinstance(ecsa_map, ECSAResult)
        assert isinstance(ecsa_map, ElectrochemicalMappingResult)
        assert ecsa_map.name is not None and len(ecsa_map.name) > 0
        assert ecsa_map.x_absolute is not None
        assert ecsa_map.y_absolute is not None
        assert len(ecsa_map.runs) == EXPECTED_ECSA_RUNS
        assert ecsa_map.double_layer_capacitance is not None
        assert len(ecsa_map.figures) == EXPECTED_ECSA_FIGURES
        assert len(ecsa_map.runs[0].figures) == EXPECTED_FIGURES


def test_decode_val():
    """Test _decode_val with bytes, numpy scalar bytes, scalars, and strings."""
    assert _decode_val(b'test_bytes') == 'test_bytes'
    assert _decode_val(np.array(b'numpy_bytes')) == 'numpy_bytes'
    assert _decode_val(np.array(42)) == 42
    assert _decode_val('already_string') == 'already_string'
    assert _decode_val(100) == 100


def test_extract_legacy_var(tmp_path):
    """Test _extract_legacy_var with various group and dataset configurations."""
    assert _extract_legacy_var(None, ['key']) is None

    test_h5 = tmp_path / 'legacy_var.h5'
    with h5py.File(test_h5, 'w') as f:
        grp = f.create_group('sig')
        grp.create_dataset('empty_ds', data=np.array([]))
        grp.create_dataset('valid_ds', data=np.array([b'extracted_value']))

    with h5py.File(test_h5, 'r') as f:
        grp = f['sig']
        assert _extract_legacy_var(grp, ['nonexistent']) is None
        assert _extract_legacy_var(grp, ['empty_ds']) is None
        assert _extract_legacy_var(grp, ['valid_ds']) == 'extracted_value'


def test_is_mainfile_variations(tmp_path):
    """Test is_mainfile file extension, corruption, and detection heuristics."""
    parser = XYPECParser()

    # Invalid file extension
    assert not parser.is_mainfile('measurement.txt', 'text/plain', b'', '')

    # Non-existent or corrupt HDF5 file
    corrupt_file = tmp_path / 'corrupt.h5'
    corrupt_file.write_text('not an hdf5 file')
    assert not parser.is_mainfile(str(corrupt_file), 'application/x-hdf', b'', '')

    # Valid HDF5 but no CAMELS_entry
    no_camels = tmp_path / 'no_camels.h5'
    with h5py.File(no_camels, 'w') as f:
        f.create_group('other_entry')
    assert not parser.is_mainfile(str(no_camels), 'application/x-hdf', b'', '')

    # CAMELS_entry with instruments/xy_pec
    with_inst = tmp_path / 'with_inst.h5'
    with h5py.File(with_inst, 'w') as f:
        entry = f.create_group('CAMELS_entry')
        inst = entry.create_group('instruments')
        inst.create_group('xy_pec')
    assert parser.is_mainfile(str(with_inst), 'application/x-hdf', b'', '')

    # CAMELS_entry with measurement_details/plan_name
    with_pn = tmp_path / 'with_pn.h5'
    with h5py.File(with_pn, 'w') as f:
        entry = f.create_group('CAMELS_entry')
        md = entry.create_group('measurement_details')
        md.create_dataset('plan_name', data=np.array(b'ScreeningLoop_Test'))
    assert parser.is_mainfile(str(with_pn), 'application/x-hdf', b'', '')

    # CAMELS_entry with measurement_details/protocol_overview
    with_po = tmp_path / 'with_po.h5'
    with h5py.File(with_po, 'w') as f:
        entry = f.create_group('CAMELS_entry')
        md = entry.create_group('measurement_details')
        md.create_dataset('protocol_overview', data=np.array(b'xy_pec screening'))
    assert parser.is_mainfile(str(with_po), 'application/x-hdf', b'', '')


def test_parser_missing_entries(tmp_path):
    """Test parser behavior when CAMELS_entry or primary data group is missing."""
    parser = XYPECParser()
    logger = logging.getLogger('test_xy_pec')

    # Missing CAMELS_entry
    no_camels = tmp_path / 'missing_camels.h5'
    with h5py.File(no_camels, 'w') as f:
        f.create_group('unrelated')
    archive = EntryArchive()
    parser.parse(str(no_camels), archive, logger)
    assert isinstance(archive.data, ElectrochemicalMapping)
    assert not archive.data.results

    # Missing primary data
    no_primary = tmp_path / 'missing_primary.h5'
    with h5py.File(no_primary, 'w') as f:
        f.create_group('CAMELS_entry')
    archive2 = EntryArchive()
    parser.parse(str(no_primary), archive2, logger)
    assert isinstance(archive2.data, ElectrochemicalMapping)
    assert not archive2.data.results


def test_parser_metadata_fallbacks_and_elapsed_time(tmp_path):
    """
    Test metadata extraction (invalid datetime, description, sample_id),
    cell size alignment, ElapsedTime usage, and variable signal fallbacks.
    """
    parser = XYPECParser()
    logger = logging.getLogger('test_xy_pec')

    h5_file = tmp_path / 'metadata_test.h5'
    with h5py.File(h5_file, 'w') as f:
        entry = f.create_group('CAMELS_entry')

        # Measurement details: invalid start_time + valid description
        md = entry.create_group('measurement_details')
        md.create_dataset('start_time', data=np.array(b'invalid-iso-time'))
        md.create_dataset('measurement_description', data=np.array(b'Test Run Description'))

        # Sample with sample_id instead of name
        sample_grp = entry.create_group('sample')
        sample_grp.create_dataset('sample_id', data=np.array(b'AIT_SAMPLE_042'))

        # Data with electrolyte and alignment size
        data_grp = entry.create_group('data')
        sig_grp = data_grp.create_group('ScreeningLoop_variable_signal')
        sig_grp.create_dataset('electrolyte', data=np.array([b'1M KOH']))
        sig_grp.create_dataset('sample_size_x', data=np.array([25.0]))
        sig_grp.create_dataset('sample_size_y', data=np.array([50.0]))

        primary = data_grp.create_group('primary')
        sub = primary.create_group('Subprotocol_RunSubprotocol_0')

        # Coordinates
        sp_sig = sub.create_group('SinglePointCVfromReservoir_variable_signal')
        sp_sig.create_dataset('position_x', data=np.array([12.5]))
        sp_sig.create_dataset('position_y', data=np.array([25.0]))
        sp_sig.create_dataset('position_index', data=np.array([0]))

        # CV with ElapsedTime instead of time, and fallbacks
        cv_grp = sub.create_group('Subprotocol_CyclicVoltammetry')
        v_data = np.linspace(-0.2, 0.6, 20)
        i_data = np.linspace(-0.001, 0.001, 20)
        cv_grp.create_dataset('matterlab_potentiostat_read_potential', data=v_data)
        cv_grp.create_dataset('matterlab_potentiostat_read_current', data=i_data)
        cv_grp.create_dataset('ElapsedTime', data=np.linspace(0, 10, 20))

        cv_sig = cv_grp.create_group('CyclicVoltammetryLegacy_variable_signal')
        cv_sig.create_dataset('electrode_area', data=np.array([0.196]))
        cv_sig.create_dataset('reference_electrode', data=np.array([b'Ag/AgCl (sat. KCl)']))

        # ECSA with ElapsedTime instead of time
        ecsa_grp = sub.create_group('Subprotocol_ECSA')
        r0 = ecsa_grp.create_group('Run_0')
        r0.create_dataset('matterlab_potentiostat_read_potential', data=v_data)
        r0.create_dataset('matterlab_potentiostat_read_current', data=i_data)
        r0.create_dataset('ElapsedTime', data=np.linspace(0, 5, 20))

    archive = EntryArchive()
    parser.parse(str(h5_file), archive, logger)

    data = archive.data
    assert data.description == 'Test Run Description'
    assert len(data.samples) == 1
    assert data.samples[0].name == 'AIT_SAMPLE_042'
    assert data.sample_alignment is not None
    assert data.sample_alignment.width.to('millimeter').magnitude == pytest.approx(25.0)
    assert data.sample_alignment.height.to('millimeter').magnitude == pytest.approx(50.0)

    # Check that fallback area and reference type were populated
    assert data.cell.working_electrode.surface_area is not None
    assert data.cell.working_electrode.surface_area.to('centimeter ** 2').magnitude == pytest.approx(0.196)
    assert data.cell.reference_electrode.reference_type == 'Ag/AgCl (sat. KCl)'

    # Check results
    assert len(data.results) == 2
    cv_res = data.results[0]
    assert isinstance(cv_res, CVMappingResult)
    assert cv_res.time is not None
    assert cv_res.point_index == 0


def test_parser_subprotocol_skip_cases(tmp_path):
    """
    Test subprotocols with missing Subprotocol_CyclicVoltammetry,
    missing Subprotocol_ECSA, missing potentiostat signals, and invalid area values.
    """
    parser = XYPECParser()
    logger = logging.getLogger('test_xy_pec')

    h5_file = tmp_path / 'skip_cases.h5'
    with h5py.File(h5_file, 'w') as f:
        entry = f.create_group('CAMELS_entry')
        data_grp = entry.create_group('data')
        primary = data_grp.create_group('primary')

        # Subprotocol 0: Missing Subprotocol_CyclicVoltammetry & Subprotocol_ECSA
        primary.create_group('Subprotocol_RunSubprotocol_0')

        # Subprotocol 1: Subprotocol_CyclicVoltammetry exists but missing potential/current
        sub1 = primary.create_group('Subprotocol_RunSubprotocol_1')
        sub1.create_group('Subprotocol_CyclicVoltammetry')

        # Subprotocol 2: ECSA exists but run missing potential/current, and invalid electrode area
        sub2 = primary.create_group('Subprotocol_RunSubprotocol_2')
        cv2 = sub2.create_group('Subprotocol_CyclicVoltammetry')
        cv2_sig = cv2.create_group('CyclicVoltammetryLegacy_variable_signal')
        cv2_sig.create_dataset('electrode_area', data=np.array([b'invalid_float_string']))

        ecsa2 = sub2.create_group('Subprotocol_ECSA')
        ecsa2.create_group('Run_0')  # Empty run missing potential/current

    archive = EntryArchive()
    parser.parse(str(h5_file), archive, logger)

    assert len(archive.data.results) == 1
    assert isinstance(archive.data.results[0], ECSAMappingResult)
    assert len(archive.data.results[0].runs) == 0


def test_parser_with_predefined_cell_parameters(tmp_path):
    """Test parse when archive.data already has cell parameters and alignment ph."""
    from nomad_ait_echt_oasis.schema_packages.electrochemical_characterization import (
        Electrolyte,
        ReferenceElectrode,
        ThreeElectrodeCell,
        WorkingElectrode,
    )

    parser = XYPECParser()
    logger = logging.getLogger('test_xy_pec')

    h5_file = tmp_path / 'predefined_cell.h5'
    with h5py.File(h5_file, 'w') as f:
        entry = f.create_group('CAMELS_entry')
        data_grp = entry.create_group('data')
        sig_grp = data_grp.create_group('ScreeningLoop_variable_signal')
        sig_grp.create_dataset('ph_value', data=np.array([2.0]))

        primary = data_grp.create_group('primary')
        sub = primary.create_group('Subprotocol_RunSubprotocol_0')
        cv_grp = sub.create_group('Subprotocol_CyclicVoltammetry')
        v_data = np.linspace(-0.2, 0.6, 15)
        i_data = np.linspace(-0.001, 0.001, 15)
        cv_grp.create_dataset('matterlab_potentiostat_read_potential', data=v_data)
        cv_grp.create_dataset('matterlab_potentiostat_read_current', data=i_data)
        cv_grp.create_dataset('time', data=np.linspace(0, 5, 15))

    cell = ThreeElectrodeCell(
        working_electrode=WorkingElectrode(surface_area=0.5 * (ureg.centimeter**2)),
        reference_electrode=ReferenceElectrode(
            standard_potential_vs_rhe=0.200 * ureg.volt
        ),
        electrolyte=Electrolyte(ph_value=2.0),
    )
    predefined_data = ElectrochemicalMapping(cell=cell)
    archive = EntryArchive(data=predefined_data)

    parser.parse(str(h5_file), archive, logger)

    assert len(archive.data.results) == 1
    cv_res = archive.data.results[0]
    assert cv_res.current_density is not None
    assert cv_res.potential_vs_rhe is not None
