import numpy as np
import pytest
from nomad.datamodel.metainfo.basesections import (
    CompositeSystem,
    CompositeSystemReference,
)
from nomad.datamodel.metainfo.plot import PlotSection
from nomad.units import ureg

from nomad_ait_echt_oasis.schema_packages.electrochemical_characterization import (
    CounterElectrode,
    CVCycle,
    CVParameter,
    CVResult,
    CyclicVoltammetry,
    ECSAMeasurement,
    ECSAParameter,
    ECSAResult,
    ElectrochemicalMappingResult,
    ElectrochemicalMeasurementResult,
    Electrolyte,
    FrequencyResponseAnalyser,
    Galvanostat,
    Potentiostat,
    PotentiostatReference,
    ReferenceElectrode,
    ThreeElectrodeCell,
    Voltammetry,
    WorkingElectrode,
)

EXPECTED_POTENTIOSTAT_VOLTAGE = 10.0
EXPECTED_FIGURE_COUNT = 2


def test_instruments(archive):
    """
    Test Potentiostat, Galvanostat, and FrequencyResponseAnalyser
    creation and references.
    """
    pot = Potentiostat(
        name='BioLogic SP-150',
        upper_voltage_limit=10.0 * ureg.volt,
        upper_current_limit=0.8 * ureg.ampere,
    )
    pot.normalize(archive, None)
    assert pot.device_type == 'Potentiostat'
    assert (
        pot.upper_voltage_limit.to('volt').magnitude == EXPECTED_POTENTIOSTAT_VOLTAGE
    )

    pot_ref = PotentiostatReference(reference=pot)
    assert pot_ref.reference == pot

    galv = Galvanostat(
        name='Custom Galvanostat',
        upper_voltage_limit=20.0 * ureg.volt,
        upper_current_limit=2.0 * ureg.ampere,
    )
    galv.normalize(archive, None)
    assert galv.device_type == 'Galvanostat'

    fra = FrequencyResponseAnalyser(
        name='BioLogic FRA',
        minimum_frequency=1e-3 * ureg.hertz,
        maximum_frequency=1e6 * ureg.hertz,
    )
    fra.normalize(archive, None)
    assert fra.device_type == 'FrequencyResponseAnalyser'


def test_working_electrode_and_sample_sync(archive):
    """
    Test WorkingElectrode referencing a CompositeSystem and bidirectional sample sync.
    """
    sample = CompositeSystem(name='TiN Thin Film on Glass', lab_id='AIT_TIN_001')
    sample_ref = CompositeSystemReference(
        reference=sample, lab_id=sample.lab_id, name=sample.name
    )

    we = WorkingElectrode(
        sample=sample_ref,
        surface_area=0.25 * (ureg.centimeter**2),
    )
    re = ReferenceElectrode(reference_type='Ag/AgCl (sat. KCl)')
    ce = CounterElectrode(geometry='Wire', surface_area=1.0 * (ureg.centimeter**2))
    electrolyte = Electrolyte(name='0.1M H2SO4', ph_value=1.0)

    cell = ThreeElectrodeCell(
        cell_type='Three-electrode cell',
        working_electrode=we,
        reference_electrode=re,
        counter_electrode=ce,
        electrolyte=electrolyte,
    )

    cv = CyclicVoltammetry(name='CV Test', cell=cell)
    # Measurement.samples should initially be empty, then filled during normalize
    assert not cv.samples
    cv.normalize(archive, None)

    # 1. Check sample sync: cell.working_electrode.sample -> cv.samples
    assert len(cv.samples) == 1
    assert cv.samples[0] == sample_ref

    # 2. Check reference electrode default standard potential fill
    assert re.standard_potential_vs_rhe is not None
    assert re.standard_potential_vs_rhe.to('volt').magnitude == pytest.approx(
        0.197, abs=1e-3
    )

    # 3. Check reverse sync: if cv.samples is set, working_electrode.sample is populated
    cv2 = CyclicVoltammetry(name='CV Test 2')
    cv2.samples = [sample_ref]
    cv2.cell = ThreeElectrodeCell(
        working_electrode=WorkingElectrode(surface_area=1.0 * (ureg.centimeter**2))
    )
    cv2.normalize(archive, None)
    assert cv2.cell.working_electrode.sample == sample_ref


