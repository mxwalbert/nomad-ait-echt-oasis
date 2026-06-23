from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from nomad.datamodel.data import (
    Category,
    EntryData,
    EntryDataCategory,
)
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.metainfo.basesections import (
    ArchiveSection,
    CompositeSystem,
)
from nomad.metainfo import (
    MEnum,
    Quantity,
    SchemaPackage,
    Section,
    SubSection,
)
from nomad_material_processing.general import (
    Cylinder,
    TimeSeries,
)
from nomad_material_processing.vapor_deposition.general import (
    ChamberEnvironment,
    SubstrateHolder,
)
from nomad_material_processing.vapor_deposition.pvd.general import (
    PhysicalVaporDeposition,
    PVDEvaporationSource,
    PVDSampleParameters,
    PVDSource,
    PVDStep,
)

from nomad_ait_echt_oasis.schema_packages.infrastructure import (
    LIMSConsumable,
    LIMSConsumableReference,
    LIMSDevice,
    LIMSDeviceReference,
    LIMSInstrument,
)

m_package = SchemaPackage(
    name='AIT ECHT Sputter Deposition',
    aliases=['nomad_ait_echt_oasis.schema_packages.sputter_deposition'],
)


sputter_mode_values = (
    'Direct Current (DC)',
    'Radio Frequency (RF)',
    'Pulsed Direct Current (PDMS)',
    'High Power Impulse (HiPIMS)',
    'Other',
)


class SputterTarget(CompositeSystem, LIMSConsumable):
    """
    A consumable which is used as source of material
    in a sputter deposition process.
    """

    geometry = SubSection(section_def=Cylinder)


class SputterTargetReference(LIMSConsumableReference):
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
    Defines the spatial location and orientation of a sputter cathode,
    i.e., the target surface, relative to the center of the substrate
    holder (origin).
    """

    m_def = Section()

    x_offset = Quantity(
        type=float,
        description='The lateral offset along the X-axis.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='X offset',
            defaultDisplayUnit='millimeter',
        ),
        unit='meter',
    )
    y_offset = Quantity(
        type=float,
        description='The lateral offset along the Y-axis.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Y offset',
            defaultDisplayUnit='millimeter',
        ),
        unit='meter',
    )
    z_offset = Quantity(
        type=float,
        description='The vertical offset along the Z-axis.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Z offset',
            defaultDisplayUnit='millimeter',
        ),
        unit='meter',
    )
    tilt_angle = Quantity(
        type=float,
        description='The tilt angle of the cathode relative to the XY-plane.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Tilt angle',
            defaultDisplayUnit='degree',
        ),
        unit='degree',
    )


class SputterCathode(LIMSDevice):
    """
    A device which holds a target in a sputter deposition process.
    """

    position = SubSection(section_def=SputterCathodePosition)


class SputterCathodeReference(LIMSDeviceReference):
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


class SputterPowerSupply(LIMSDevice):
    """
    A device which supplies power to a source
    in a sputter deposition process.
    """

    supported_modes = Quantity(
        type=MEnum(*sputter_mode_values),
        shape=['*'],
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            label='Supported sputter modes',
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


class PowerSupplyPower(TimeSeries):
    """
    The power supplied by the power supply (watt).
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
        unit='watt',
    )
    set_value = Quantity(
        type=float,
        shape=['*'],
        unit='watt',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Set value',
            defaultDisplayUnit='watt',
        ),
    )


class SputterPowerSupplyReference(LIMSDeviceReference):
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
    mode = Quantity(
        type=MEnum(*sputter_mode_values),
        shape=[],
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            label='Sputter mode',
        ),
    )
    power = SubSection(
        section_def=PowerSupplyPower,
    )

    def normalize(self, archive, logger):
        super().normalize(archive, logger)

        if self.mode and self.reference and self.reference.supported_modes:
            if self.mode not in self.reference.supported_modes:
                if logger:
                    logger.warning(
                        'Specified sputter mode not supported by power supply'
                    )


class DCSputterPowerSupplyReference(SputterPowerSupplyReference):
    """
    Configuration of a DC power supply for a sputter deposition process.
    """

    mode = 'Direct Current (DC)'
    voltage = SubSection(
        section_def=PowerSupplyVoltage,
    )
    current = SubSection(
        section_def=PowerSupplyCurrent,
    )

    def normalize(self, archive, logger):
        super().normalize(archive, logger)

        if self.m_xpath('power.value') is None:
            if (
                self.m_xpath('voltage.value') is not None
                and self.m_xpath('current.value') is not None
            ):
                self.power.value = self.voltage.value * self.current.value


class RFSputterPowerSupplyReference(SputterPowerSupplyReference):
    """
    Configuration of an RF power supply for a sputter deposition process.
    """

    mode = 'Radio Frequency (RF)'
    forward_power = SubSection(
        section_def=PowerSupplyPower,
    )
    reflected_power = SubSection(
        section_def=PowerSupplyPower,
    )

    def normalize(self, archive, logger):
        super().normalize(archive, logger)

        if self.m_xpath('power.value') is None:
            if (
                self.m_xpath('forward_power.value') is not None
                and self.m_xpath('reflected_power.value') is not None
            ):
                self.power.value = self.forward_power.value - self.reflected_power.value


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

    def normalize(self, archive, logger):
        super().normalize(archive, logger)

        if self.m_xpath('power.value') is None:
            if self.m_xpath('power_supply.power.value') is not None:
                self.power.value = self.power_supply.power.value


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


