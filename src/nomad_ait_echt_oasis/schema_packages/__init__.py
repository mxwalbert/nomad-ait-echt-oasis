from nomad.config.models.plugins import SchemaPackageEntryPoint


class VaporDepositionV0(SchemaPackageEntryPoint):
    def load(self):
        from nomad_ait_echt_oasis.schema_packages.vapor_deposition.v0 import m_package

        return m_package


vapor_deposition_v0 = VaporDepositionV0(
    name='AIT ECHT Vapor Deposition Schema',
    description="""
    Schema package containing base classes for the vapor deposition process.
    """,
)


class PhysicalVaporDepositionV0(SchemaPackageEntryPoint):
    def load(self):
        from nomad_ait_echt_oasis.schema_packages.physical_vapor_deposition.v0 import (
            m_package,
        )

        return m_package


physical_vapor_deposition_v0 = PhysicalVaporDepositionV0(
    name='AIT ECHT Physical Vapor Deposition Schema',
    description="""
    Schema package containing base classes for the physical vapor deposition process.
    """,
)


class SputterDepositionV0(SchemaPackageEntryPoint):
    def load(self):
        from nomad_ait_echt_oasis.schema_packages.sputter_deposition.v0 import m_package

        return m_package


sputter_deposition_v0 = SputterDepositionV0(
    name='AIT ECHT Sputter Deposition Schema',
    description="""
    Schema package containing specific classes for the sputtering process.
    """,
)
