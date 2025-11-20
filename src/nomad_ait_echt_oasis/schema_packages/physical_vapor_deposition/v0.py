from nomad.metainfo import (
    SchemaPackage,
    Section,
    SubSection,
)
from nomad_ait_echt_oasis.schema_packages.vapor_deposition.v0 import (
    VaporDeposition, VaporDepositionStep,
)

m_package = SchemaPackage(
    name='AIT ECHT Physical Vapor Deposition',
    aliases=['nomad_ait_echt_oasis.schema_packages.physical_vapor_deposition'],
)


class PhysicalVaporDepositionStep(VaporDepositionStep):
    """
    A step of a physical vapor deposition process.
    """


class PhysicalVaporDeposition(VaporDeposition):
    """
    A synthesis technique where vaporized molecules or atoms condense on a surface,
    forming a thin layer. The process is purely physical; no chemical reaction occurs
    at the surface.

    Synonyms:
     - PVD
     - physical vapor deposition
    """
    m_def = Section(
        links=['https://purl.obolibrary.org/obo/CHMO_0001356'],
    )
    steps = SubSection(
        section_def=PhysicalVaporDepositionStep,
        repeats=True,
    )


m_package.__init_metainfo__()
