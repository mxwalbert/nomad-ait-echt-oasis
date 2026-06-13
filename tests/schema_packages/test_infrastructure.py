from nomad_ait_echt_oasis.schema_packages.infrastructure.v0 import (
    LIMSConsumable,
    LIMSDevice,
    LIMSInstrument,
)


def test_lims_components(archive):
    lims_device = LIMSDevice(name='device')
    lims_instrument = LIMSInstrument(name='instrument')
    lims_consumable = LIMSConsumable(name='consumable')
    lims_apple = LIMSConsumable(name='apple', item_type='fruit')

    for li in [lims_device, lims_instrument, lims_consumable, lims_apple]:
        li.normalize(archive, None)

    assert lims_device.device_type == 'LIMSDevice'
    assert lims_instrument.device_type == 'LIMSInstrument'
    assert lims_consumable.item_type == 'LIMSConsumable'
    assert lims_apple.item_type == 'fruit'
