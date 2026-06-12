from nomad.datamodel.data import (
    Category,
    EntryData,
    EntryDataCategory,
)
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.metainfo import Quantity, SchemaPackage, Section
from nomad.metainfo.data_type import (
    Datetime,
)

m_package = SchemaPackage(
    name='AIT ECHT Infrastructure',
    aliases=['nomad_ait_echt_oasis.schema_packages.infrastructure'],
)


class LIMSDeviceCategory(EntryDataCategory):
    """
    Category for entry schemas related to devices
    for aboratory inventory management.
    """

    m_def = Category(
        label='LIMS Devices',
        categories=[EntryDataCategory],
    )


class DeviceEntry(EntryData):
    """
    Adds reoccurring quantities to a top-level section that describes a device.
    """

    m_def = Section(
        categories=[LIMSDeviceCategory],
    )

    vendor = Quantity(
        type=str,
        description='The manufacturer or seller of the device.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Vendor Name',
        ),
    )
    model = Quantity(
        type=str,
        description='The specific product name of the device.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Model Name',
        ),
    )
    serial = Quantity(
        type=str,
        description='The unique identification code of the device.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Serial Number',
        ),
    )
    activation_date = Quantity(
        type=Datetime,
        description='The day when the device was started to be used.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.DateTimeEditQuantity,
            label='Activation Date',
        ),
    )
    device_type = Quantity(
        type=str,
        description='The type of device.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Device Type',
        ),
    )

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        if self.device_type is None:
            self.device_type = self.__class__.__name__


class LIMSDConsumableCategory(EntryDataCategory):
    """
    Category for entry schemas related to consumables
    for aboratory inventory management.
    """

    m_def = Category(
        label='LIMS Consumables',
        categories=[EntryDataCategory],
    )


class ConsumableEntry(EntryData):
    """
    Adds reoccurring quantities to a top-level section that describes a consumable.
    """

    m_def = Section(
        categories=[LIMSDConsumableCategory],
    )

    vendor = Quantity(
        type=str,
        description='The manufacturer or seller of the consumable.',
        a_eln=ELNAnnotation(
            component='StringEditQuantity',
        ),
    )
    batch_number = Quantity(
        type=str,
        description='The unique identification code of the manufacturing lot.',
        a_eln=ELNAnnotation(
            component='StringEditQuantity',
        ),
    )
    stock_date = Quantity(
        type=Datetime,
        description='The day when the consumable was put into stock.',
        a_eln=ELNAnnotation(
            component='DateTimeEditQuantity',
        ),
    )
    item_type = Quantity(
        type=str,
        description='The type of consumable.',
        a_eln=ELNAnnotation(
            component='StringEditQuantity',
        ),
    )

    def normalize(self, archive, logger) -> None:
        super().normalize(archive, logger)

        if self.item_type is None:
            self.item_type = self.__class__.__name__


m_package.__init_metainfo__()
