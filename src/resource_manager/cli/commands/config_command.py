"""Config command implementation."""

from pathlib import Path
from cleo.commands.command import Command
from cleo.helpers import argument, option
from typing import Any

from ...core.config import ConfigManager, Config


class ConfigCommand(Command):
    """Manage configuration."""

    name = "config"
    description = "Manage configuration"

    arguments = [
        argument(
            "action",
            "Action to perform (init, show, validate)",
            optional=False,
        ),
    ]

    options = [
        option(
            "force",
            "f",
            "Force initialization even if config exists",
            flag=True,
        ),
        option(
            "pretty",
            "p",
            "Pretty print configuration",
            flag=True,
        ),
    ]

    def handle(self):
        """Handle the command."""
        action = self.argument("action")
        config_manager = self._get_config_manager()

        try:
            if action == "init":
                return self._init_config(config_manager)
            elif action == "show":
                return self._show_config(config_manager)
            elif action == "validate":
                return self._validate_config(config_manager)
            else:
                self.line_error(f"Unknown action: {action}")
                self.line("Available actions: init, show, validate")
                return 1
        except Exception as e:
            self.line_error(f"Error: {str(e)}")
            return 1

    def _init_config(self, config_manager: ConfigManager) -> int:
        """Initialize configuration."""
        if config_manager.config_path.exists() and not self.option("force"):
            self.line_error("Configuration already exists. Use --force to overwrite.")
            return 1

        config_path = config_manager.create_sample_config()
        self.info(f"Configuration initialized at: {config_path}")
        return 0

    def _show_config(self, config_manager: ConfigManager) -> int:
        """Show current configuration."""
        config = config_manager.load_config()
        
        if not config:
            self.line("No configuration found. Use 'config init' to create configuration.")
            return 1

        if self.option("pretty"):
            self._print_config_pretty(config)
        else:
            self._print_config_simple(config)

        return 0

    def _validate_config(self, config_manager: ConfigManager) -> int:
        """Validate configuration."""
        try:
            config = config_manager.load_config()
            if not config:
                self.line_error("No configuration found to validate")
                return 1
                
            # Use the improved validation method
            if config_manager.validate_config(config):
                self.info("Configuration is valid")
                return 0
            else:
                self.line_error("Configuration is invalid")
                return 1
                
        except Exception as e:
            self.line_error(f"Error validating config: {str(e)}")
            return 1

    def _basic_config_check(self, config) -> bool:
        """Basic configuration structure check."""
        try:
            # Check if it's dict-like and has basic structure
            if not hasattr(config, 'get'):
                return False
                
            providers = config.get('providers')
            if not providers:
                return False
                
            # Check if providers has expected structure
            if not isinstance(providers, dict):
                return False
                
            # Basic checks passed
            return True
        except:
            return False

    def _get_config_manager(self) -> ConfigManager:
        """Get configuration manager."""
        config_dir = Path.cwd() / ".resource-manager"
        return ConfigManager(config_dir)

    def _print_config_simple(self, config: Config):
        """Print configuration in a simple format."""
        try:
            config_dict = config.to_dict()
            self._print_dict(config_dict, 0)
        except Exception as e:
            self.line_error(f"Error printing config: {e}")
            
    def _print_dict(self, data: dict, indent: int = 0):
        """Print dictionary recursively."""
        for key, value in data.items():
            if isinstance(value, dict):
                self.line(" " * indent + f"{key}:")
                self._print_dict(value, indent + 2)
            elif isinstance(value, list):
                self.line(" " * indent + f"{key}:")
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        self.line(" " * (indent + 2) + f"[{i}]:")
                        self._print_dict(item, indent + 4)
                    else:
                        self.line(" " * (indent + 2) + f"[{i}]: {item}")
            else:
                self.line(" " * indent + f"{key}: {value}")

    def _print_config_pretty(self, config: Config):
        """Print configuration in a pretty format."""
        self.line("\n<info>Configuration:</info>")
        
        # Print providers
        self.line("\n<comment>Providers:</comment>")
        
        # GitHub providers
        github_providers = config.get_providers("github")
        if github_providers:
            self.line("\n  <info>GitHub:</info>")
            for i, provider in enumerate(github_providers):
                self.line(f"    [{i}] {provider['name']}:")
                self.line(f"      URL: {provider.get('url', 'N/A')}")
                self.line(f"      Enabled: {provider.get('enabled', True)}")
                self.line(f"      Branch: {provider.get('default_branch', 'main')}")
                self.line(f"      Resource Dir: {provider.get('resource_dir', 'resources')}")
                self.line(f"      Timeout: {provider.get('timeout', 10)}s")
        
        # Local providers
        local_providers = config.get_providers("local")
        if local_providers:
            self.line("\n  <info>Local:</info>")
            for i, provider in enumerate(local_providers):
                self.line(f"    [{i}] {provider['name']}:")
                self.line(f"      Path: {provider.get('path', 'N/A')}")
                self.line(f"      Enabled: {provider.get('enabled', True)}")
        
        # Print resource patterns
        self.line("\n<comment>Resource Patterns:</comment>")
        include_patterns = config.get("resources.include_patterns", [])
        exclude_patterns = config.get("resources.exclude_patterns", [])
        
        if include_patterns:
            self.line(f"  Include: {', '.join(include_patterns)}")
        if exclude_patterns:
            self.line(f"  Exclude: {', '.join(exclude_patterns)}")
        
        # Print cache settings
        cache = config.get("cache", {})
        if cache:
            self.line("\n<comment>Cache:</comment>")
            self.line(f"  Enabled: {cache.get('enabled', True)}")
            self.line(f"  TTL: {cache.get('ttl', 3600)}s")
            if "dir" in cache:
                self.line(f"  Directory: {cache['dir']}")