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
    CVParameter,
    CVResult,
    CyclicVoltammetry,
    ECSAParameter,
    ECSAResult,
    ECSAMeasurement,
    ElectrochemicalMapping,
    ElectrochemicalMappingResult,
    ElectrochemicalMappingStep,
)

EXPECTED_POINTS = 2
EXPECTED_TOTAL_RESULTS = 4
EXPECTED_FIGURES = 2
EXPECTED_ECSA_FIGURES = 1
EXPECTED_ECSA_RUNS = 8

TEST_FILE = 'tests/data/xy_pec_test.h5'


def test_xy_pec_parser():
    if not os.path.exists(TEST_FILE):
        return

    parser = XYPECParser()
    archive = EntryArchive(metadata=EntryMetadata(entry_name='test_xy_pec'))
    logger = logging.getLogger('test_xy_pec')

    mainfile_keys = parser.is_mainfile(TEST_FILE, 'application/x-hdf', b'', '')
    assert isinstance(mainfile_keys, list)
    assert len(mainfile_keys) == EXPECTED_TOTAL_RESULTS

    child_archives = {k: EntryArchive() for k in mainfile_keys}
    parser.parse(TEST_FILE, archive, logger, child_archives=child_archives)

    assert len(child_archives) == EXPECTED_TOTAL_RESULTS
    for key, child in child_archives.items():
        assert isinstance(child.data, (CyclicVoltammetry, ECSAMeasurement))

    assert isinstance(archive.data, ElectrochemicalMapping)
    assert len(archive.data.steps) == EXPECTED_TOTAL_RESULTS

    # Run normalizer
    archive.data.normalize(archive, logger)

    cv_steps = [
        s for s in archive.data.steps
        if isinstance(s.measurement, CyclicVoltammetry)
    ]
    ecsa_steps = [
        s for s in archive.data.steps
        if isinstance(s.measurement, ECSAMeasurement)
    ]

    assert len(cv_steps) == EXPECTED_POINTS
    assert len(ecsa_steps) == EXPECTED_POINTS

    for cv_map in cv_steps:
        assert isinstance(cv_map, ElectrochemicalMappingStep)
        assert cv_map.name is not None and len(cv_map.name) > 0
        assert cv_map.x_absolute is not None
        assert cv_map.y_absolute is not None
        cv = cv_map.measurement
        assert isinstance(cv, CyclicVoltammetry)
        assert cv.name is not None and len(cv.name) > 0
        assert isinstance(cv.parameters, CVParameter)
        assert cv.parameters.initial_potential is not None
        assert cv.parameters.lower_switching_potential is not None
        assert cv.parameters.upper_switching_potential is not None
        assert cv.parameters.scan_rate is not None
        assert cv.parameters.number_of_cycles is not None
        cv_result = cv.results[0]
        assert isinstance(cv_result, CVResult)
        assert cv_result.scan_rate is not None
        assert len(cv_result.cycles) > 0
        assert len(cv_result.figures) == EXPECTED_FIGURES

    for ecsa_map in ecsa_steps:
        assert isinstance(ecsa_map, ElectrochemicalMappingStep)
        assert ecsa_map.name is not None and len(ecsa_map.name) > 0
        assert ecsa_map.x_absolute is not None
        assert ecsa_map.y_absolute is not None
        ecsa = ecsa_map.measurement
        assert isinstance(ecsa, ECSAMeasurement)
        assert ecsa.name is not None and len(ecsa.name) > 0
        assert isinstance(ecsa.parameters, ECSAParameter)
        assert len(ecsa.parameters.runs) == EXPECTED_ECSA_RUNS
        for run_param in ecsa.parameters.runs:
            assert isinstance(run_param, CVParameter)
            assert run_param.scan_rate is not None
            assert run_param.lower_switching_potential is not None
            assert run_param.upper_switching_potential is not None
        ecsa_result = ecsa.results[0]
        assert isinstance(ecsa_result, ECSAResult)
        assert ecsa_result.double_layer_capacitance is not None
        assert len(ecsa_result.figures) == EXPECTED_ECSA_FIGURES
        assert len(ecsa_result.runs[0].figures) == EXPECTED_FIGURES
        for run_cv in ecsa_result.runs:
            assert isinstance(run_cv, CVResult)
            assert run_cv.scan_rate is not None


