"""Common test fixtures."""


import tempfile
from pathlib import Path
import pytest
from resource_manager.core.config import Config


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_config():
    """Create a sample configuration."""
    return {
        "providers": {
            "github": [
                {
                    "name": "test-github",
                    "enabled": True,
                    "url": "https://github.com/crimson206/my-prompts",
                    "resource_dir": "prompts",
                    "timeout": 10,
                    "default_branch": "main"
                }
            ],
            "local": [
                {
                    "name": "test-local",
                    "enabled": True,
                    "path": "./local-resources"
                }
            ]
        },
        "cache": {
            "enabled": True,
            "ttl": 3600
        }
    }


@pytest.fixture
def config(sample_config):
    """Create a Config instance with sample data."""
    return Config(sample_config) 