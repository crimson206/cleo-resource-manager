"""Tests for resource providers."""

import pytest
from unittest.mock import patch

from resource_manager.core.config import Config

from resource_manager.core.provider_getter import get_provider, get_all_providers
from resource_manager.providers.local import LocalProvider
from resource_manager.providers.github.core import GitHubProvider


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return Config(
        {
            "providers": {
                "github": [
                    {
                        "name": "test-github",
                        "enabled": True,
                        "url": "https://github.com/test/repo",
                        "default_branch": "main",
                        "resource_dir": "resources",
                    },
                    {
                        "name": "test-github-real",
                        "enabled": True,
                        "url": "https://github.com/crimson206/cleo-resource-manager",
                        "default_branch": "dev",
                        "resource_dir": "tests/environment/sample_outputs/remote_resource",
                    },
                ],
                "local": [
                    {"name": "test-local", "enabled": True, "path": "./local-resources"}
                ],
            },
            "resources": {
                "include_patterns": ["*.txt"],
                "exclude_patterns": [".git", "*.pyc"],
            },
        }
    )


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


@pytest.fixture
def github_provider_real(sample_config):
    """Create a GitHubProvider instance for testing with real repository."""
    provider_config = sample_config.get_providers("github")[1]
    return GitHubProvider(sample_config, provider_config)


def test_local_provider_download_folder(local_provider, tmp_path):
    """Test LocalProvider download_folder functionality."""
    # Setup source directory with test files
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "test1.txt").write_text("content 1")
    (source_dir / "test2.txt").write_text("content 2")
    (source_dir / "test.pyc").write_text("compiled")  # Should be excluded

    # Setup target directory
    target_dir = tmp_path / "target"

    # Update provider path
    local_provider.base_path = source_dir

    # Test download_folder
    downloaded_files = local_provider.download_folder(str(target_dir))

    # Check results
    assert len(downloaded_files) == 2  # Only .txt files due to filtering
    assert "test1.txt" in downloaded_files
    assert "test2.txt" in downloaded_files
    assert "test.pyc" not in downloaded_files  # Excluded by pattern

    # Check files were actually created
    assert (target_dir / "test1.txt").exists()
    assert (target_dir / "test2.txt").exists()
    assert (target_dir / "test1.txt").read_text() == "content 1"
    assert (target_dir / "test2.txt").read_text() == "content 2"


def test_local_provider_basic_functionality(local_provider, tmp_path):
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

    # Test is_available
    assert local_provider.is_available()


@patch("requests.get")
def test_github_provider_basic_functionality(mock_get, github_provider):
    """Test basic GitHubProvider functionality."""
    # Mock exists check
    mock_get.return_value.status_code = 200

    # Test exists
    assert github_provider.exists("test.txt")

    # Test exists with non-existent file
    mock_get.return_value.status_code = 404
    assert not github_provider.exists("nonexistent.txt")


@pytest.mark.integration
def test_github_provider_real_exists(github_provider_real):
    """Test GitHubProvider with real remote files."""
    # 실제 존재하는 파일들
    assert github_provider_real.exists("test_file1.txt")
    assert github_provider_real.exists("test_file2.txt")
    assert github_provider_real.exists("nested_folder/test_file3.txt")

    # 없는 파일
    assert not github_provider_real.exists("not_exist.txt")


@pytest.mark.integration
def test_github_provider_real_download(github_provider_real, tmp_path):
    """Test GitHubProvider download with real repository."""
    target_dir = tmp_path / "real_download"

    # Test download_folder
    downloaded_files = github_provider_real.download_folder(str(target_dir))

    # Should have downloaded some files
    assert len(downloaded_files) > 0

    # Check that files were actually created
    for file_name in downloaded_files:
        file_path = target_dir / file_name
        assert file_path.exists()
        assert file_path.stat().st_size > 0  # File should have content


def test_provider_disabled(sample_config):
    """Test disabled provider behavior."""
    # Create disabled provider
    provider_config = sample_config.get_providers("github")[0]
    provider_config["enabled"] = False
    provider = GitHubProvider(sample_config, provider_config)

    # Test disabled behavior
    assert not provider.is_available()
    assert len(provider.download_folder("/tmp")) == 0


def test_get_provider(sample_config):
    """Test provider factory functions."""
    # Test get_provider
    provider = get_provider(sample_config, "github", "test-github")
    assert isinstance(provider, GitHubProvider)
    assert provider.name == "test-github"

    # Test get_all_providers
    providers = get_all_providers(sample_config)
    assert len(providers) == 3
    assert any(isinstance(p, GitHubProvider) for p in providers)
    assert any(isinstance(p, LocalProvider) for p in providers)


def test_pattern_filtering(local_provider, tmp_path):
    """Test file pattern filtering."""
    # Setup test files
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "test.txt").write_text("text file")
    (source_dir / "script.py").write_text("python file")
    (source_dir / "data.json").write_text("json file")

    target_dir = tmp_path / "target"
    local_provider.base_path = source_dir

    # Test with specific pattern
    downloaded_files = local_provider.download_folder(str(target_dir), "*.py")

    # Should only download .py files, but also filtered by include_patterns (*.txt)
    # So nothing should be downloaded since *.py doesn't match *.txt pattern
    assert len(downloaded_files) == 0

    # Test with txt pattern
    downloaded_files = local_provider.download_folder(str(target_dir), "*.txt")
    assert len(downloaded_files) == 1
    assert "test.txt" in downloaded_files


def test_github_provider_auth_integration(sample_config):
    """Test GitHubProvider with real auth functions."""
    config_data = {
        "auth": {"github": {"method": "dotenv"}},
        "providers": {
            "github": [{"name": "test", "url": "https://github.com/test/repo"}]
        },
    }

    config = Config(config_data)
    provider_config = config.get_providers("github")[0]

    # 실제 auth 함수가 호출됨
    provider = GitHubProvider(config, provider_config)
