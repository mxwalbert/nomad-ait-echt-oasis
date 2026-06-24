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
    SubstrateHeater,
    Temperature,
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

heater_type_values = (
    'Halogen lamp',
    'Filament',
    'Resistive element',
    'CO2 laser',
    'Other',
)


class SputterTarget(CompositeSystem, LIMSConsumable):
    """
    A consumable which is used as source of material
    in a sputter deposition process.

    Inherited from `BaseSection`:
        name (str)
        datetime (Datetime)
        lab_id (str)
        description (str)

    Inherited from `System`:
        elemental_composition (list[ElementalComposition])

    Inherited from `CompositeSystem`:
        components (list[Component])

    Inherited from `LIMSConsumable`:
        vendor (str)
        batch_number (str)
        stock_date (Datetime)
        item_type (str)

    Own properties:
        geometry (Cylinder)
    """

    geometry = SubSection(
        section_def=Cylinder,
        description="""
        The geometry of the sputter target.
        """,
    )


class SputterTargetReference(LIMSConsumableReference):
    """
    A section used for referencing a SputterTarget.

    Inherited from `SectionReference`:
        name (str)

    Inherited from `EntityReference`:
        lab_id (str)

    Own properties:
        reference (SputterTarget)
    """

    reference = Quantity(
        type=SputterTarget,
        description="""
        A reference to a `SputterTarget` entry.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
            label='SputterTarget reference',
        ),
    )


class SputterCathodePosition(ArchiveSection):
    """
    Defines the spatial location and orientation of a sputter cathode,
    i.e., the target surface, relative to the center of the mount for
    the substrate holder.

    Own properties:
        x_offset (float)
        y_offset (float)
        z_offset (float)
        tilt_angle (float)
    """

    m_def = Section()

    x_offset = Quantity(
        type=float,
        description="""
        The lateral offset along the X-axis.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='X offset',
            defaultDisplayUnit='millimeter',
        ),
        unit='meter',
    )
    y_offset = Quantity(
        type=float,
        description="""
        The lateral offset along the Y-axis.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Y offset',
            defaultDisplayUnit='millimeter',
        ),
        unit='meter',
    )
    z_offset = Quantity(
        type=float,
        description="""
        The vertical offset along the Z-axis.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Z offset',
            defaultDisplayUnit='millimeter',
        ),
        unit='meter',
    )
    tilt_angle = Quantity(
        type=float,
        description="""
        The tilt angle of the cathode relative to the XY-plane.
        """,
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
        position (SputterCathodePosition)
    """

    position = SubSection(
        section_def=SputterCathodePosition,
        description="""
        The position of the cathode relative to the center of 
        the mount for the substrate holder.
        """,
    )


class SputterCathodeReference(LIMSDeviceReference):
    """
    A section used for referencing a SputterCathode.

    Inherited from `SectionReference`:
        name (str)

    Inherited from `EntityReference`:
        lab_id (str)

    Own properties:
        reference (SputterCathode)
    """

    reference = Quantity(
        type=SputterCathode,
        description="""
        A reference to a `SputterCathode` entry.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
            label='SputterCathode reference',
        ),
    )


class SputterPowerSupply(LIMSDevice):
    """
    A device which supplies power to a source
    in a sputter deposition process.

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
        supported_modes (list[str])
    """

    supported_modes = Quantity(
        type=MEnum(*sputter_mode_values),
        shape=['*'],
        description="""
        The modes of sputtering which can be supplied by this device.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            label='Supported sputter modes',
        ),
    )


class PowerSupplyCurrent(TimeSeries):
    """
    The current supplied by the power supply (ampere).

    Inherited from `TimeSeries`:
        set_time (np.ndarray[float])
        time (np.ndarray[float])

    Own properties:
        set_value (np.ndarray[float])
        value (np.ndarray[float])
    """

    m_def = Section(
        a_plot=dict(
            x='time',
            y='value',
        ),
    )
    set_value = Quantity(
        type=float,
        shape=['*'],
        unit='ampere',
        description="""
        The set value of the current supplied by the power supply.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Set value',
            defaultDisplayUnit='ampere',
        ),
    )
    value = Quantity(
        type=float,
        shape=['*'],
        unit='ampere',
        description="""
        The actual value of the current supplied by the power supply.
        """,
    )


