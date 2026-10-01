from typing import TYPE_CHECKING

import numpy as np
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.metainfo.basesections import (
    ActivityStep,
    ArchiveSection,
    Measurement,
    SectionReference,
)
from nomad.metainfo import (
    Quantity,
    SchemaPackage,
    Section,
    SubSection,
)

if TYPE_CHECKING:
    pass

m_package = SchemaPackage(
    name='AIT ECHT General',
    aliases=['nomad_ait_echt_oasis.schema_packages.general'],
    description="""
    Schemas for the general sections that are used across the plugin.
    This package is based on NOMAD's Measurements and Material Processing plugins.
    The class structures are aligned with EMMO, including domain ontologies.

    Ontology Namespaces:
        emmo:  https://w3id.org/emmo#
        chameo: https://w3id.org/emmo/domain/characterisation-methodology/chameo#
    """,
)


# --- Measurement Classes ---


class MeasurementReference(SectionReference):
    """
    A section used for referencing a Measurement.
    """

    reference = Quantity(
        type=Measurement,
        description='A reference to a Measurement entry.',
        a_eln=ELNAnnotation(
            component='ReferenceEditQuantity',
            label='Measurement reference',
        ),
    )


class MeasurementParameter(ArchiveSection):
    """
    Base section describing the input parameters of a generic measurement.

    Ontology:
        chameo:MeasurementParameter
        (https://w3id.org/emmo/domain/characterisation-methodology/chameo#MeasurementParameter)
    """

    m_def = Section(
        description="""
        Base parameters for a generic measurement.
        """,
    )


# --- Mapping Classes ---


class MappingStep(ActivityStep):
    """
    A single measurement step at a defined stage/sample coordinate within a mapping run.
    """

    m_def = Section(
        description="""
        A single measurement step at a defined stage/sample coordinate 
        within a mapping run.
        """,
        a_eln={
            'overview': False,
        },
    )

    x_absolute = Quantity(
        type=np.float64,
        unit='m',
        description='Absolute x position of the measurement stage.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
    )

    y_absolute = Quantity(
        type=np.float64,
        unit='m',
        description='Absolute y position of the measurement stage.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
    )

    x_relative = Quantity(
        type=np.float64,
        unit='m',
        description='Relative x position on the sample.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
    )

    y_relative = Quantity(
        type=np.float64,
        unit='m',
        description='Relative y position on the sample.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
    )

    measurement_ref = SubSection(
        section_def=MeasurementReference,
        description="""
        Reference to the stand-alone measurement entry.
        """,
    )


m_package.__init_metainfo__()