def test_decode_val():
    """Test _decode_val with bytes, numpy scalar bytes, scalars, strings, and 1D arrays."""
    assert _decode_val(b'test_bytes') == 'test_bytes'
    assert _decode_val(np.array(b'numpy_bytes')) == 'numpy_bytes'
    assert _decode_val(np.array([b'array_bytes'])) == 'array_bytes'
    assert _decode_val(np.array([42])) == 42
    assert _decode_val(np.array(42)) == 42
    assert _decode_val('already_string') == 'already_string'
    assert _decode_val(100) == 100
    assert _decode_val(np.array([b'a', b'b'])) == ['a', 'b']
    assert _decode_val(np.array([1, 2])) == [1, 2]


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
        inst = entry.create_group('instruments')
        inst.create_group('xy_pec')

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
        sig_grp.create_dataset('sample_shape', data=np.array(b'rectangle'))
        sig_grp.create_dataset('electrolyte', data=np.array([b'1M KOH']))
        sig_grp.create_dataset('sample_size_x', data=np.array([25.0]))
        sig_grp.create_dataset('sample_size_y', data=np.array([50.0]))

        primary = data_grp.create_group('primary')
        sub = primary.create_group('Subprotocol_RunSubprotocol_0')

        # Coordinates and variable signal
        sp_sig = sub.create_group('SinglePointCVfromReservoir_variable_signal')
        sp_sig.create_dataset('position_x', data=np.array([12.5]))
        sp_sig.create_dataset('position_y', data=np.array([25.0]))
        sp_sig.create_dataset('position_index', data=np.array([0]))
        sp_sig.create_dataset('electrolyte', data=np.array([b'1M KOH']))
        sp_sig.create_dataset('ph_value', data=np.array([14.0]))

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

    archive = EntryArchive(metadata=EntryMetadata(entry_name='metadata_test'))
    mainfile_keys = parser.is_mainfile(str(h5_file), 'application/x-hdf', b'', '')
    child_archives = {k: EntryArchive() for k in mainfile_keys} if isinstance(mainfile_keys, list) else {}
    parser.parse(str(h5_file), archive, logger, child_archives=child_archives)

    data = archive.data
    assert data.description == 'Test Run Description'
    assert len(data.samples) == 1
    assert data.samples[0].lab_id == 'AIT_SAMPLE_042'
    assert data.sample_alignment is not None
    assert data.sample_alignment.width.to('millimeter').magnitude == pytest.approx(25.0)
    assert data.sample_alignment.height.to('millimeter').magnitude == pytest.approx(50.0)

    # Check steps
    assert len(data.steps) == 2
    cv_map = data.steps[0]
    assert isinstance(cv_map, ElectrochemicalMappingStep)
    assert cv_map.x_absolute.to('millimeter').magnitude == pytest.approx(12.5)
    assert cv_map.y_absolute.to('millimeter').magnitude == pytest.approx(25.0)

    cv = cv_map.measurement
    assert isinstance(cv, CyclicVoltammetry)
    assert cv.name is not None
    assert cv.cell is not None
    assert cv.cell.working_electrode is not None
    assert cv.cell.reference_electrode.reference_type == 'Reversible Hydrogen Electrode (RHE)'
    assert cv.cell.counter_electrode.geometry == 'Wire'
    assert cv.cell.electrolyte.description == '1M KOH'
    assert cv.cell.electrolyte.ph_value == 14.0

    cv_res = cv.results[0]
    assert isinstance(cv_res, CVResult)
    assert cv_res.time is not None
    assert len(cv_res.time) == 20

    ecsa_map = data.steps[1]
    assert isinstance(ecsa_map, ElectrochemicalMappingStep)
    ecsa = ecsa_map.measurement
    assert isinstance(ecsa, ECSAMeasurement)
    assert ecsa.name is not None
    ecsa_res = ecsa.results[0]
    assert isinstance(ecsa_res, ECSAResult)
    assert len(ecsa_res.runs) == 1
    assert ecsa_res.runs[0].time is not None


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
        inst = entry.create_group('instruments')
        inst.create_group('xy_pec')
        data_grp = entry.create_group('data')
        data_grp.create_group('ScreeningLoop_variable_signal')
        primary = data_grp.create_group('primary')

        # Subprotocol 0: Missing Subprotocol_CyclicVoltammetry & Subprotocol_ECSA
        sub0 = primary.create_group('Subprotocol_RunSubprotocol_0')
        sub0.create_group('SinglePointCVfromReservoir_variable_signal')

        # Subprotocol 1: Subprotocol_CyclicVoltammetry exists but missing potential/current
        sub1 = primary.create_group('Subprotocol_RunSubprotocol_1')
        sub1.create_group('SinglePointCVfromReservoir_variable_signal')
        sub1.create_group('Subprotocol_CyclicVoltammetry')

        # Subprotocol 2: ECSA exists but run missing potential/current, and invalid electrode area
        sub2 = primary.create_group('Subprotocol_RunSubprotocol_2')
        sub2.create_group('SinglePointCVfromReservoir_variable_signal')
        cv2 = sub2.create_group('Subprotocol_CyclicVoltammetry')
        cv2_sig = cv2.create_group('CyclicVoltammetryLegacy_variable_signal')
        cv2_sig.create_dataset('electrode_area', data=np.array([b'invalid_float_string']))

        ecsa2 = sub2.create_group('Subprotocol_ECSA')
        ecsa2.create_group('Run_0')  # Empty run missing potential/current

    archive = EntryArchive(metadata=EntryMetadata(entry_name='skip_cases'))
    mainfile_keys = parser.is_mainfile(str(h5_file), 'application/x-hdf', b'', '')
    child_archives = {k: EntryArchive() for k in mainfile_keys} if isinstance(mainfile_keys, list) else {}
    parser.parse(str(h5_file), archive, logger, child_archives=child_archives)

    assert len(archive.data.steps) == 1
    ecsa_map = archive.data.steps[0]
    assert isinstance(ecsa_map, ElectrochemicalMappingStep)
    ecsa = ecsa_map.measurement
    assert isinstance(ecsa, ECSAMeasurement)
    assert len(ecsa.results[0].runs) == 0


