from typing import TYPE_CHECKING

from nomad.datamodel.data import (
    Category,
    EntryDataCategory,
)
from nomad.metainfo import (
    SchemaPackage,
)

if TYPE_CHECKING:
    pass

m_package = SchemaPackage(
    name='AIT ECHT Mapping Analysis',
    aliases=['nomad_ait_echt_oasis.schema_packages.mapping_analysis'],
    description="""
    Schemas for the analysis of (combinatorial) mapping measurements.
    This package is based on NOMAD's Measurements and Material Processing plugins.
    The class structures are aligned with EMMO, including domain ontologies.
    """,
)


# --- Categories ---
class MappingAnalysisCategory(EntryDataCategory):
    """
    Category for mapping analysis sections.
    """

    m_def = Category(
        label='Mapping Analysis',
        categories=[EntryDataCategory],
    )


m_package.__init_metainfo__()