def test_cyclic_voltammetry_normalization(archive):
    """
    Test full CyclicVoltammetry normalizer: area normalization, RHE shift,
    and plots.
    """
    # Synthetic CV data: 2 cycles between -0.2 V and +0.6 V
    # Generate triangular potential waveform: 0 -> 0.6 -> -0.2 -> 0.6 -> -0.2 -> 0
    t1 = np.linspace(0, 6, 61)  # 0 to 0.6 V
    v1 = np.linspace(0.0, 0.6, 61)

    t2 = np.linspace(6, 14, 81)  # 0.6 to -0.2 V
    v2 = np.linspace(0.6, -0.2, 81)

    t3 = np.linspace(14, 22, 81)  # -0.2 to 0.6 V
    v3 = np.linspace(-0.2, 0.6, 81)

    t4 = np.linspace(22, 30, 81)  # 0.6 to -0.2 V
    v4 = np.linspace(0.6, -0.2, 81)

    t_arr = np.concatenate([t1, t2[1:], t3[1:], t4[1:]])
    v_arr = np.concatenate([v1, v2[1:], v3[1:], v4[1:]])

    # Synthetic reversible redox wave centered at ~0.22 V:
    # Anodic peak at ~0.26 V, cathodic peak at ~0.18 V
    i_arr = 0.002 * (
        np.exp(-((v_arr - 0.26) ** 2) / 0.005) - np.exp(-((v_arr - 0.18) ** 2) / 0.005)
    )

    sample = CompositeSystem(name='Sample Glassy Carbon')
    sample_ref = CompositeSystemReference(reference=sample)

    we = WorkingElectrode(
        sample=sample_ref,
        surface_area=0.5 * (ureg.centimeter**2),  # 0.5 cm²
    )
    re = ReferenceElectrode(
        reference_type='Ag/AgCl (sat. KCl)',
        standard_potential_vs_rhe=0.197 * ureg.volt,
    )
    electrolyte = Electrolyte(name='0.5M H2SO4', ph_value=0.3)

    cv_params = CVParameter(
        initial_potential=0.0 * ureg.volt,
        lower_limit_potential=-0.2 * ureg.volt,
        upper_limit_potential=0.6 * ureg.volt,
        scan_rate=0.1 * (ureg.volt / ureg.second),
        number_of_cycles=2,
    )

    cv_cycle = CVCycle(
        cycle_index=1,
        time=t_arr * ureg.second,
        potential=v_arr * ureg.volt,
        current=i_arr * ureg.ampere,
    )

    cv_result = CVResult(
        cycles=[cv_cycle],
    )

    cv = CyclicVoltammetry(
        name='Ferri/Ferrocyanide CV',
        cell=ThreeElectrodeCell(
            working_electrode=we,
            reference_electrode=re,
            electrolyte=electrolyte,
        ),
        parameters=cv_params,
        results=[cv_result],
    )

    cv.normalize(archive, None)

    # 1. Verify current density normalization on CVCycle: J = I / Area
    assert cv_cycle.current_density is not None
    max_j = np.max(
        cv_cycle.current_density.to('milliampere / centimeter ** 2').magnitude
    )
    expected_max_j = (np.max(i_arr) / 0.5) * 1000.0
    assert max_j == pytest.approx(expected_max_j, rel=1e-3)

    # 2. Verify RHE conversion on CVCycle: E_RHE = E + 0.197 + 0.05916 * 0.3 = E + ~0.2147 V
    assert cv_cycle.potential_vs_rhe is not None
    expected_rhe = 0.0 + 0.197 + 0.05916 * 0.3
    assert cv_cycle.potential_vs_rhe[0].to('volt').magnitude == pytest.approx(
        expected_rhe, rel=1e-3
    )

    # 3. Verify cycle structure and inheritance
    assert len(cv_result.cycles) == 1
    first_cyc = cv_result.cycles[0]
    assert isinstance(first_cyc, CVCycle)
    assert isinstance(first_cyc, ElectrochemicalMeasurementResult)
    assert first_cyc.cycle_index == 1
    assert first_cyc.potential is not None
    assert first_cyc.current is not None

    # 4. Verify generated Plotly figures
    assert len(cv_result.figures) == EXPECTED_FIGURE_COUNT
    assert cv_result.figures[0].label == 'Cyclic Voltammogram'
    assert cv_result.figures[1].label == 'Potential & Current vs. Time'
    assert 'data' in cv_result.figures[0].figure


