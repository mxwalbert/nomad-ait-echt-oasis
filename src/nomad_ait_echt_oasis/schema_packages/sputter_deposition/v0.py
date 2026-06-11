from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from nomad.datamodel.metainfo.annotations import ELNAnnotation
from nomad.datamodel.metainfo.basesections import (
    Entity,
    EntityReference,
)
from nomad.metainfo import MEnum, Quantity, SchemaPackage, Section, SubSection
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


class SputterTarget(Entity, ConsumableEntry):
    """
    A consumable which is used as source of material
    in a sputter deposition process.
    """


class SputterTargetUse(EntityReference):
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


class SputterCathode(Entity, DeviceEntry):
    """
    A device which holds a target in a sputter deposition process.
    """


class SputterCathodeUse(EntityReference):
    """
    Using a sputter cathode in a deposition process.
    """

    reference = Quantity(
        type=SputterCathode,
        a_eln=ELNAnnotation(
            component='ReferenceEditQuantity',
            label='sputter cathode reference',
        ),
    )


class SputterPowerSupply(Entity, DeviceEntry):
    """
    A device which supplies power to a source
    in a sputter deposition process.
    """

    supported_modes = Quantity(
        type=MEnum(
            'direct current',
            'radio frequency',
            'pulsed direct current',
            'high power impuls',
        ),
        shape=['*'],
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


class SputterSource(PVDEvaporationSource):
    """
    A configuration of a sputter cathode and a power supply
    that are used as energy source for sputtering.
    """

    cathode = SubSection(
        section_def=SputterCathodeUse,
    )
    power_supply = SubSection(
        section_def=SputterPowerSupplyUse,
    )


class SputterSourceConfiguration(PVDSource):
    """
    Configuration of devices and consumables
    for a sputter deposition process.
    """

    vapor_source = SubSection(
        section_def=SputterSource,
    )
    material_source = SubSection(
        section_def=SputterTargetUse,
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
