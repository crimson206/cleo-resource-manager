"""Configuration management core functionality."""

import json
from pathlib import Path
from typing import Any, Dict, Optional, List


class Config:
    """Configuration wrapper class."""

    def __init__(self, config_data: Dict[str, Any]):
        self._config = config_data
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

    def items(self) -> Dict[str, Any]:
        """Get all configuration items."""
        return self._config

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


# Default configuration schema with documentation
DEFAULT_CONFIG_SCHEMA = {
    "cache": {
        "max_age_hours": {
            "type": int,
            "default": 24,
            "description": "Maximum age of cache entries in hours"
        },
        "enabled": {
            "type": bool,
            "default": True,
            "description": "Whether caching is enabled"
        }
    },
    "providers": {
        "type": "object",
        "description": "Resource provider configuration",
        "properties": {
            "github": {
                "type": "array",
                "description": "GitHub provider configurations",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": str,
                            "description": "Unique name for this provider"
                        },
                        "enabled": {
                            "type": bool,
                            "default": True,
                            "description": "Whether this provider is enabled"
                        },
                        "timeout": {
                            "type": int,
                            "default": 10,
                            "description": "Timeout for GitHub API requests in seconds"
                        },
                        "default_branch": {
                            "type": str,
                            "default": "main",
                            "description": "Default branch to use for GitHub repositories"
                        },
                        "url": {
                            "type": str,
                            "description": "GitHub repository URL to fetch resources from",
                            "format": "uri"
                        },
                        "resource_dir": {
                            "type": str,
                            "default": "resources",
                            "description": "Directory in the repository where resources are stored"
                        }
                    },
                    "required": ["name", "url"]
                }
            },
            "local": {
                "type": "array",
                "description": "Local provider configurations",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": str,
                            "description": "Unique name for this provider"
                        },
                        "enabled": {
                            "type": bool,
                            "default": True,
                            "description": "Whether this provider is enabled"
                        },
                        "path": {
                            "type": str,
                            "description": "Path to local resources directory"
                        }
                    },
                    "required": ["name", "path"]
                }
            }
        }
    },
    "resources": {
        "default_pattern": {
            "type": str,
            "default": "*",
            "description": "Default file pattern for resource filtering"
        },
        "exclude_patterns": {
            "type": list,
            "default": [".git", "__pycache__", "*.pyc"],
            "description": "Patterns to exclude from resource collection"
        },
        "include_patterns": {
            "type": list,
            "default": [],
            "description": "Patterns to include in resource collection"
        },
        "output_dir": {
            "type": str,
            "default": "./output",
            "description": "Default directory to save downloaded resources"
        }
    }
}


class ConfigManager:
    """Core configuration management functionality."""

    def __init__(
        self,
        config_dir: Path,
        config_file: str = "config.json",
        schema: Optional[Dict] = None,
    ):
        self.config_dir = config_dir
        self.config_file = config_file
        self.schema = schema or DEFAULT_CONFIG_SCHEMA
        self.config_path = config_dir / config_file

    def init(self) -> None:
        """Initialize empty configuration."""
        config = Config({
            "providers": {
                "github": [],
                "local": []
            }
        })
        self.save_config(config)

    def load_config(self) -> Config:
        """Load configuration from file."""
        if not self.config_path.exists():
            return Config({
                "providers": {
                    "github": [],
                    "local": []
                }
            })

        try:
            with open(self.config_path, "r") as f:
                return Config(json.load(f))
        except Exception as e:
            raise RuntimeError(f"Failed to load config: {e}")

    def save_config(self, config: Config) -> None:
        """Save configuration to file."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w") as f:
                json.dump(config._config, f, indent=2)
        except Exception as e:
            raise RuntimeError(f"Failed to save config: {e}")

    def create_sample_config(self) -> Path:
        """Create a sample configuration file."""
        sample_config = {
            "providers": {
                "github": [],
                "local": []
            }
        }
        self.save_config(Config(sample_config))
        return self.config_path

    def validate_config(self, config: Config) -> bool:
        """Validate configuration against schema."""
        if not self.schema:
            return True

        try:
            self._validate_dict(config._config, self.schema)
            return True
        except ValueError:
            return False

    def get_config_info(self) -> Dict[str, Any]:
        """Get configuration information."""
        config = self.load_config()
        return {
            "path": str(self.config_path),
            "exists": self.config_path.exists(),
            "valid": self.validate_config(config),
            "schema_defined": bool(self.schema),
        }

    def _generate_sample_config(self) -> Dict:
        """Generate sample configuration based on schema."""
        if not self.schema:
            return {}

        def _generate_value(value: Dict) -> Any:
            if "type" in value:
                return value.get("default", None)
            return {k: _generate_value(v) for k, v in value.items()}

        return _generate_value(self.schema)

    def _validate_dict(self, data: Dict, schema: Dict) -> None:
        """Validate dictionary against schema."""
        for key, value in schema.items():
            if key not in data:
                if value.get("required", False):
                    raise ValueError(f"Missing required key: {key}")
                continue

            if isinstance(value, dict) and "type" not in value:
                if not isinstance(data[key], dict):
                    raise ValueError(f"Expected dict for key: {key}")
                self._validate_dict(data[key], value)
            else:
                expected_type = value.get("type", type(None))
                if not isinstance(data[key], expected_type):
                    raise ValueError(
                        f"Invalid type for key {key}: expected {expected_type.__name__}"
                    ) 