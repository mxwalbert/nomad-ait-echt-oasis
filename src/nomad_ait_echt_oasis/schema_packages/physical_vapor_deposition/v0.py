from nomad.config import config
from nomad.metainfo import (
    SchemaPackage,
    Section,
)

from nomad_ait_echt_oasis.schema_packages.vapor_deposition.v0 import (
    VaporDeposition,
)

m_package = SchemaPackage(
    name='AIT ECHT Physical Vapor Deposition',
    aliases=['nomad_ait_echt_oasis.schema_packages.physical_vapor_deposition'],
)

configuration = config.get_plugin_entry_point(
    'nomad_ait_echt_oasis.schema_packages:physical_vapor_deposition_v0',
)


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
        links=['http://purl.obolibrary.org/obo/CHMO_0001356'],
    )


m_package.__init_metainfo__()