def test_parser_with_predefined_cell_parameters(tmp_path):
    """Test parse with cell parameters and ph from variable signal."""
    parser = XYPECParser()
    logger = logging.getLogger('test_xy_pec')

    h5_file = tmp_path / 'predefined_cell.h5'
    with h5py.File(h5_file, 'w') as f:
        entry = f.create_group('CAMELS_entry')
        inst = entry.create_group('instruments')
        inst.create_group('xy_pec')
        data_grp = entry.create_group('data')
        data_grp.create_group('ScreeningLoop_variable_signal')

        primary = data_grp.create_group('primary')
        sub = primary.create_group('Subprotocol_RunSubprotocol_0')
        sub_sig = sub.create_group('SinglePointCVfromReservoir_variable_signal')
        sub_sig.create_dataset('ph_value', data=np.array([2.0]))
        sub_sig.create_dataset('electrolyte', data=np.array([b'0.1M H2SO4']))

        cv_grp = sub.create_group('Subprotocol_CyclicVoltammetry')
        v_data = np.linspace(-0.2, 0.6, 15)
        i_data = np.linspace(-0.001, 0.001, 15)
        cv_grp.create_dataset('matterlab_potentiostat_read_potential', data=v_data)
        cv_grp.create_dataset('matterlab_potentiostat_read_current', data=i_data)
        cv_grp.create_dataset('time', data=np.linspace(0, 5, 15))

    archive = EntryArchive(metadata=EntryMetadata(entry_name='predefined_cell'))
    mainfile_keys = parser.is_mainfile(str(h5_file), 'application/x-hdf', b'', '')
    child_archives = {k: EntryArchive() for k in mainfile_keys} if isinstance(mainfile_keys, list) else {}
    parser.parse(str(h5_file), archive, logger, child_archives=child_archives)

    assert len(archive.data.steps) == 1
    cv_map = archive.data.steps[0]
    assert isinstance(cv_map, ElectrochemicalMappingStep)
    cv = cv_map.measurement
    assert isinstance(cv, CyclicVoltammetry)
    assert cv.cell.electrolyte.ph_value == 2.0
    assert cv.cell.electrolyte.description == '0.1M H2SO4'
    assert cv.cell.reference_electrode.reference_type == 'Reversible Hydrogen Electrode (RHE)'

    cv_res = cv.results[0]
    assert isinstance(cv_res, CVResult)
    assert cv_res.potential_vs_rhe is not None


