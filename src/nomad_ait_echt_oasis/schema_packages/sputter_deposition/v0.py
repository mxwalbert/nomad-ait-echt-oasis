from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.metainfo.basesections import (
    ArchiveSection,
    CompositeSystem,
    Entity,
    EntityReference,
)
from nomad.metainfo import MEnum, Quantity, SchemaPackage, Section, SubSection
from nomad_material_processing.general import (
    Cylinder,
    TimeSeries,
)
from nomad_material_processing.vapor_deposition.pvd.general import (
    PhysicalVaporDeposition,
    PVDEvaporationSource,
    PVDSource,
    PVDStep,
)

from nomad_ait_echt_oasis.schema_packages.infrastructure import (
    ConsumableEntry,
    DeviceEntry,
)

m_package = SchemaPackage(
    name='AIT ECHT Sputter Deposition',
    aliases=['nomad_ait_echt_oasis.schema_packages.sputter_deposition'],
)


sputter_modes = MEnum(
    'Direct Current (DC)',
    'Radio Frequency (RF)',
    'Pulsed Direct Current (PDMS)',
    'High Power Impulse (HiPIMS)',
    'Other',
)


class SputterTarget(CompositeSystem, ConsumableEntry):
    """
    A consumable which is used as source of material
    in a sputter deposition process.
    """

    geometry = SubSection(section_def=Cylinder)


class SputterTargetReference(EntityReference):
    """
    Reference to a sputter target for a deposition process.
    """

    reference = Quantity(
        type=SputterTarget,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
            label='SputterTarget reference',
        ),
    )


class SputterCathodePosition(ArchiveSection):
    """
    Defines the spatial location and orientation of a sputter cathode
    relative to the substrate holder (origin).
    """

    m_def = Section()

    x = Quantity(
        type=float,
        description='The lateral offset along the X-axis.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='X offset',
            defaultDisplayUnit='millimeter',
        ),
        unit='meter',
    )
    y = Quantity(
        type=float,
        description='The lateral offset along the Y-axis.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Y offset',
            defaultDisplayUnit='millimeter',
        ),
        unit='meter',
    )
    distance_z = Quantity(
        type=float,
        description='The vertical distance along the Z-axis.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Z distance',
            defaultDisplayUnit='millimeter',
        ),
        unit='meter',
    )
    tilt_angle = Quantity(
        type=float,
        description='The tilt angle of the cathode relative to the Z-axis.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Tilt angle',
            defaultDisplayUnit='degree',
        ),
        unit='degree',
    )

    def normalize(self, archive, logger):
        super().normalize(archive, logger)


class SputterCathode(Entity, DeviceEntry):
    """
    A device which holds a target in a sputter deposition process.
    """

    position = SubSection(section_def=SputterCathodePosition)


class SputterCathodeReference(EntityReference):
    """
    Reference to a sputter cathode for a deposition process.
    """

    reference = Quantity(
        type=SputterCathode,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
            label='SputterCathode reference',
        ),
    )


class SputterPowerSupply(Entity, DeviceEntry):
    """
    A device which supplies power to a source
    in a sputter deposition process.
    """

    supported_modes = Quantity(
        type=sputter_modes,
        shape=['*'],
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            label='Supported sputter modes',
        ),
    )


class SputterPowerSupplyReference(EntityReference):
    """
    Reference to a sputter power supply for a deposition process.
    """

    reference = Quantity(
        type=SputterPowerSupply,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
            label='SputterPowerSupply reference',
        ),
    )


class PowerSupplyCurrent(TimeSeries):
    """
    The current supplied by the power supply (ampere).
    """

    m_def = Section(
        a_plot=dict(
            x='time',
            y='value',
        ),
    )
    value = Quantity(
        type=float,
        shape=['*'],
        unit='ampere',
    )
    set_value = Quantity(
        type=float,
        shape=['*'],
        unit='ampere',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Set value',
            defaultDisplayUnit='ampere',
        ),
    )


class PowerSupplyVoltage(TimeSeries):
    """
    The voltage supplied by the power supply (volt).
    """

    m_def = Section(
        a_plot=dict(
            x='time',
            y='value',
        ),
    )
    value = Quantity(
        type=float,
        shape=['*'],
        unit='volt',
    )
    set_value = Quantity(
        type=float,
        shape=['*'],
        unit='volt',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Set value',
            defaultDisplayUnit='volt',
        ),
    )


class SputterSource(PVDEvaporationSource):
    """
    A configuration of a sputter cathode and a power supply
    that are used as energy source for sputtering.
    """

    cathode = SubSection(
        section_def=SputterCathodeReference,
    )
    power_supply = SubSection(
        section_def=SputterPowerSupplyReference,
    )
    mode = Quantity(
        type=sputter_modes,
        shape=[],
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            label='Sputter mode',
        ),
    )
    voltage = SubSection(
        section_def=PowerSupplyVoltage,
    )
    current = SubSection(
        section_def=PowerSupplyCurrent,
    )
    frequency = Quantity(
        type=float,
        shape=[],
        unit='hertz',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Frequency',
            defaultDisplayUnit='hertz',
        ),
    )
    duty_cycle = Quantity(
        type=float,
        shape=[],
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Duty cycle',
        ),
    )
    reverse_voltage = Quantity(
        type=float,
        shape=[],
        unit='volt',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Reverse voltage',
            defaultDisplayUnit='volt',
        ),
    )
    pulse_width = Quantity(
        type=float,
        shape=[],
        unit='second',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Pulse width',
            defaultDisplayUnit='microsecond',
        ),
    )


class SputterSourceConfiguration(PVDSource):
    """
    Configuration of devices and consumables
    for a sputter deposition process.
    """

    material = SubSection(
        section_def=SputterTargetReference,
    )
    vapor_source = SubSection(
        section_def=SputterSource,
    )


class SputterDepositionStep(PVDStep):
    """
    A step of a sputter deposition process.
    """

    sources = SubSection(
        section_def=SputterSourceConfiguration,
        repeats=True,
    )


class SputterDeposition(PhysicalVaporDeposition):
    """
    A synthesis technique where a solid target is bombarded with electrons or
    energetic ions (e.g. Ar+) causing atoms to be ejected ('sputtering'). The ejected
    atoms then deposit as a thin-film on a substrate.

    Synonyms:
     - sputtering
     - sputter coating
    """

    m_def = Section(
        links=['https://purl.obolibrary.org/obo/CHMO_0001364'],
    )
    steps = SubSection(
        section_def=SputterDepositionStep,
        repeats=True,
    )


m_package.__init_metainfo__()
