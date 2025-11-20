from nomad.metainfo import (
    SchemaPackage,
    Quantity,
)
from nomad.metainfo.data_type import (
    Datetime,
)
from nomad.datamodel import (
    EntryData
)
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation
)

m_package = SchemaPackage(
    name='AIT ECHT Infrastructure',
    aliases=['nomad_ait_echt_oasis.schema_packages.infrastructure'],
)


class DeviceEntry(EntryData):
    """
    Adds reoccurring quantities to a top-level section that describes a device.
    """
    vendor = Quantity(
        type=str,
        description='The manufacturer or seller of the device.',
        a_eln=ELNAnnotation(
            component='StringEditQuantity',
        )
    )
    model = Quantity(
        type=str,
        description='The specific product code of the device.',
        a_eln=ELNAnnotation(
            component='StringEditQuantity',
        )
    )
    serial = Quantity(
        type=str,
        description='The unique identification code of the device.',
        a_eln=ELNAnnotation(
            component='StringEditQuantity',
        )
    )
    activation_date = Quantity(
        type=Datetime,
        description='The day when the device was started to be used.',
        a_eln=ELNAnnotation(
            component='DateTimeEditQuantity',
        )
    )


class ConsumableEntry(EntryData):
    """
    Adds reoccurring quantities to a top-level section that describes a consumable.
    """
    vendor = Quantity(
        type=str,
        description='The manufacturer or seller of the consumable.',
        a_eln=ELNAnnotation(
            component='StringEditQuantity',
        )
    )
    batch_number = Quantity(
        type=str,
        description='The unique identification code of the manufacturing lot.',
        a_eln=ELNAnnotation(
            component='StringEditQuantity',
        )
    )
    stock_date = Quantity(
        type=Datetime,
        description='The day when the consumable was put into stock.',
        a_eln=ELNAnnotation(
            component='DateTimeEditQuantity',
        )
    )


m_package.__init_metainfo__()
