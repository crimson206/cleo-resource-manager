"""Configuration management core functionality."""

import json
from pathlib import Path
from typing import Any, Dict, Optional, List, Iterator, Tuple


class Config:
    """Configuration wrapper class."""

    def __init__(self, config_data: Dict[str, Any]):
        self._config = config_data or {}
        self._validate_config()

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation."""
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                # Handle array index access (e.g. "github[0]")
                if "[" in k and "]" in k:
                    array_key, index = k.split("[")
                    index = int(index.rstrip("]"))
                    if array_key not in value or not isinstance(value[array_key], list):
                        return default
                    if index >= len(value[array_key]):
                        return default
                    value = value[array_key][index]
                else:
                    value = value.get(k, default)
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation."""
        keys = key.split(".")
        config = self._config

        for k in keys[:-1]:
            if "[" in k and "]" in k:
                array_key, index = k.split("[")
                index = int(index.rstrip("]"))
                if array_key not in config:
                    config[array_key] = []
                while len(config[array_key]) <= index:
                    config[array_key].append({})
                config = config[array_key][index]
            else:
                if k not in config:
                    config[k] = {}
                config = config[k]

        last_key = keys[-1]
        if "[" in last_key and "]" in last_key:
            array_key, index = last_key.split("[")
            index = int(index.rstrip("]"))
            if array_key not in config:
                config[array_key] = []
            while len(config[array_key]) <= index:
                config[array_key].append({})
            config[array_key][index] = value
        else:
            config[last_key] = value

        self._validate_config()

    def items(self) -> Iterator[Tuple[str, Any]]:
        """Get all configuration items as iterator of (key, value) pairs."""
        return iter(self._config.items())

    def keys(self) -> Iterator[str]:
        """Get all configuration keys."""
        return iter(self._config.keys())

    def values(self) -> Iterator[Any]:
        """Get all configuration values."""
        return iter(self._config.values())

    def get_providers(self, provider_type: str) -> List[Dict[str, Any]]:
        """Get providers of specific type."""
        return self.get(f"providers.{provider_type}", [])

    def get_enabled_providers(self, provider_type: str) -> List[Dict[str, Any]]:
        """Get enabled providers of specific type."""
        providers = self.get_providers(provider_type)
        return [p for p in providers if p.get("enabled", True)]

    def _validate_config(self) -> None:
        """Validate configuration structure."""
        if not isinstance(self._config, dict):
            raise ValueError("Configuration must be a dictionary")

        # Initialize providers if not present
        if "providers" not in self._config:
            self._config["providers"] = {"github": [], "local": []}

        # Validate providers
        providers = self._config["providers"]
        if not isinstance(providers, dict):
            raise ValueError("Providers must be a dictionary")

        # Initialize provider types if not present
        if "github" not in providers:
            providers["github"] = []
        if "local" not in providers:
            providers["local"] = []

        # Validate GitHub providers
        github_providers = providers["github"]
        if not isinstance(github_providers, list):
            raise ValueError("GitHub providers must be a list")

        for provider in github_providers:
            if not isinstance(provider, dict):
                raise ValueError("GitHub provider must be a dictionary")
            if "name" not in provider:
                raise ValueError("GitHub provider must have a name")
            if "url" not in provider:
                raise ValueError("GitHub provider must have a URL")

        # Validate Local providers
        local_providers = providers["local"]
        if not isinstance(local_providers, list):
            raise ValueError("Local providers must be a list")

        for provider in local_providers:
            if not isinstance(provider, dict):
                raise ValueError("Local provider must be a dictionary")
            if "name" not in provider:
                raise ValueError("Local provider must have a name")
            if "path" not in provider:
                raise ValueError("Local provider must have a path")

        # Initialize and validate auth section
        if "auth" not in self._config:
            self._config["auth"] = {"github": {"method": "auto"}}

        auth = self._config["auth"]
        if not isinstance(auth, dict):
            raise ValueError("Auth must be a dictionary")

        # Initialize GitHub auth if not present
        if "github" not in auth:
            auth["github"] = {"method": "auto"}

        github_auth = auth["github"]
        if not isinstance(github_auth, dict):
            raise ValueError("GitHub auth must be a dictionary")

        # Validate auth method
        auth_method = github_auth.get("method", "auto")
        valid_methods = ["default", "auto", "dotenv", "gitcli"]
        if auth_method not in valid_methods:
            raise ValueError(
                f"Invalid auth method '{auth_method}'. Must be one of: {', '.join(valid_methods)}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self._config.copy()

    def __getitem__(self, key: str) -> Any:
        """Get configuration value using dictionary syntax."""
        return self._config[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Set configuration value using dictionary syntax."""
        self._config[key] = value
        self._validate_config()

    def __contains__(self, key: str) -> bool:
        """Check if key exists in configuration."""
        return key in self._config

    def __iter__(self):
        """Iterate over configuration keys."""
        return iter(self._config)

    def __len__(self) -> int:
        """Get number of configuration items."""
        return len(self._config)

    def __bool__(self) -> bool:
        """Check if config is not empty."""
        return bool(self._config)


class ConfigManager:
    """Core configuration management functionality."""

    def __init__(
        self,
        config_dir: Path = None,
        config_file: str = "config.json",
    ):
        if config_dir is None:
            config_dir = Path.cwd() / ".resource-manager"

        self.config_dir = config_dir
        self.config_file = config_file
        self.config_path = config_dir / config_file

    def init(self) -> None:
        """Initialize empty configuration."""
        config = Config({"providers": {"github": [], "local": []}})
        self.save_config(config)

    def load_config(self) -> Optional[Config]:
        """Load configuration from file."""
        if not self.config_path.exists():
            return None

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return Config(data)
        except Exception as e:
            raise RuntimeError(f"Failed to load config: {e}")

    def save_config(self, config: Config) -> None:
        """Save configuration to file."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config.to_dict(), f, indent=2)
        except Exception as e:
            raise RuntimeError(f"Failed to save config: {e}")

    def create_sample_config(self) -> Path:
        """Create a sample configuration file."""
        sample_config = {
            "auth": {"github": {"method": "auto"}},
            "providers": {
                "github": [
                    {
                        "name": "example-github",
                        "enabled": True,
                        "url": "https://github.com/owner/repo",
                        "default_branch": "main",
                        "resource_dir": "resources",
                        "timeout": 10,
                    }
                ],
                "local": [
                    {
                        "name": "example-local",
                        "enabled": True,
                        "path": "./local-resources",
                    }
                ],
            },
            "resources": {
                "include_patterns": ["*.txt", "*.md"],
                "exclude_patterns": [".git", "__pycache__", "*.pyc"],
            },
        }

        config = Config(sample_config)
        self.save_config(config)
        return self.config_path

    def validate_config(self, config: Config) -> bool:
        """Validate configuration."""
        if not config:
            return False

        try:
            # Basic structure validation
            if not isinstance(config.to_dict(), dict):
                return False

            # Check if providers exist
            providers = config.get("providers")
            if not isinstance(providers, dict):
                return False

            # Check GitHub providers
            github_providers = config.get("providers.github", [])
            if not isinstance(github_providers, list):
                return False

            for provider in github_providers:
                if not isinstance(provider, dict):
                    return False
                if "name" not in provider or "url" not in provider:
                    return False

            # Check local providers
            local_providers = config.get("providers.local", [])
            if not isinstance(local_providers, list):
                return False

            for provider in local_providers:
                if not isinstance(provider, dict):
                    return False
                if "name" not in provider or "path" not in provider:
                    return False

            # Check auth section
            auth = config.get("auth", {})
            if auth and not isinstance(auth, dict):
                return False

            # Check GitHub auth
            github_auth = config.get("auth.github", {})
            if github_auth:
                if not isinstance(github_auth, dict):
                    return False

                auth_method = github_auth.get("method", "auto")
                valid_methods = ["default", "auto", "dotenv", "gitcli"]
                if auth_method not in valid_methods:
                    return False

            return True

        except Exception:
            return False

    def get_config_info(self) -> Dict[str, Any]:
        """Get configuration information."""
        config = self.load_config()
        return {
            "path": str(self.config_path),
            "exists": self.config_path.exists(),
            "valid": self.validate_config(config) if config else False,
            "has_providers": (
                bool(config and config.get("providers")) if config else False
            ),
        }
