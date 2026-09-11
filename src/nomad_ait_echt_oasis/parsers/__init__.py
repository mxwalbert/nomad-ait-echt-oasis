from nomad.config.models.plugins import ParserEntryPoint
from pydantic import Field


class NewParserEntryPoint(ParserEntryPoint):
    parameter: int = Field(0, description='Custom configuration parameter')

    def load(self):
        from nomad_ait_echt_oasis.parsers.parser import NewParser

        return NewParser(**self.model_dump())


parser_entry_point = NewParserEntryPoint(
    name='NewParser',
    description='New parser entry point configuration.',
    mainfile_name_re=r'.*\.newmainfilename',
)


class XYPECParserEntryPoint(ParserEntryPoint):
    def load(self):
        from nomad_ait_echt_oasis.parsers.xy_pec import XYPECParser

        return XYPECParser(**self.model_dump())


xy_pec_parser = XYPECParserEntryPoint(
    name='XYPECParser',
    description='Parser for NOMAD CAMELS XY-PEC measurement files.',
    mainfile_name_re=r'^.*\.h5$',
    mainfile_mime_re=r'(application/x-hdf)',
)
