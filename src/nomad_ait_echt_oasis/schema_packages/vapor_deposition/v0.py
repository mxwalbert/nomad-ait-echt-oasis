from nomad.config import config
from nomad.datamodel.data import (
    ArchiveSection,
)
from nomad.datamodel.metainfo.basesections import (
    BaseSection,
    CompositeSystem,
    ProcessStep,
)
from nomad.metainfo import (
    Quantity,
    SchemaPackage,
    Section,
    SubSection,
)
from nomad_material_processing.general import (
    SampleDeposition,
)

m_package = SchemaPackage(
    name='AIT ECHT Vapor Deposition',
    aliases=['nomad_ait_echt_oasis.schema_packages.vapor_deposition'],
)

configuration = config.get_plugin_entry_point(
    'nomad_ait_echt_oasis.schema_packages:vapor_deposition_v0',
)


class MaterialSource(BaseSection):
    pass


class EnergySource(BaseSection):
    pass


class VaporDepositionSource(ArchiveSection):
    material_source = SubSection(
        section_def=MaterialSource,
        description="""
        The source of the material that is being evaporated.
        Example: A sputtering target, a powder in a crucible, etc.
        """,
    )
    energy_source = SubSection(
        section_def=EnergySource,
        description="""
        The source of the energy which is used to evaporate the material.
        Example: A heater, a filament, a laser, a bubbler, etc.
        """,
    )


class GasFlow(ArchiveSection):
    """
    Section describing the flow of a gas.
    """

    m_def = Section()
    gas = SubSection(
        section_def=CompositeSystem,
    )
    flow_rate = Quantity(
        type=float,
        unit='meter ** 3 / second',
        shape=[],
    )


class ChamberEnvironment(ArchiveSection):
    m_def = Section()
    gas_flow = SubSection(
        section_def=GasFlow,
        repeats=True,
    )
    pressure = Quantity(
        type=float,
        unit='pascal',
        shape=[],
    )
    substrate_temperature = Quantity(
        type=float,
        unit='kelvin',
        shape=[],
    )


class VaporDepositionStep(ProcessStep):
    """
    A step of any vapor deposition process.
    """

    sources = SubSection(
        section_def=VaporDepositionSource,
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
     - sources:
       Both PVD and CVD involve a source material that is transformed into
       a vapor phase.
       In PVD, the source material is physically evaporated or sputtered from
       a solid target.
       In CVD, gaseous precursors undergo chemical reactions to produce a solid material
       on the substrate.
     - environment:
       The process typically takes place in a controlled environment.
       The deposition is usually affected by the pressure in the chamber.
       For some processes additional background gasses are also added.
    """

    m_def = Section(
        links=[
            'http://purl.obolibrary.org/obo/CHMO_0001314',
            'http://purl.obolibrary.org/obo/CHMO_0001356',
        ],
    )
    steps = SubSection(
        description="""
        The steps of the deposition process.
        """,
        section_def=VaporDepositionStep,
        repeats=True,
    )
    # TODO overwrite samples


m_package.__init_metainfo__()
