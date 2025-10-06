def test_importing_api():
    # this will raise an exception if pydantic model validation fails for th app
    from nomad_ait_echt_oasis.apis import api_entry_point

    assert api_entry_point.prefix == 'new_api'
