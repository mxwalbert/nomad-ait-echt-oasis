from nomad.config.models.plugins import APIEntryPoint


class NewAPIEntryPoint(APIEntryPoint):

    def load(self):
        from ait_echt_oasis.apis.api import new_api

        return new_api


api_entry_point = NewAPIEntryPoint(
    prefix = 'new_api',
    name = 'NewAPI',
    description = 'New API endpoint configuration.',
)
