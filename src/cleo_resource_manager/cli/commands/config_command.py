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
            "Action to perform (init, show, set, validate)",
            optional=False,
        ),
        argument(
            "key",
            "Configuration key to set (e.g. providers.github[0].url)",
            optional=True,
        ),
        argument(
            "value",
            "Configuration value to set",
            optional=True,
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
            elif action == "set":
                return self._set_config(config_manager)
            elif action == "validate":
                return self._validate_config(config_manager)
            else:
                self.line_error(f"Unknown action: {action}")
                self.line("Available actions: init, show, set, validate")
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
            self._print_config(config)

        return 0

    def _set_config(self, config_manager: ConfigManager) -> int:
        """Set configuration value."""
        key = self.argument("key")
        value = self.argument("value")

        if not key or not value:
            self.line_error("Both key and value are required for 'set' action")
            self.line("Example: config set providers.github[0].url https://github.com/owner/repo")
            return 1

        try:
            # Parse value based on key
            value = self._parse_value(value)
            
            # Set value
            config = config_manager.load_config()
            config.set(key, value)
            config_manager.save_config(config)
            
            self.info(f"Configuration updated: {key} = {value}")
            return 0
        except ValueError as e:
            self.line_error(f"Invalid value: {str(e)}")
            return 1

    def _validate_config(self, config_manager: ConfigManager) -> int:
        """Validate configuration."""
        config = config_manager.load_config()
        
        try:
            if config_manager.validate_config(config):
                self.info("Configuration is valid")
                return 0
            else:
                self.line_error("Configuration is invalid")
                return 1
        except Exception as e:
            self.line_error(f"Validation error: {str(e)}")
            return 1

    def _get_config_manager(self) -> ConfigManager:
        """Get configuration manager."""
        config_dir = Path.cwd() / ".resource-manager"
        return ConfigManager(config_dir)

    def _print_config(self, config: Config, indent: int = 0):
        """Print configuration in a simple format."""
        for key, value in config.items():
            if isinstance(value, dict):
                self.line(" " * indent + f"{key}:")
                self._print_config(Config(value), indent + 2)
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
                self.line(f"      Timeout: {provider.get('timeout', 10)}s")
        
        # Local providers
        local_providers = config.get_providers("local")
        if local_providers:
            self.line("\n  <info>Local:</info>")
            for i, provider in enumerate(local_providers):
                self.line(f"    [{i}] {provider['name']}:")
                self.line(f"      Path: {provider.get('path', 'N/A')}")
                self.line(f"      Enabled: {provider.get('enabled', True)}")
        
        # Print cache settings
        cache = config.get("cache", {})
        if cache:
            self.line("\n<comment>Cache:</comment>")
            self.line(f"  Enabled: {cache.get('enabled', True)}")
            self.line(f"  TTL: {cache.get('ttl', 3600)}s")
            if "dir" in cache:
                self.line(f"  Directory: {cache['dir']}")

    def _parse_value(self, value: str) -> Any:
        """Parse configuration value."""
        # Try to parse as boolean
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        
        # Try to parse as integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try to parse as float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