def test_parser_sample_reference_edge_cases(tmp_path):
    """
    Test sample reference edge cases:
    - Missing sample group entirely: data.samples is not set, no downstream crashes.
    - Empty sample group: data.samples is not set, no downstream crashes.
    - Sample with only sample_id: name falls back to sample_id, working electrode sample syncs.
    - Sample with only name: name is set, working electrode sample syncs.
    """
    parser = XYPECParser()
    logger = logging.getLogger('test_xy_pec')

    for case_name, sample_data in [
        ('missing_sample', None),
        ('empty_sample', {}),
        ('id_only', {'sample_id': b'SAMPLE-ID-99'}),
        ('name_only', {'name': b'SAMPLE-NAME-88'}),
    ]:
        h5_file = tmp_path / f'{case_name}.h5'
        with h5py.File(h5_file, 'w') as f:
            entry = f.create_group('CAMELS_entry')
            inst = entry.create_group('instruments')
            inst.create_group('xy_pec')
            if sample_data is not None:
                s_grp = entry.create_group('sample')
                for k, v in sample_data.items():
                    s_grp.create_dataset(k, data=np.array(v))

            data_grp = entry.create_group('data')
            data_grp.create_group('ScreeningLoop_variable_signal')
            primary = data_grp.create_group('primary')
            sub = primary.create_group('Subprotocol_RunSubprotocol_0')
            sub.create_group('SinglePointCVfromReservoir_variable_signal')

            cv_grp = sub.create_group('Subprotocol_CyclicVoltammetry')
            cv_grp.create_dataset('matterlab_potentiostat_read_potential', data=np.array([0.1, 0.2]))
            cv_grp.create_dataset('matterlab_potentiostat_read_current', data=np.array([0.01, 0.02]))
            cv_grp.create_dataset('time', data=np.array([0.0, 1.0]))

        archive = EntryArchive(metadata=EntryMetadata(entry_name=case_name))
        mainfile_keys = parser.is_mainfile(str(h5_file), 'application/x-hdf', b'', '')
        child_archives = {k: EntryArchive() for k in mainfile_keys} if isinstance(mainfile_keys, list) else {}
        parser.parse(str(h5_file), archive, logger, child_archives=child_archives)

        data = archive.data
        assert len(data.steps) == 1
        cv = data.steps[0].measurement
        assert isinstance(cv, CyclicVoltammetry)

        if case_name == 'missing_sample' or case_name == 'empty_sample':
            assert not data.samples
            assert cv.cell.working_electrode.sample is None
        elif case_name == 'id_only':
            assert len(data.samples) == 1
            assert data.samples[0].lab_id == 'SAMPLE-ID-99'
            assert data.samples[0].name == 'SAMPLE-ID-99'
            assert cv.cell.working_electrode.sample == data.samples[0]
        elif case_name == 'name_only':
            assert len(data.samples) == 1
            assert data.samples[0].name == 'SAMPLE-NAME-88'
            assert cv.cell.working_electrode.sample == data.samples[0]