class PowerSupplyVoltage(TimeSeries):
    """
    The voltage supplied by the power supply (volt).

    Inherited from `TimeSeries`:
        set_time (np.ndarray[float])
        time (np.ndarray[float])

    Own properties:
        set_value (np.ndarray[float])
        value (np.ndarray[float])
    """

    m_def = Section(
        a_plot=dict(
            x='time',
            y='value',
        ),
    )
    set_value = Quantity(
        type=float,
        shape=['*'],
        unit='volt',
        description="""
        The set value of the voltage supplied by the power supply.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Set value',
            defaultDisplayUnit='volt',
        ),
    )
    value = Quantity(
        type=float,
        shape=['*'],
        unit='volt',
        description="""
        The actual value of the voltage supplied by the power supply.
        """,
    )


class PowerSupplyPower(TimeSeries):
    """
    The power supplied by the power supply (watt).

    Inherited from `TimeSeries`:
        set_time (np.ndarray[float])
        time (np.ndarray[float])

    Own properties:
        set_value (np.ndarray[float])
        value (np.ndarray[float])
    """

    m_def = Section(
        a_plot=dict(
            x='time',
            y='value',
        ),
    )
    set_value = Quantity(
        type=float,
        shape=['*'],
        unit='watt',
        description="""
        The set value of the power supplied by the power supply.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Set value',
            defaultDisplayUnit='watt',
        ),
    )
    value = Quantity(
        type=float,
        shape=['*'],
        unit='watt',
        description="""
        The actual value of the power supplied by the power supply.
        """,
    )


class SputterPowerSupplyReference(LIMSDeviceReference):
    """
    A section used for referencing a SputterPowerSupply and
    tracking the parameters during the deposition process.

    Inherited from `SectionReference`:
        name (str)

    Inherited from `EntityReference`:
        lab_id (str)

    Own properties:
        reference (SputterPowerSupply)
        mode (str)
        power (PowerSupplyPower)
    """

    reference = Quantity(
        type=SputterPowerSupply,
        description="""
        A reference to a `SputterPowerSupply` entry.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
            label='SputterPowerSupply reference',
        ),
    )
    mode = Quantity(
        type=MEnum(*sputter_mode_values),
        shape=[],
        description="""
        The mode of sputtering which is used for this deposition process.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            label='Sputter mode',
        ),
    )
    power = SubSection(
        section_def=PowerSupplyPower,
        description="""
        The power supplied by the power supply.
        """,
    )

    def normalize(self, archive, logger):
        """
        Checks if the configured mode is supported by the referenced power supply.
        """
        super().normalize(archive, logger)

        if self.mode and self.reference and self.reference.supported_modes:
            if self.mode not in self.reference.supported_modes:
                if logger:
                    logger.warning(
                        'Specified sputter mode not supported by power supply'
                    )


