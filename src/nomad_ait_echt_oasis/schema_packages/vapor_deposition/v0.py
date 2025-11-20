from nomad.metainfo import (
    Quantity,
    SchemaPackage,
    Section,
    SubSection,
)
from nomad.datamodel.data import (
    ArchiveSection,
)
from nomad.datamodel.metainfo.basesections import (
    Entity,
    EntityReference,
    CompositeSystem,
    ProcessStep,
)

from nomad_material_processing.general import (
    SampleDeposition, ThinFilmStackReference,
)

m_package = SchemaPackage(
    name='AIT ECHT Vapor Deposition',
    aliases=['nomad_ait_echt_oasis.schema_packages.vapor_deposition'],
)


class MaterialSource(Entity):
    """
    Entity describing the source of material to be deposited.
    """


class MaterialSourceUse(EntityReference):
    """
    Using a source of material in a vapor deposition process.
    """


class EnergySource(Entity):
    """
    Entity that describes the source of energy to generate
    and sustain a vapor phase.
    """


class EnergySourceUse(EntityReference):
    """
    Using a source of energy in a vapor deposition process.
    """


class VaporDepositionSourceConfiguration(ArchiveSection):
    """
    Coupled material and energy sources used in a vapor deposition process.
    """
    material_source = SubSection(
        section_def=MaterialSourceUse,
    )
    energy_source = SubSection(
        section_def=EnergySourceUse,
    )


class GasFlow(ArchiveSection):
    """
    Section describing the flow of a gas.
    """
    gas = SubSection(
        section_def=CompositeSystem,
    )
    flow_rate = Quantity(
        type=float,
        unit='meter ** 3 / second',
        shape=[],
        description="Volumetric flow of the gas.",
    )


class ChamberEnvironment(ArchiveSection):
    """
    Section describing the environment inside a reaction chamber.
    """
    gas_flow = SubSection(
        section_def=GasFlow,
        repeats=True,
    )
    pressure = Quantity(
        type=float,
        unit='pascal',
        shape=[],
        description="Total static pressure within the reaction chamber.",
    )
    temperature = Quantity(
        type=float,
        unit='kelvin',
        shape=[],
        description="The temperature inside the reaction chamber during the deposition.",
    )


class VaporDepositionStep(ProcessStep):
    """
    A step of any vapor deposition process.
    """
    sources = SubSection(
        section_def=VaporDepositionSourceConfiguration,
        repeats=True,
    )
    environment = SubSection(
        section_def=ChamberEnvironment,
    )


class VaporDeposition(SampleDeposition):
    """
    VaporDeposition is a general class that encompasses both Physical Vapor Deposition
    (PVD) and Chemical Vapor Deposition (CVD).
    It involves the deposition of material from a vapor phase to a solid thin film or
    coating onto a substrate.
    """
    m_def = Section(
        links=[
            'https://purl.obolibrary.org/obo/CHMO_0001314',
            'https://purl.obolibrary.org/obo/CHMO_0001356',
        ],
    )
    steps = SubSection(
        section_def=VaporDepositionStep,
        repeats=True,
    )
    samples = SubSection(
        section_def=ThinFilmStackReference,
        repeats=True,
    )


m_package.__init_metainfo__()
