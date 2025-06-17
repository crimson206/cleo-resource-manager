"""Tests for resource providers."""

import os
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from cleo_resource_manager.core.config import Config
from cleo_resource_manager.core.providers import (
    GitHubProvider,
    LocalProvider,
    get_provider,
    get_all_providers
)


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return Config({
        "providers": {
            "github": [
                {
                    "name": "test-github",
                    "enabled": True,
                    "url": "https://github.com/crimson206/my-prompts",
                    "resource_dir": "prompts",
                    "default_branch": "main",
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
        "resources": {
            "include_patterns": ["*.txt"],
            "exclude_patterns": [".git", "*.pyc"]
        }
    })


@pytest.fixture
def local_provider(sample_config):
    """Create a LocalProvider instance for testing."""
    provider_config = sample_config.get_providers("local")[0]
    return LocalProvider(sample_config, provider_config)


@pytest.fixture
def github_provider(sample_config):
    """Create a GitHubProvider instance for testing."""
    provider_config = sample_config.get_providers("github")[0]
    return GitHubProvider(sample_config, provider_config)


def test_local_provider_basic(local_provider, tmp_path):
    """Test basic LocalProvider functionality."""
    # Setup test files
    test_dir = tmp_path / "local-resources"
    test_dir.mkdir()
    test_file = test_dir / "test.txt"
    test_file.write_text("test content")

    # Update provider path
    local_provider.base_path = test_dir

    # Test exists
    assert local_provider.exists("test.txt")
    assert not local_provider.exists("nonexistent.txt")

    # Test get_resource
    content = local_provider.get_resource("test.txt")
    assert content == "test content"

    # Test get_resources
    resources = local_provider.get_resources()
    assert len(resources) == 1
    assert resources[0][0] == "test.txt"
    assert resources[0][1] == "test content"


def test_local_provider_filtering(local_provider, tmp_path):
    """Test LocalProvider resource filtering."""
    # Setup test files
    test_dir = tmp_path / "local-resources"
    test_dir.mkdir()
    (test_dir / "test.txt").write_text("test content")
    (test_dir / "test.pyc").write_text("compiled")
    (test_dir / ".git").mkdir()

    # Update provider path
    local_provider.base_path = test_dir

    # Test filtering
    resources = local_provider.get_resources()
    assert len(resources) == 1  # Only test.txt should be included
    assert resources[0][0] == "test.txt"


@patch("requests.get")
def test_github_provider_basic(mock_get, github_provider):
    """Test basic GitHubProvider functionality."""
    # Mock GitHub API responses
    mock_get.return_value.json.return_value = [
        {
            "name": "commits/conventional_commits.md",
            "type": "file",
            "download_url": "https://raw.githubusercontent.com/crimson206/my-prompts/refs/heads/main/prompts/commits/conventional_commits.md"
        }
    ]
    mock_get.return_value.text = "test content"
    mock_get.return_value.status_code = 200

    # Test exists
    assert github_provider.exists("prompts/commits/conventional_commits.md")
    # assert not github_provider.exists("nonexistent.txt")

    # Test get_resource
    content = github_provider.get_resource("prompts/commits/conventional_commits.md")
    assert content == "test content"

    # Test get_resources
    resources = github_provider.get_resources()

    assert len(resources) == 1
    assert resources[0][0] == "prompts/commits/conventional_commits.md"
    assert resources[0][1] == "test content"


def test_provider_disabled(sample_config):
    """Test disabled provider behavior."""
    # Create disabled provider
    provider_config = sample_config.get_providers("github")[0]
    provider_config["enabled"] = False
    provider = GitHubProvider(sample_config, provider_config)

    # Test disabled behavior
    assert not provider.is_available()
    assert len(provider.get_resources()) == 0
    with pytest.raises(RuntimeError, match="Provider test-github is disabled"):
        provider.get_resource("test.txt")


def test_get_provider(sample_config):
    """Test provider factory functions."""
    # Test get_provider
    provider = get_provider(sample_config, "github", "test-github")
    assert isinstance(provider, GitHubProvider)
    assert provider.name == "test-github"

    # Test get_all_providers
    providers = get_all_providers(sample_config)
    assert len(providers) == 2
    assert any(isinstance(p, GitHubProvider) for p in providers)
    assert any(isinstance(p, LocalProvider) for p in providers) 