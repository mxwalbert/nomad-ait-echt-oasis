from nomad_material_processing.vapor_deposition.general import SubstrateHolderPosition
from nomad_ait_echt_oasis.schema_packages.infrastructure import LIMSDeviceReference
from nomad_ait_echt_oasis.schema_packages.sputter_deposition.v0 import (
    SputterCathodeReference,
    SputterDeposition,
    SputterDepositionStep,
    SputterInstrument,
    SputterPowerSupply,
    SputterPowerSupplyReference,
    SputterSource,
    SputterSourceConfiguration,
    sputter_mode_values,
    SamplePosition,
    SputterSampleParameters,
    SputterSubstrateHolder,
    SputterSubstrateHolderReference,
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
    holder_pos = SubstrateHolderPosition(name='Pos1', x_position=0.01, y_position=0.02)
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
