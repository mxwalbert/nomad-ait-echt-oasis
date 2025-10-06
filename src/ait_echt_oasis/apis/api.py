from fastapi import FastAPI
from nomad.config import config

api_entry_point = config.get_plugin_entry_point('ait_echt_oasis.apis:api_entry_point')

new_api = FastAPI(
    root_path=f'{config.services.api_base_path}/{api_entry_point.prefix}'
)

@new_api.get('/')
async def root():
    return {"message": "Hello World"}