class DCSputterPowerSupplyReference(SputterPowerSupplyReference):
    """
    A section used for referencing a SputterPowerSupply and
    tracking DC parameters during the deposition process.

    Inherited from `SectionReference`:
        name (str)

    Inherited from `EntityReference`:
        lab_id (str)

    Inherited from `SputterPowerSupplyReference`:
        reference (SputterPowerSupply)
        power (PowerSupplyPower)

    Own properties:
        mode (str)
        voltage (PowerSupplyVoltage)
        current (PowerSupplyCurrent)
    """

    mode = Quantity(
        type=str,
        default='Direct Current (DC)',
        description="""
        The mode of sputtering which is used for this deposition process.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Sputter mode',
        ),
        a_display={'editable': False},
    )
    voltage = SubSection(
        section_def=PowerSupplyVoltage,
        description="""
        The voltage supplied by the power supply.
        """,
    )
    current = SubSection(
        section_def=PowerSupplyCurrent,
        description="""
        The current supplied by the power supply.
        """,
    )

    def normalize(self, archive, logger):
        """
        Calculates the power from the voltage and current if not already provided.
        """

        super().normalize(archive, logger)

        if self.m_xpath('power.value') is None:
            if (
                self.m_xpath('voltage.value') is not None
                and self.m_xpath('current.value') is not None
            ):
                self.power.value = self.voltage.value * self.current.value


class RFSputterPowerSupplyReference(SputterPowerSupplyReference):
    """
    A section used for referencing a SputterPowerSupply and
    tracking RF parameters during the deposition process.

    Inherited from `SectionReference`:
        name (str)

    Inherited from `EntityReference`:
        lab_id (str)

    Inherited from `SputterPowerSupplyReference`:
        reference (SputterPowerSupply)
        power (PowerSupplyPower)

    Own properties:
        mode (str)
        forward_power (PowerSupplyPower)
        reflected_power (PowerSupplyPower)
    """

    mode = Quantity(
        type=str,
        default='Radio Frequency (RF)',
        description="""
        The mode of sputtering which is used for this deposition process.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Sputter mode',
        ),
        a_display={'editable': False},
    )
    forward_power = SubSection(
        section_def=PowerSupplyPower,
        description="""
        The forward power supplied by the power supply.
        """,
    )
    reflected_power = SubSection(
        section_def=PowerSupplyPower,
        description="""
        The reflected power measured by the power supply.
        """,
    )

    def normalize(self, archive, logger):
        """
        Calculates the power from the forward and reflected power
        if not already provided.
        """

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

    Inherited from `PVDEvaporationSource`:
        power (SourcePower)

    Own properties:
        cathode (SputterCathodeReference)
        power_supply (SputterPowerSupplyReference)
    """

    cathode = SubSection(
        section_def=SputterCathodeReference,
        description="""
        The cathode used for the deposition process.
        """,
    )
    power_supply = SubSection(
        section_def=SputterPowerSupplyReference,
        description="""
        The power supply used for the deposition process.
        """,
    )

    def normalize(self, archive, logger):
        """
        Replaces the values for the power with the ones from the power supply.
        """

        super().normalize(archive, logger)

        if self.m_xpath('power_supply.power.value') is not None:
            self.power.value = self.power_supply.power.value


class SputterSourceConfiguration(PVDSource):
    """
    Configuration of devices and consumables
    for a sputter deposition process.

    Inherited from `VaporDepositionSource`:
        name (str)
        vapor_molar_flow_rate (MolarFlowRate)

    Inherited from `PVDSource`:
        impinging_flux (ImpingingFlux)

    Own properties:
        material (SputterTargetReference)
        vapor_source (SputterSource)
    """

    material = SubSection(
        section_def=SputterTargetReference,
        description="""
        The target used for the deposition process.
        """,
    )
    vapor_source = SubSection(
        section_def=SputterSource,
        description="""
        The configuration of sputter cathode and power supply 
        used for the deposition process.
        """,
    )


class SamplePosition(ArchiveSection):
    """
    Position of a sample on a substrate holder.

    Own properties:
        x_coordinate (float)
        y_coordinate (float)
        name (str)
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
        """
        Generates the name of the sample position from the x and y coordinates
        if no name is provided.
        """

        super().normalize(archive, logger)

        if self.name is None:
            x = f'{self.x_coordinate.to("millimeter").magnitude:.2f}'
            y = f'{self.y_coordinate.to("millimeter").magnitude:.2f}'
            self.name = f'{x},{y}'


class SputterSampleParameters(PVDSampleParameters):
    """
    Parameters for a sample in a sputter deposition process.

    Inherited from `PlotSection`:
        figures (list[PlotlyFigure])

    Inherited from `SampleParameters`:
        growth_rate (GrowthRate)
        substrate_temperature (Temperature)
        layer (ThinFilmReference)
        substrate (ThinFilmStackReference)

    Inherited from `PVDSampleParameters`:
        distance_to_source (float)

    Own properties:
        heater (list[str])
        position (SamplePosition)
    """

    heater = Quantity(
        type=MEnum(*heater_type_values),
        shape=[],
        description="""
        The type of heater used for the deposition process.
        """,
        default='Other',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            label='Heater type',
        ),
    )
    position = SubSection(
        section_def=SamplePosition,
        description="""
        The position of the sample on the substrate holder.
        """,
    )


class SputterSubstrateHolder(LIMSDevice):
    """
    A holder for substrates in a sputter deposition process.

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
        height (float)
        positions (list[SamplePosition])
    """

    height = Quantity(
        type=float,
        unit='meter',
        description="""
        The height of the substrate holder.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Height',
            defaultDisplayUnit='millimeter',
        ),
    )
    positions = SubSection(
        section_def=SamplePosition,
        repeats=True,
        description="""
        The positions of the samples on the substrate holder.
        """,
    )


class SputterSubstrateHolderReference(LIMSDeviceReference):
    """
    A section used for referencing a SputterSubstrateHolder and
    tracking the parameters during the deposition process.

    Inherited from `SectionReference`:
        name (str)

    Inherited from `EntityReference`:
        lab_id (str)

    Own properties:
        reference (SputterSubstrateHolder)
        rotation_speed (float)
    """

    reference = Quantity(
        type=SputterSubstrateHolder,
        description="""
        A reference to a `SputterSubstrateHolder` entry.
        """,
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
        description="""
        The rotation speed of the substrate holder (rpm).
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Rotation speed',
            defaultDisplayUnit='rpm',
        ),
    )


