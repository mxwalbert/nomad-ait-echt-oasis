from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )
    from structlog.stdlib import (
        BoundLogger,
    )

from nomad.metainfo import (
    SchemaPackage,
    Section,
    SubSection,
    Quantity,
    MEnum
)
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation
)
from nomad.datamodel.metainfo.basesections import (
    Entity,
    EntityReference,
)
from nomad_ait_echt_oasis.schema_packages.vapor_deposition import (
    MaterialSource,
    MaterialSourceUse,
    EnergySource,
    EnergySourceUse,
    VaporDepositionSourceConfiguration
)
from nomad_ait_echt_oasis.schema_packages.physical_vapor_deposition import (
    PhysicalVaporDeposition,
    PhysicalVaporDepositionStep,
)

m_package = SchemaPackage(
    name='AIT ECHT Sputter Deposition',
    aliases=['nomad_ait_echt_oasis.schema_packages.sputter_deposition'],
)


class SputterTarget(MaterialSource):
    """
    A consumable which is used as source of material in a sputter deposition process.
    """


class SputterTargetUse(MaterialSourceUse):
    """
    Using a sputter target in a deposition process.
    """
    reference = Quantity(
        type=SputterTarget,
        a_eln=ELNAnnotation(
            component='ReferenceEditQuantity',
            label='sputter target reference',
        ),
    )


class SputterSource(EnergySource):
    """
    A device which holds a target in a sputter deposition process.
    """


class SputterSourceUse(EnergySourceUse):
    """
    Using a sputter source in a deposition process.
    """
    reference = Quantity(
        type=SputterSource,
        a_eln=ELNAnnotation(
            component='ReferenceEditQuantity',
            label='sputter source reference',
        ),
    )


class SputterPowerSupply(Entity):
    """
    A device which supplies power to a source in a sputter deposition process.
    """
    supported_modes = Quantity(
        type=MEnum(
            'direct current',
            'radio frequency',
            'pulsed direct current',
            'high power impuls'
        ),
        shape=['*']
    )
    max_power = Quantity(
        type=float,
        unit='W',
        shape=[]
    )
    max_voltage = Quantity(
        type=float,
        unit='V',
        shape=[]
    )
    max_current = Quantity(
        type=float,
        unit='A',
        shape=[]
    )
    rf_frequency = Quantity(
        type=float,
        unit='Hz',
        shape=[]
    )


class SputterPowerSupplyUse(EntityReference):
    """
    Using a sputter power supply in a deposition process.
    """
    reference = Quantity(
        type=SputterPowerSupply,
        a_eln=ELNAnnotation(
            component='ReferenceEditQuantity',
            label='sputter power supply reference',
        ),
    )


class SputterSourceConfiguration(VaporDepositionSourceConfiguration):
    """
    Configuration of devices and consumables for a sputter deposition process.
    """
    material_source = SubSection(
        section_def=SputterTargetUse,
    )
    energy_source = SubSection(
        section_def=SputterSourceUse,
    )
    power_supply = SubSection(
        section_def=SputterPowerSupplyUse,
    )


class SputterDepositionStep(PhysicalVaporDepositionStep):
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
