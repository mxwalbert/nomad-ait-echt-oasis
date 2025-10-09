from nomad.config import config
from nomad.metainfo import (
    SchemaPackage,
    Section,
)

from nomad_ait_echt_oasis.schema_packages.physical_vapor_deposition.v0 import (
    PhysicalVaporDeposition,
)

m_package = SchemaPackage(
    name='AIT ECHT Sputter Deposition',
    aliases=['nomad_ait_echt_oasis.schema_packages.sputter_deposition'],
)

configuration = config.get_plugin_entry_point(
    'nomad_ait_echt_oasis.schema_packages:sputter_deposition_v0',
)


class SputterDeposition(PhysicalVaporDeposition):
    """
    A synthesis technique where a solid target is bombarded with electrons or
    energetic ions (e.g. Ar+) causing atoms to be ejected ('sputtering'). The ejected
    atoms then deposit, as a thin-film, on a substrate.

    Synonyms:
     - sputtering
     - sputter coating
    """

    m_def = Section(
        links=['http://purl.obolibrary.org/obo/CHMO_0001364'],
    )


m_package.__init_metainfo__()
