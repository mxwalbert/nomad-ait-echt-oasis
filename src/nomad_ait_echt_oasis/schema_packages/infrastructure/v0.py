from nomad.datamodel.data import (
    Category,
    EntryData,
    EntryDataCategory,
)
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.metainfo.basesections.v1 import (
    Entity,
    EntityReference,
    Instrument,
    InstrumentReference,
)
from nomad.metainfo import Quantity, SchemaPackage, Section, SubSection
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
    for laboratory inventory management.
    """

    m_def = Category(
        label='LIMS Devices',
        categories=[EntryDataCategory],
    )


class LIMSDevice(Entity, EntryData):
    """
    A device that is registered in the laboratory inventory management.

    Inherited from `BaseSection`:
        name (str)
        datetime (Datetime)
        lab_id (str)
        description (str)

    Own properties:
        vendor (str)
        model (str)
        serial (str)
        activation_date (Datetime)
        device_type (str)
    """

    m_def = Section(
        categories=[LIMSDeviceCategory],
    )

    vendor = Quantity(
        type=str,
        description="""
        The manufacturer or seller of the device.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Vendor Name',
        ),
    )
    model = Quantity(
        type=str,
        description="""
        The specific product name of the device.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Model Name',
        ),
    )
    serial = Quantity(
        type=str,
        description="""
        The unique identification code of the device.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Serial Number',
        ),
    )
    activation_date = Quantity(
        type=Datetime,
        description="""
        The day when the device was started to be used.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.DateTimeEditQuantity,
            label='Activation Date',
        ),
    )
    device_type = Quantity(
        type=str,
        description="""
        The type of device.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Device Type',
        ),
    )

    def normalize(self, archive, logger) -> None:
        """
        Fills the device_type property if empty or
        if the entry is a subclass of LIMSDevice.
        """

        super().normalize(archive, logger)

        if self.device_type is None or type(self) is not LIMSDevice:
            self.device_type = self.__class__.__name__


class LIMSDeviceReference(EntityReference):
    """
    A section used for referencing a LIMSDevice.

    Inherited from `SectionReference`:
        name (str)

    Inherited from `EntityReference`:
        lab_id (str)

    Own properties:
        reference (LIMSDevice)
    """

    reference = Quantity(
        type=LIMSDevice,
        description="""
        A reference to a `LIMSDevice` entry.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
            label='LIMSDevice reference',
        ),
    )


class LIMSInstrument(Instrument, LIMSDevice):
    """
    An instrument that is registered in the laboratory inventory management.
    The instrument can be a standalone device or contain other devices.

    Inherited from `BaseSection`:
        name (str)
        datetime (Datetime)
        lab_id (str)
        description (str)

    Inherited from `LIMSDevice`:
        vendor (str)
        model (str)
        serial (str)
        activation_date (Datetime)
        device_type (str)

    Own properties:
        sub_devices (list[LIMSDeviceReference])
    """

    sub_devices = SubSection(
        section_def=LIMSDeviceReference,
        repeats=True,
        description="""
        A list of references to `LIMSDevice` entries that are 
        part of this instrument.
        """,
    )


class LIMSInstrumentReference(InstrumentReference):
    """
    A section used for referencing a LIMSInstrument.

    Inherited from `SectionReference`:
        name (str)

    Inherited from `EntityReference`:
        lab_id (str)

    Own properties:
        reference (LIMSInstrument)
    """

    reference = Quantity(
        type=LIMSInstrument,
        description="""
        A reference to a `LIMSInstrument` entry.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
            label='LIMSInstrument reference',
        ),
    )


class LIMSConsumableCategory(EntryDataCategory):
    """
    Category for entry schemas related to consumables
    for laboratory inventory management.
    """

    m_def = Category(
        label='LIMS Consumables',
        categories=[EntryDataCategory],
    )


class LIMSConsumable(Entity, EntryData):
    """
    A consumable that is registered in the laboratory inventory management.

    Inherited from `BaseSection`:
        name (str)
        datetime (Datetime)
        lab_id (str)
        description (str)

    Own properties:
        vendor (str)
        batch_number (str)
        stock_date (Datetime)
        item_type (str)
    """

    m_def = Section(
        categories=[LIMSConsumableCategory],
    )

    vendor = Quantity(
        type=str,
        description="""
        The manufacturer or seller of the consumable.
        """,
        a_eln=ELNAnnotation(
            component='StringEditQuantity',
        ),
    )
    batch_number = Quantity(
        type=str,
        description="""
        The unique identification code of the manufacturing lot.
        """,
        a_eln=ELNAnnotation(
            component='StringEditQuantity',
        ),
    )
    stock_date = Quantity(
        type=Datetime,
        description="""
        The day when the consumable was put into stock.
        """,
        a_eln=ELNAnnotation(
            component='DateTimeEditQuantity',
        ),
    )
    item_type = Quantity(
        type=str,
        description="""
        The type of consumable.
        """,
        a_eln=ELNAnnotation(
            component='StringEditQuantity',
        ),
    )

    def normalize(self, archive, logger) -> None:
        """
        Fills the item_type property if empty or
        if the entry is a subclass of LIMSConsumable.
        """

        super().normalize(archive, logger)

        if self.item_type is None or type(self) is not LIMSConsumable:
            self.item_type = self.__class__.__name__


class LIMSConsumableReference(EntityReference):
    """
    A section used for referencing a LIMSConsumable.

    Inherited from `SectionReference`:
        name (str)

    Inherited from `EntityReference`:
        lab_id (str)

    Own properties:
        reference (LIMSConsumable)
    """

    reference = Quantity(
        type=LIMSConsumable,
        description="""
        A reference to a `LIMSConsumable` entry.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
            label='LIMSConsumable reference',
        ),
    )


m_package.__init_metainfo__()
