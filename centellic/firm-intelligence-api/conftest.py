"""Keep the test suite offline, including import-time SDK/Chroma constructors."""

from unittest.mock import MagicMock, patch


def pytest_configure(config):
    claude = MagicMock()
    claude.messages.create.side_effect = AssertionError("Mock Claude in this test")
    voyage = MagicMock()
    voyage.embed.side_effect = AssertionError("Mock Voyage in this test")
    chroma = MagicMock()
    chroma.get_or_create_collection.return_value.count.return_value = 0
    patches = [
        patch.dict("os.environ", {
            "ANTHROPIC_API_KEY": "offline-test-placeholder",
            "VOYAGE_API_KEY": "offline-test-placeholder",
        }),
        patch("anthropic.Anthropic", return_value=claude),
        patch("voyageai.Client", return_value=voyage),
        patch("chromadb.PersistentClient", return_value=chroma),
    ]
    for provider_patch in patches:
        provider_patch.start()
    config._offline_provider_patches = patches


def pytest_unconfigure(config):
    for provider_patch in reversed(getattr(config, "_offline_provider_patches", [])):
        provider_patch.stop()