def test_parse_cv_and_ecsa_parameters(tmp_path):
    """Test parsing CVParameter and ECSAParameter from CyclicVoltammetryLegacy_variable_signal."""
    parser = XYPECParser()
    logger = logging.getLogger('test_xy_pec')

    h5_file = tmp_path / 'params_test.h5'
    with h5py.File(h5_file, 'w') as f:
        entry = f.create_group('CAMELS_entry')
        inst = entry.create_group('instruments')
        inst.create_group('xy_pec')
        data_grp = entry.create_group('data')
        data_grp.create_group('ScreeningLoop_variable_signal')
        primary = data_grp.create_group('primary')
        sub = primary.create_group('Subprotocol_RunSubprotocol_0')
        sub.create_group('SinglePointCVfromReservoir_variable_signal')

        # CV with legacy variable signal containing all parameters
        cv_grp = sub.create_group('Subprotocol_CyclicVoltammetry')
        v_cv = np.array([0.0, 0.5, 1.0, 0.5, 0.0])
        i_cv = np.array([1e-4, 2e-4, 3e-4, 1e-4, 0.0])
        cv_grp.create_dataset('matterlab_potentiostat_read_potential', data=v_cv)
        cv_grp.create_dataset('matterlab_potentiostat_read_current', data=i_cv)
        cv_grp.create_dataset('time', data=np.array([0.0, 1.0, 2.0, 3.0, 4.0]))

        cv_sig = cv_grp.create_group('CyclicVoltammetryLegacy_variable_signal')
        cv_sig.create_dataset('start_v', data=np.array([0.0]))
        cv_sig.create_dataset('stop_v', data=np.array([0.0]))
        cv_sig.create_dataset('min_v', data=np.array([0.0]))
        cv_sig.create_dataset('max_v', data=np.array([1.0]))
        cv_sig.create_dataset('num_cycles', data=np.array([3]))
        cv_sig.create_dataset('scan_rate_mvpers', data=np.array([50.0]))
        cv_sig.create_dataset('Screening_Count', data=np.array([1]))
        cv_sig.create_dataset('Screening_Value', data=np.array([0.5]))
        cv_sig.create_dataset('scan_rate_cal_a', data=np.array([1.0]))
        cv_sig.create_dataset('scan_rate_cal_b', data=np.array([0.0]))
        cv_sig.create_dataset('scan_rate_cal_c', data=np.array([0.0]))
        cv_sig.create_dataset('scan_rate_cal_pair', data=np.array([1.0]))

        # ECSA with 2 RunCV subprotocols each having CyclicVoltammetryLegacy_variable_signal
        ecsa_grp = sub.create_group('Subprotocol_ECSA')
        for idx, sr_val in enumerate([20.0, 100.0]):
            r_grp = ecsa_grp.create_group(f'Subprotocol_RunCV_{idx}')
            r_grp.create_dataset('matterlab_potentiostat_read_potential', data=v_cv)
            r_grp.create_dataset('matterlab_potentiostat_read_current', data=i_cv * (sr_val / 50.0))
            r_grp.create_dataset('time', data=np.linspace(0.0, 2000.0 / sr_val, len(v_cv)))

            r_sig = r_grp.create_group('CyclicVoltammetryLegacy_variable_signal')
            r_sig.create_dataset('start_v', data=np.array([0.2]))
            r_sig.create_dataset('stop_v', data=np.array([0.2]))
            r_sig.create_dataset('min_v', data=np.array([0.1]))
            r_sig.create_dataset('max_v', data=np.array([0.8]))
            r_sig.create_dataset('num_cycles', data=np.array([2]))
            r_sig.create_dataset('scan_rate_mvpers', data=np.array([sr_val]))

    archive = EntryArchive(metadata=EntryMetadata(entry_name='params_test'))
    mainfile_keys = parser.is_mainfile(str(h5_file), 'application/x-hdf', b'', '')
    child_archives = {k: EntryArchive() for k in mainfile_keys} if isinstance(mainfile_keys, list) else {}
    parser.parse(str(h5_file), archive, logger, child_archives=child_archives)

    data = archive.data
    assert len(data.steps) == 2

    # Check CV
    cv = data.steps[0].measurement
    assert isinstance(cv, CyclicVoltammetry)
    assert isinstance(cv.parameters, CVParameter)
    assert cv.parameters.initial_potential.to('volt').magnitude == pytest.approx(0.0)
    assert cv.parameters.final_potential.to('volt').magnitude == pytest.approx(0.0)
    assert cv.parameters.lower_switching_potential.to('volt').magnitude == pytest.approx(0.0)
    assert cv.parameters.upper_switching_potential.to('volt').magnitude == pytest.approx(1.0)
    assert cv.parameters.number_of_cycles == 3
    assert cv.parameters.scan_rate.to('millivolt / second').magnitude == pytest.approx(50.0)
    assert cv.parameters.initial_scan_direction == 'positive'
    cv_res = cv.results[0]
    assert cv_res.scan_rate is not None
    assert cv_res.scan_rate.to('volt / second').magnitude == pytest.approx(0.5)

    # Check ECSA
    ecsa = data.steps[1].measurement
    assert isinstance(ecsa, ECSAMeasurement)
    assert isinstance(ecsa.parameters, ECSAParameter)
    assert len(ecsa.parameters.runs) == 2

    r0_param = ecsa.parameters.runs[0]
    assert isinstance(r0_param, CVParameter)
    assert r0_param.scan_rate.to('millivolt / second').magnitude == pytest.approx(20.0)
    assert r0_param.initial_potential.to('volt').magnitude == pytest.approx(0.2)
    assert r0_param.final_potential.to('volt').magnitude == pytest.approx(0.2)
    assert r0_param.lower_switching_potential.to('volt').magnitude == pytest.approx(0.1)
    assert r0_param.upper_switching_potential.to('volt').magnitude == pytest.approx(0.8)
    assert r0_param.number_of_cycles == 2

    r1_param = ecsa.parameters.runs[1]
    assert isinstance(r1_param, CVParameter)
    assert r1_param.scan_rate.to('millivolt / second').magnitude == pytest.approx(100.0)
    assert r1_param.number_of_cycles == 2

    assert ecsa.results[0].runs[0].scan_rate is not None
    assert ecsa.results[0].runs[0].scan_rate.to('volt / second').magnitude == pytest.approx(0.02)
    assert ecsa.results[0].runs[1].scan_rate is not None
    assert ecsa.results[0].runs[1].scan_rate.to('volt / second').magnitude == pytest.approx(0.1)
