import numpy as np
import pytest
from nomad_material_processing.vapor_deposition.pvd.general import SourcePower
from nomad_material_processing.vapor_deposition.general import Temperature
from nomad_ait_echt_oasis.schema_packages.infrastructure import LIMSDeviceReference
from nomad_ait_echt_oasis.schema_packages.sputter_deposition.v0 import (
    SputterCathodeReference,
    SputterDeposition,
    SputterDepositionStep,
    SputterGrowthRate,
    SputterInstrument,
    SputterPowerSupply,
    SputterPowerSupplyReference,
    SputterSource,
    SputterSourceConfiguration,
    SputterThicknessCalibration,
    SputterThicknessCalibrationReference,
    sputter_mode_values,
    SamplePosition,
    SputterSampleParameters,
    SputterSubstrateHolder,
    SputterSubstrateHolderReference,
    DCSputterPowerSupplyReference,
    RFSputterPowerSupplyReference,
    PowerSupplyVoltage,
    PowerSupplyCurrent,
    PowerSupplyPower,
    SputterSubstrateHeater,
    SputterSubstrateHeaterReference,
    SputterChamberEnvironment,
)


def test_sputter_instrument_normalize(archive):
    instrument = SputterInstrument()
    cathode1_ref = SputterCathodeReference(name='cathode1')
    cathode2_ref = SputterCathodeReference(name='cathode2')
    power1_supply_ref = SputterPowerSupplyReference(name='ps1')
    power2_supply_ref = SputterPowerSupplyReference(name='ps2')
    device1_ref = LIMSDeviceReference(name='device')

    instrument.sub_devices = [cathode1_ref, power1_supply_ref, device1_ref]
    instrument.cathodes = [cathode2_ref]
    instrument.power_supplies = [power2_supply_ref]

    instrument.normalize(archive, None)

    assert len(instrument.cathodes) == 2
    assert set(instrument.cathodes) == {cathode1_ref, cathode2_ref}

    assert len(instrument.power_supplies) == 2
    assert set(instrument.power_supplies) == {power1_supply_ref, power2_supply_ref}

    assert len(instrument.sub_devices) == 1
    assert instrument.sub_devices[0] == device1_ref


def test_sputter_modes_assignment(archive):
    """Test that SputterPowerSupply accepts a list of modes and SputterSource accepts a scalar mode."""
    ps = SputterPowerSupply()
    ps.supported_modes = ['Direct Current (DC)', 'Radio Frequency (RF)']

    source = SputterSource()
    source.mode = 'Pulsed Direct Current (PDMS)'

    ps.normalize(archive, None)
    source.normalize(archive, None)

    assert len(ps.supported_modes) == 2
    assert ps.supported_modes[0] == 'Direct Current (DC)'
    assert ps.supported_modes[1] == 'Radio Frequency (RF)'
    assert source.mode == 'Pulsed Direct Current (PDMS)'


def test_sputter_deposition_hierarchy(archive):
    """Test instantiating the full hierarchy for a SputterDeposition process."""
    dep = SputterDeposition()

    step = SputterDepositionStep()
    config = SputterSourceConfiguration()
    source = SputterSource()

    source.mode = sputter_mode_values[0]  # 'Direct Current (DC)'
    config.vapor_source = source
    step.sources = [config]
    dep.steps = [step]

    dep.normalize(archive, None)

    assert len(dep.steps) == 1
    assert len(dep.steps[0].sources) == 1
    assert dep.steps[0].sources[0].vapor_source.mode == 'Direct Current (DC)'


def test_sample_position_normalize(archive):
    """Test that SamplePosition infers its name from coordinates when not provided."""
    pos = SamplePosition()
    pos.x_coordinate = 0.015  # 15 mm
    pos.y_coordinate = -0.005 # -5 mm

    pos.normalize(archive, None)

    assert pos.name == '15.00,-5.00'

    # Test that name is not overwritten if already provided
    pos2 = SamplePosition()
    pos2.x_coordinate = 0.010
    pos2.y_coordinate = 0.010
    pos2.name = 'CustomName'

    pos2.normalize(archive, None)

    assert pos2.name == 'CustomName'


def test_sputter_sample_and_holder(archive):
    """Test instantiating and assigning SputterSampleParameters and SputterSubstrateHolderReference."""
    step = SputterDepositionStep()

    pos = SamplePosition(x_coordinate=0.01, y_coordinate=0.0)
    sample_param = SputterSampleParameters(position=pos)
    
    holder = SputterSubstrateHolder()
    holder_ref = SputterSubstrateHolderReference(reference=holder)
    # Default rotation speed should be 0.0
    assert holder_ref.rotation_speed == 0.0
    holder_ref.rotation_speed = 10.5

    step.sample_parameters = [sample_param]
    step.substrate_holder = holder_ref

    step.normalize(archive, None)

    assert len(step.sample_parameters) == 1
    assert step.sample_parameters[0].position.x_coordinate.magnitude == 0.01
    assert step.substrate_holder.rotation_speed.magnitude == 10.5
    assert step.substrate_holder.reference == holder