class SamplePosition(ArchiveSection):
    """
    Position of a sample on a substrate holder.
    """

    m_def = Section()

    x_coordinate = Quantity(
        type=float,
        unit='meter',
        description="""
        The x coordinate of the sample position center
        relative to the center of the substrate holder.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='x coordinate',
            defaultDisplayUnit='millimeter',
        ),
    )
    y_coordinate = Quantity(
        type=float,
        unit='meter',
        description="""
        The y coordinate of the sample position center
        relative to the center of the substrate holder.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='y coordinate',
            defaultDisplayUnit='millimeter',
        ),
    )
    name = Quantity(
        type=str,
        description="""
        The short name for the sample position.
        This name is matched with the positions 
        of the substrate holder. If no name is provided, 
        it is inferred from the x and y coordinates.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='SubstrateHolderPosition name',
        ),
    )

    def normalize(self, archive, logger):
        super().normalize(archive, logger)

        if self.name is None:
            x = f'{self.x_coordinate.to("millimeter").magnitude:.2f}'
            y = f'{self.y_coordinate.to("millimeter").magnitude:.2f}'
            self.name = f'{x},{y}'


class SputterSampleParameters(PVDSampleParameters):
    """
    Parameters for a sample in a sputter deposition process.
    """

    position = SubSection(
        section_def=SamplePosition,
    )


class SputterSubstrateHolder(SubstrateHolder, LIMSDevice):
    """
    A holder for substrates in a sputter deposition process.
    """


class SputterSubstrateHolderReference(LIMSDeviceReference):
    """
    Reference to a substrate holder in a sputter deposition process.
    """

    reference = Quantity(
        type=SputterSubstrateHolder,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
            label='SputterSubstrateHolder reference',
        ),
    )
    rotation_speed = Quantity(
        type=float,
        shape=[],
        unit='rpm',
        default=0.0,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Rotation speed',
            defaultDisplayUnit='rpm',
        ),
    )


class SputterChamberEnvironment(ChamberEnvironment):
    """
    The conditions inside the chamber during a sputter deposition process.
    """


class SputterDepositionStep(PVDStep):
    """
    A step of a sputter deposition process.
    """

    sources = SubSection(
        section_def=SputterSourceConfiguration,
        repeats=True,
    )
    sample_parameters = SubSection(
        section_def=SputterSampleParameters,
        repeats=True,
    )
    substrate_holder = SubSection(
        section_def=SputterSubstrateHolderReference,
    )
    environment = SubSection(
        section_def=SputterChamberEnvironment,
    )

    def normalize(self, archive, logger):
        super().normalize(archive, logger)

        if self.sample_parameters:
            for sp in self.sample_parameters:
                pos = sp.position
                pos.normalize(archive, logger)
                substrate_holder = self.substrate_holder.reference
                if substrate_holder is None or substrate_holder.positions is None:
                    continue
                if pos.name in [p.name for p in substrate_holder.positions]:
                    pos.x_coordinate = substrate_holder.positions[pos.name].x_position
                    pos.y_coordinate = substrate_holder.positions[pos.name].y_position


class DepositionCategory(EntryDataCategory):
    """
    Category for entry schemas related to deposition experiments.
    """

    m_def = Category(
        label='Depositions',
        categories=[EntryDataCategory],
    )


class SputterInstrument(LIMSInstrument):
    """
    A tool for sputter deposition.
    """

    cathodes = SubSection(
        section_def=SputterCathodeReference,
        repeats=True,
    )
    power_supplies = SubSection(
        section_def=SputterPowerSupplyReference,
        repeats=True,
    )

    def normalize(self, archive, logger):
        super().normalize(archive, logger)

        all_sub_devices = set()
        if self.cathodes:
            all_sub_devices.update(self.cathodes)
        if self.power_supplies:
            all_sub_devices.update(self.power_supplies)
        if self.sub_devices:
            all_sub_devices.update(self.sub_devices)
        new_cathodes, new_power_supplies, new_sub_devices = [], [], []
        for ref in all_sub_devices:
            if isinstance(ref, SputterCathodeReference):
                new_cathodes.append(ref)
            elif isinstance(ref, SputterPowerSupplyReference):
                new_power_supplies.append(ref)
            else:
                new_sub_devices.append(ref)
        if new_cathodes:
            self.cathodes = new_cathodes
        if new_power_supplies:
            self.power_supplies = new_power_supplies
        if new_sub_devices:
            self.sub_devices = new_sub_devices


class SputterDeposition(PhysicalVaporDeposition, EntryData):
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
        categories=[DepositionCategory],
    )
    steps = SubSection(
        section_def=SputterDepositionStep,
        repeats=True,
    )


m_package.__init_metainfo__()
