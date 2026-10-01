from nomad.config.models.plugins import SchemaPackageEntryPoint


class GeneralSchema(SchemaPackageEntryPoint):
    def load(self):
        from nomad_ait_echt_oasis.schema_packages.general import m_package

        return m_package


general = GeneralSchema(
    name='AIT ECHT General Schema',
    description="""
    Schema package containing base classes for general sections.
    """,
)


class InfrastructureSchema(SchemaPackageEntryPoint):
    def load(self):
        from nomad_ait_echt_oasis.schema_packages.infrastructure import m_package

        return m_package


infrastructure = InfrastructureSchema(
    name='AIT ECHT Infrastructure Schema',
    description="""
    Schema package containing base classes for pieces of infrastructure.
    """,
)


class SputterDepositionSchema(SchemaPackageEntryPoint):
    def load(self):
        from nomad_ait_echt_oasis.schema_packages.sputter_deposition import m_package

        return m_package


sputter_deposition = SputterDepositionSchema(
    name='AIT ECHT Sputter Deposition Schema',
    description="""
    Schema package containing specific classes for the sputtering process.
    """,
)


class ElectrochemicalMeasurementSchema(SchemaPackageEntryPoint):
    def load(self):
        from nomad_ait_echt_oasis.schema_packages.electrochemical_measurement import (  # noqa: E501
            m_package,
        )

        return m_package


electrochemical_measurement = ElectrochemicalMeasurementSchema(
    name='AIT ECHT Electrochemical Measurement Schema',
    description="""
    Schema package containing schemas for electrochemical characterization
    techniques based on the ECHO domain ontology.
    """,
)


class MappingAnalysisSchema(SchemaPackageEntryPoint):
    def load(self):
        from nomad_ait_echt_oasis.schema_packages.mapping_analysis import m_package

        return m_package


mapping_analysis = MappingAnalysisSchema(
    name='AIT ECHT Mapping Analysis Schema',
    description="""
    Schema package containing schemas for mapping analysis of combinatorial datasets.
    """,
)