def test_sputter_deposition_step_normalize(archive):
    """Test that SamplePosition inherits coordinates from the substrate holder."""
    
    holder = SputterSubstrateHolder()
    holder_pos = SamplePosition(name='Pos1', x_coordinate=0.01, y_coordinate=0.02)
    holder.positions = [holder_pos]
    
    holder_ref = SputterSubstrateHolderReference(reference=holder)
    
    sample_pos = SamplePosition(name='Pos1')
    sample_param = SputterSampleParameters(position=sample_pos)
    
    step = SputterDepositionStep()
    step.substrate_holder = holder_ref
    step.sample_parameters = [sample_param]
    
    step.normalize(archive, None)
    
    assert sample_pos.x_coordinate.magnitude == 0.01
    assert sample_pos.y_coordinate.magnitude == 0.02


def test_sputter_power_supply_reference_normalize(archive):
    ps = SputterPowerSupply()
    ps.supported_modes = ['Direct Current (DC)']

    ps_ref = SputterPowerSupplyReference()
    ps_ref.reference = ps
    ps_ref.mode = 'Radio Frequency (RF)'

    class MockLogger:
        def __init__(self):
            self.warnings = []
        def warning(self, msg):
            self.warnings.append(msg)

    logger = MockLogger()
    ps_ref.normalize(archive, logger)

    assert len(logger.warnings) == 1
    assert logger.warnings[0] == 'Specified sputter mode not supported by power supply'


def test_dc_sputtering_normalize(archive):
    dc = DCSputterPowerSupplyReference()
    dc.voltage = PowerSupplyVoltage(value=[10.0])
    dc.current = PowerSupplyCurrent(value=[2.0])
    dc.power = PowerSupplyPower()

    dc.normalize(archive, None)

    assert dc.power.value[0].magnitude == 20.0


def test_rf_sputtering_normalize(archive):
    rf = RFSputterPowerSupplyReference()
    rf.forward_power = PowerSupplyPower(value=[100.0])
    rf.reflected_power = PowerSupplyPower(value=[10.0])
    rf.power = PowerSupplyPower()

    rf.normalize(archive, None)

    assert rf.power.value[0].magnitude == 90.0


def test_sputter_source_normalize(archive):
    source = SputterSource()
    ps_ref = SputterPowerSupplyReference()
    ps_ref.power = PowerSupplyPower(value=[150.0])
    source.power_supply = ps_ref
    source.power = SourcePower()

    source.normalize(archive, None)

    assert source.power.value[0].magnitude == 150.0


def test_sputter_heater_normalize(archive):
    """Test that heater configuration is copied from environment to sample parameters."""
    
    heater = SputterSubstrateHeater(heater_type='Halogen lamp')
    
    heater_ref = SputterSubstrateHeaterReference()
    heater_ref.reference = heater
    heater_ref.temperature = Temperature(value=[300.0])
    
    env = SputterChamberEnvironment()
    env.heater = heater_ref
    
    sp = SputterSampleParameters(position=SamplePosition(name='Pos1'))
    
    step = SputterDepositionStep()
    step.environment = env
    step.sample_parameters = [sp]
    
    step.normalize(archive, None)
    
    assert sp.heater == 'Halogen lamp'
    assert sp.substrate_temperature is not None
    assert sp.substrate_temperature.value[0].magnitude == 300.0


def test_sputter_growth_rate(archive):
    """Test SputterGrowthRate instantiation, quantities, and measurement_type enum."""
    growth_rate = SputterGrowthRate(
        measurement_type='QCM',
        value=[0.12, 0.15],
        time=[0.0, 30.0],
        set_value=[0.15, 0.15],
    )
    growth_rate.normalize(archive, None)

    assert growth_rate.measurement_type == 'QCM'
    np.testing.assert_allclose(np.asarray(getattr(growth_rate.value, 'magnitude', growth_rate.value)), [0.12, 0.15])
    np.testing.assert_allclose(np.asarray(getattr(growth_rate.time, 'magnitude', growth_rate.time)), [0.0, 30.0])
    np.testing.assert_allclose(np.asarray(getattr(growth_rate.set_value, 'magnitude', growth_rate.set_value)), [0.15, 0.15])


def test_sputter_thickness_calibration_and_instrument(archive):
    """Test SputterThicknessCalibration, reference section, and instrument attachment."""
    step = SputterDepositionStep(name='Deposition Step 1')
    calib = SputterThicknessCalibration(
        name='Target A Thickness Calibration',
        model_type='zero-intercept linear',
        input_values=[60.0, 120.0, 180.0],
        output_values=[12.0, 24.0, 36.0],
        step=step,
    )
    calib.normalize(archive, None)

    assert calib.step == step
    assert calib.model_coefficients is not None
    assert len(calib.model_coefficients) == 1
    assert calib.model_coefficients[0] == pytest.approx(0.2, rel=1e-3)

    calib_ref = SputterThicknessCalibrationReference(
        name='Target A Calib Ref',
        reference=calib,
    )

    instrument = SputterInstrument(
        name='Sputter System',
        calibrations=[calib_ref],
    )
    instrument.normalize(archive, None)

    assert len(instrument.calibrations) == 1
    assert instrument.calibrations[0].reference == calib
    assert instrument.calibrations[0].name == 'Target A Calib Ref'