def test_cyclic_voltammetry_raw_data_cycle_splitting(archive):
    """Test auto-splitting of continuous raw data into CVCycle objects and populating cycle_index array."""
    we = WorkingElectrode(
        name='Glassy Carbon',
        surface_area=0.5 * (ureg.centimeter**2),
    )
    re = ReferenceElectrode(
        name='Ag/AgCl',
        reference_type='Ag/AgCl (sat. KCl)',
        standard_potential_vs_rhe=0.197 * ureg.volt,
    )
    electrolyte = Electrolyte(name='0.5M H2SO4', ph_value=0.3)

    cv_params = CVParameter(
        initial_potential=0.0 * ureg.volt,
        lower_limit_potential=-0.2 * ureg.volt,
        upper_limit_potential=0.6 * ureg.volt,
        scan_rate=0.1 * (ureg.volt / ureg.second),
        number_of_cycles=2,
    )

    t_arr = np.linspace(0, 16, 200)
    v_arr = np.concatenate([
        np.linspace(0, 0.6, 50),
        np.linspace(0.6, -0.2, 50),
        np.linspace(-0.2, 0.6, 50),
        np.linspace(0.6, 0.0, 50),
    ])
    i_arr = (
        0.005 * np.exp(-((v_arr - 0.25) ** 2) / 0.01)
        - 0.004 * np.exp(-((v_arr - 0.20) ** 2) / 0.01)
    )

    cv_result = CVResult(
        time=t_arr * ureg.second,
        potential=v_arr * ureg.volt,
        current=i_arr * ureg.ampere,
    )

    cv = CyclicVoltammetry(
        name='Ferri/Ferrocyanide CV Continuous',
        cell=ThreeElectrodeCell(
            working_electrode=we,
            reference_electrode=re,
            electrolyte=electrolyte,
        ),
        parameters=cv_params,
        results=[cv_result],
    )

    cv.normalize(archive, None)

    # 1. Verify cycles were decomposed and populated
    assert len(cv_result.cycles) >= 1
    assert cv_result.cycle_index is not None
    assert len(cv_result.cycle_index) == len(v_arr)
    assert cv_result.current_density is not None
    assert cv_result.potential_vs_rhe is not None

    # 2. Verify first cycle is a CVCycle
    first_cyc = cv_result.cycles[0]
    assert isinstance(first_cyc, CVCycle)
    assert isinstance(first_cyc, ElectrochemicalMeasurementResult)
    assert first_cyc.cycle_index == 1
    assert first_cyc.potential is not None
    assert first_cyc.current is not None
    assert first_cyc.current_density is not None
    assert first_cyc.potential_vs_rhe is not None

    # 3. Verify figures generated
    assert len(cv_result.figures) == EXPECTED_FIGURE_COUNT


