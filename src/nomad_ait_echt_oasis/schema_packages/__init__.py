from nomad.config.models.plugins import SchemaPackageEntryPoint


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


class ElectrochemicalCharacterizationSchema(SchemaPackageEntryPoint):
    def load(self):
        from nomad_ait_echt_oasis.schema_packages import (
            electrochemical_characterization,
        )

        return electrochemical_characterization.m_package


electrochemical_characterization = ElectrochemicalCharacterizationSchema(
    name='AIT ECHT Electrochemical Characterization Schema',
    description="""
    Schema package containing schemas for electrochemical characterization
    techniques based on the ECHO domain ontology.
    """,
)
