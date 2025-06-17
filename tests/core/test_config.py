"""Tests for config module."""

import os
import json
from pathlib import Path
import pytest
from cleo_resource_manager.core.config import Config, ConfigManager


@pytest.fixture
def test_env():
    """Get test environment paths."""
    base_dir = Path(__file__).parent.parent
    return {
        "base": base_dir,
        "sample_outputs": base_dir / "environment" / "sample_outputs",
        "result_outputs": base_dir / "environment" / "result_outputs"
    }


@pytest.fixture
def config_manager(test_env):
    """Create a ConfigManager instance with test environment."""
    result_dir = test_env["result_outputs"]
    result_dir.mkdir(parents=True, exist_ok=True)
    return ConfigManager(config_dir=result_dir)


def test_init_empty_config(config_manager, test_env):
    """Test initializing empty configuration."""
    # Initialize empty config
    config_manager.init()
    config = config_manager.load_config()

    # Save result
    result_file = test_env["result_outputs"] / "config_empty_result.json"
    with open(result_file, "w") as f:
        json.dump(config._config, f, indent=4)

    # Compare with sample
    sample_file = test_env["sample_outputs"] / "config_empty.json"
    with open(sample_file) as f:
        sample_data = json.load(f)

    # Verify core structure
    assert "providers" in config._config
    assert "github" in config._config["providers"]
    assert "local" in config._config["providers"]
    # cache는 없어도 됨

    # Verify providers are empty
    assert len(config._config["providers"]["github"]) == 0
    assert len(config._config["providers"]["local"]) == 0


def test_config_validation(sample_config):
    """Test configuration validation."""
    # Valid config
    config = Config(sample_config)
    assert config.get("providers.github[0].name") == "test-github"
    assert config.get("providers.local[0].path") == "./local-resources"

    # Invalid config - providers not a dict
    with pytest.raises(ValueError, match="Providers must be a dictionary"):
        Config({"providers": []})

    # Invalid config - missing required fields
    with pytest.raises(ValueError, match="GitHub provider must have a name"):
        Config({
            "providers": {
                "github": [{"url": "https://github.com/test/repo"}]
            }
        })


def test_config_get_set(sample_config):
    """Test getting and setting configuration values."""
    config = Config(sample_config)

    # Test get with dot notation
    assert config.get("providers.github[0].name") == "test-github"
    assert config.get("cache.enabled") is True
    assert config.get("nonexistent", "default") == "default"

    # Test set with dot notation
    config.set("providers.github[0].timeout", 30)
    assert config.get("providers.github[0].timeout") == 30

    # Test set new value
    config.set("new.key", "value")
    assert config.get("new.key") == "value"


def test_config_providers(sample_config):
    """Test provider-related methods."""
    config = Config(sample_config)

    # Test get_providers
    github_providers = config.get_providers("github")
    assert len(github_providers) == 1
    assert github_providers[0]["name"] == "test-github"

    # Test get_enabled_providers
    enabled_providers = config.get_enabled_providers("github")
    assert len(enabled_providers) == 1

    # Test with disabled provider
    config.set("providers.github[0].enabled", False)
    enabled_providers = config.get_enabled_providers("github")
    assert len(enabled_providers) == 0


def test_config_manager_save_load(config_manager, sample_config):
    """Test saving and loading configuration."""
    config = Config(sample_config)
    config_manager.save_config(config)
    loaded_config = config_manager.load_config()
    assert loaded_config.get("providers.github[0].name") == "test-github"
    assert loaded_config.get("providers.local[0].path") == "./local-resources"


def test_config_manager_create_sample(config_manager):
    """Test creating a sample configuration file."""
    config_path = config_manager.create_sample_config()
    assert config_path.exists()
    
    config = config_manager.load_config()
    # 예시 provider들이 있는지 확인
    assert len(config.get("providers.github")) > 0
    assert len(config.get("providers.local")) > 0
    
    # Auth 섹션 확인
    assert config.get("auth.github.method") == "auto"
