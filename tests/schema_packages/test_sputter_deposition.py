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