class SputterSubstrateHeater(SubstrateHeater, LIMSDevice):
    """
    A heater for substrates in a sputter deposition process.

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
        heater_type (str)
    """

    heater_type = Quantity(
        type=MEnum(*heater_type_values),
        shape=[],
        description="""
        The type of heater used for the deposition process.
        """,
        default='Other',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            label='Heater type',
        ),
    )


class SputterSubstrateHeaterReference(LIMSDeviceReference):
    """
    A section used for referencing a SputterSubstrateHeater and
    tracking the parameters during the deposition process.

    Inherited from `SectionReference`:
        name (str)

    Inherited from `EntityReference`:
        lab_id (str)

    Own properties:
        reference (SputterSubstrateHeater)
        temperature (Temperature)
    """

    reference = Quantity(
        type=SputterSubstrateHeater,
        description="""
        A reference to a `SputterSubstrateHeater` entry.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
            label='SputterSubstrateHeater reference',
        ),
    )
    temperature = SubSection(
        section_def=Temperature,
        description="""
        The temperature of the substrate heater.
        """,
    )


class SputterChamberEnvironment(ChamberEnvironment):
    """
    The conditions inside the chamber during a sputter deposition process.

    Inherited from `ChamberEnvironment`:
        gas_flow (GasFlow)
        pressure (Pressure)

    Own properties:
        heater (SputterSubstrateHeaterReference)
    """

    heater = SubSection(
        section_def=SputterSubstrateHeaterReference,
        description="""
        The heater used for the deposition process.
        """,
    )


class SputterDepositionStep(PVDStep):
    """
    A step of a sputter deposition process.

    Inherited from `ActivityStep`:
        name (str)
        start_time (Datetime)
        comment (str)

    Inherited from `VaporDepositionStep`:
        creates_new_thin_film (bool)
        duration (float)

    Own properties:
        sources (list[SputterSourceConfiguration])
        sample_parameters (list[SputterSampleParameters])
        substrate_holder (SputterSubstrateHolderReference)
        environment (SputterChamberEnvironment)
    """

    sources = SubSection(
        section_def=SputterSourceConfiguration,
        repeats=True,
        description="""
        The sources used in the sputter deposition process.
        """,
    )
    sample_parameters = SubSection(
        section_def=SputterSampleParameters,
        repeats=True,
        description="""
        The parameters for the samples in the sputter deposition process.
        """,
    )
    substrate_holder = SubSection(
        section_def=SputterSubstrateHolderReference,
        description="""
        The substrate holder used in the sputter deposition process.
        """,
    )
    environment = SubSection(
        section_def=SputterChamberEnvironment,
        description="""
        The conditions inside the chamber during the sputter deposition process.
        """,
    )

    def normalize(self, archive, logger):
        """
        Replaces the coordinates of the sample parameters positions with
        the substrate holder positions if the names match.

        Copies the heater type and temperature from the environment to the
        sample parameters.
        """

        super().normalize(archive, logger)

        if self.sample_parameters:
            for sp in self.sample_parameters:
                pos = sp.position
                pos.normalize(archive, logger)

                if self.m_xpath(
                    'substrate_holder.reference.positions'
                ) is not None and pos.name in [
                    p.name for p in self.substrate_holder.reference.positions
                ]:
                    holder_positions = self.substrate_holder.reference.positions
                    pos.x_coordinate = holder_positions[pos.name].x_coordinate
                    pos.y_coordinate = holder_positions[pos.name].y_coordinate

                if self.m_xpath('environment.heater.reference') is not None:
                    sp.heater = self.environment.heater.reference.heater_type

                if self.m_xpath('environment.heater.temperature') is not None:
                    sp.substrate_temperature = self.environment.heater.temperature


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

    Inherited from LIMSInstrument:
        sub_devices (list[LIMSDeviceReference])

    Own properties:
        cathodes (list[SputterCathodeReference])
        power_supplies (list[SputterPowerSupplyReference])
    """

    cathodes = SubSection(
        section_def=SputterCathodeReference,
        repeats=True,
        description="""
        The cathodes installed in the instrument.
        """,
    )
    power_supplies = SubSection(
        section_def=SputterPowerSupplyReference,
        repeats=True,
        description="""
        The power supplies installed in the instrument.
        """,
    )

    def normalize(self, archive, logger):
        """
        Syncs the sub_devices list with the cathodes and power supplies.
        """

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

    Inherited from `Process`:
        end_time (Datetime)
        instruments (list[InstrumentReference])
        samples (list[CompositeSystemReference])

    Own properties:
        steps (list[SputterDepositionStep])
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
