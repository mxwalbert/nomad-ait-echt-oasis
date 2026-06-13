import pytest
from nomad.datamodel import EntryArchive, EntryMetadata


@pytest.fixture
def archive():
    """Returns an empty EntryArchive with metadata."""
    return EntryArchive(metadata=EntryMetadata(entry_name='test_entry'))
