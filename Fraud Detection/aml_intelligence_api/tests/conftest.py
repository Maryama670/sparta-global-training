"""Keep API tests offline and away from the persistent Chroma database."""

import os
import sys
from copy import deepcopy
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Import-time constructors are mocked before main/agent/knowledge_store are loaded.
# These are dummy test values, not credentials; production configuration is untouched.
_provider = MagicMock()
_provider.messages.create.side_effect = AssertionError("Mock the Claude call in this test")
_voyage = MagicMock()
_voyage.embed.side_effect = AssertionError("Mock the embedding call in this test")
_patches = [
    patch.dict(os.environ, {"VOYAGE_API_KEY": "test-only-placeholder", "ANTHROPIC_API_KEY": "test-only-placeholder"}),
    patch("anthropic.Anthropic", return_value=_provider),
    patch("voyageai.Client", return_value=_voyage),
    patch("chromadb.PersistentClient", return_value=MagicMock()),
]
for _patch in _patches:
    _patch.start()


def pytest_unconfigure(config):
    for provider_patch in reversed(_patches):
        provider_patch.stop()


@pytest.fixture(autouse=True)
def restore_seed_data():
    import data

    names = ("accounts", "counterparties", "transactions", "rules", "analysts", "alerts", "cases")
    snapshots = {name: deepcopy(getattr(data, name)) for name in names}
    yield
    # Restore in place so existing module references keep pointing to the same lists.
    for name, records in snapshots.items():
        getattr(data, name)[:] = records