def test_ecsa_and_normalizer(archive):
    """Test ECSAMeasurement entry and decoupled ECSA normalizer."""
    cv_params = [
        CVParameter(
            lower_limit_potential=0.1 * ureg.volt,
            upper_limit_potential=0.3 * ureg.volt,
            scan_rate=sr * (ureg.volt / ureg.second),
        )
        for sr in [0.02, 0.05, 0.10]
    ]
    ecsa_params = ECSAParameter(runs=cv_params)

    v_dense = np.linspace(0.1, 0.3, 30)
    v_arr = np.concatenate([v_dense, np.flip(v_dense)])

    cv_runs = []
    for sr in [0.02, 0.05, 0.10]:
        cdl_sim = 1e-3  # 1 mF
        i_fwd = np.full(30, cdl_sim * sr)
        i_rev = np.full(30, -cdl_sim * sr)
        i_arr = np.concatenate([i_fwd, i_rev])

        run_cv = CVResult(
            potential=v_arr * ureg.volt,
            current=i_arr * ureg.ampere,
            scan_rate=sr * (ureg.volt / ureg.second),
        )
        cv_runs.append(run_cv)

    ecsa_res = ECSAResult(
        runs=cv_runs,
        specific_capacitance=40.0 * (ureg.microfarad / (ureg.centimeter**2)),
    )

    ecsa_res.normalize(archive, None)

    ecsa = ECSAMeasurement(
        name='Test ECSA',
        cell=ThreeElectrodeCell(
            working_electrode=WorkingElectrode(
                surface_area=1.0 * (ureg.centimeter**2)
            ),
        ),
        parameters=ecsa_params,
        results=[ecsa_res],
    )

    ecsa.normalize(archive, None)

    res = ecsa.results[0]
    assert res.double_layer_capacitance is not None
    cdl_val = res.double_layer_capacitance.to('farad').magnitude
    assert cdl_val == pytest.approx(1e-3, rel=1e-2)
    assert res.scan_rates is not None
    assert len(res.scan_rates) == 3
    assert res.charging_currents is not None
    assert len(res.charging_currents) == 3
    assert res.electrochemical_surface_area is not None
    assert res.electrochemical_surface_area.to(
        'centimeter ** 2'
    ).magnitude == pytest.approx(25.0, rel=1e-2)
    assert len(res.figures) == 1
    assert res.figures[0].label == 'Cdl Determination'
    # Verify individual CV results retain their own PlotSection figures
    assert len(res.runs[0].figures) >= 1
    assert res.runs[0].figures[0].label == 'Cyclic Voltammogram'


def test_voltammetry_normalizer(archive):
    """
    Test Voltammetry.normalize method:
    - Synchronizes potentiostat into instruments list when instruments is None or empty.
    - Appends potentiostat to instruments list when instruments already contains other entries.
    - Does not duplicate potentiostat if already present in instruments.
    - Handles case where potentiostat is None.
    - Verifies base ElectrochemicalTesting normalizer runs (sample synchronization).
    """
    pot = Potentiostat(name='BioLogic SP-150')
    pot_ref = PotentiostatReference(reference=pot)

    # 1. When potentiostat is set and instruments is None/empty:
    v1 = Voltammetry(name='Voltammetry 1', potentiostat=pot_ref)
    assert not v1.instruments
    v1.normalize(archive, None)
    assert len(v1.instruments) == 1
    assert v1.instruments[0] == pot_ref

    # 2. When instruments already contains another instrument reference:
    pot2 = Potentiostat(name='Another Potentiostat')
    pot_ref2 = PotentiostatReference(reference=pot2)
    v2 = Voltammetry(name='Voltammetry 2', potentiostat=pot_ref)
    v2.instruments = [pot_ref2]
    v2.normalize(archive, None)
    assert len(v2.instruments) == 2
    assert v2.instruments[0] == pot_ref2
    assert v2.instruments[1] == pot_ref

    # 3. When potentiostat is already in instruments (no duplication):
    v3 = Voltammetry(name='Voltammetry 3', potentiostat=pot_ref)
    v3.instruments = [pot_ref]
    v3.normalize(archive, None)
    assert len(v3.instruments) == 1
    assert v3.instruments[0] == pot_ref

    # 4. When potentiostat is None:
    v4 = Voltammetry(name='Voltammetry 4')
    v4.normalize(archive, None)
    assert not v4.instruments

    # 5. Check super().normalize synchronization (sample sync via cell.working_electrode):
    sample = CompositeSystem(name='Working Sample', lab_id='WS-01')
    sample_ref = CompositeSystemReference(
        reference=sample, lab_id=sample.lab_id, name=sample.name
    )
    v5 = Voltammetry(
        name='Voltammetry 5',
        potentiostat=pot_ref,
        cell=ThreeElectrodeCell(
            working_electrode=WorkingElectrode(sample=sample_ref)
        ),
    )
    v5.normalize(archive, None)
    assert len(v5.instruments) == 1
    assert v5.instruments[0] == pot_ref
    assert len(v5.samples) == 1
    assert v5.samples[0] == sample_ref

    # 6. Check reverse synchronization (Measurement.samples -> cell.working_electrode.sample):
    v6 = Voltammetry(
        name='Voltammetry 6',
        potentiostat=pot_ref,
        samples=[sample_ref],
        cell=ThreeElectrodeCell(working_electrode=WorkingElectrode()),
    )
    v6.normalize(archive, None)
    assert v6.cell.working_electrode.sample == sample_ref



