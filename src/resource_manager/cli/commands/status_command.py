"""Status command implementation."""

from pathlib import Path
from cleo.commands.command import Command
from cleo.helpers import argument, option

from ...core.config import ConfigManager
from ...core.providers import get_provider, get_all_providers


class StatusCommand(Command):
    """Show status of configured providers."""

    name = "status"
    description = "Show status of configured providers"

    arguments = [
        argument(
            "provider_name",
            "Provider name to check status (optional - shows all providers if not specified)",
            optional=True,
        ),
    ]

    options = [
        option(
            "check-connection",
            "c",
            "Test connection to providers",
            flag=True,
        ),
    ]

    def handle(self):
        """Handle the command."""
        try:
            config_manager = self._get_config_manager()
            config = config_manager.load_config()

            if not config:
                self.line_error("No configuration found. Use 'config init' to create configuration.")
                return 1

            provider_name = self.argument("provider_name")

            if provider_name:
                return self._show_provider_status(config, provider_name)
            else:
                return self._show_all_providers_status(config)

        except Exception as e:
            self.line_error(f"Error: {str(e)}")
            return 1

    def _show_provider_status(self, config, provider_name: str) -> int:
        """Show status of a specific provider."""
        provider = self._get_provider(config, provider_name)
        if not provider:
            self.line_error(f"Provider not found: {provider_name}")
            self._show_available_providers(config)
            return 1

        self.line(f"<info>Provider: {provider.name}</info>")
        self._print_provider_details(provider)
        
        return 0

    def _show_all_providers_status(self, config) -> int:
        """Show status of all providers."""
        providers = get_all_providers(config)
        
        if not providers:
            self.line("No providers configured. Use 'config init' to create configuration.")
            return 1

        self.line("<info>Provider Status Overview:</info>\n")

        # Summary table
        enabled_count = sum(1 for p in providers if p.enabled)
        available_count = 0
        
        if self.option("check-connection"):
            self.line("Checking connections...")
            available_count = sum(1 for p in providers if p.enabled and p.is_available())
        
        self.line(f"Total providers: {len(providers)}")
        self.line(f"Enabled providers: {enabled_count}")
        if self.option("check-connection"):
            self.line(f"Available providers: {available_count}\n")
        else:
            self.line("")

        # Provider details
        for provider in providers:
            self.line(f"<comment>▶ {provider.name}</comment>")
            self._print_provider_details(provider, indent=2)
            self.line("")

        return 0

    def _print_provider_details(self, provider, indent: int = 0) -> None:
        """Print detailed information about a provider."""
        prefix = " " * indent
        
        # Basic info
        provider_type = provider.__class__.__name__.replace("Provider", "").lower()
        self.line(f"{prefix}Type: {provider_type}")
        self.line(f"{prefix}Enabled: {'Yes' if provider.enabled else 'No'}")
        
        # Connection status
        if self.option("check-connection") or self.argument("provider_name"):
            try:
                is_available = provider.is_available()
                status_color = "info" if is_available else "error"
                status_text = "Available" if is_available else "Unavailable"
                self.line(f"{prefix}Status: <{status_color}>{status_text}</{status_color}>")
            except Exception as e:
                self.line(f"{prefix}Status: <error>Error - {str(e)}</error>")
        
        # Provider-specific details
        if hasattr(provider, 'url'):  # GitHub provider
            self.line(f"{prefix}URL: {provider.url}")
            if self.option("verbose"):
                self.line(f"{prefix}Owner: {provider.owner}")
                self.line(f"{prefix}Repository: {provider.repo}")
                self.line(f"{prefix}Branch: {provider.branch}")
                self.line(f"{prefix}Resource Directory: {provider.resource_dir}")
                self.line(f"{prefix}Timeout: {provider.timeout}s")
        
        elif hasattr(provider, 'base_path'):  # Local provider
            self.line(f"{prefix}Path: {provider.base_path}")
            if self.option("verbose"):
                path_exists = provider.base_path.exists()
                path_status = "exists" if path_exists else "missing"
                path_color = "info" if path_exists else "error"
                self.line(f"{prefix}Path Status: <{path_color}>{path_status}</{path_color}>")
                
                if path_exists and provider.base_path.is_dir():
                    try:
                        file_count = len(list(provider.base_path.glob("*")))
                        self.line(f"{prefix}Files: {file_count}")
                    except Exception:
                        self.line(f"{prefix}Files: Unable to count")

        # Pattern filters
        if self.option("verbose"):
            if hasattr(provider, '_include_patterns') and provider._include_patterns:
                self.line(f"{prefix}Include Patterns: {', '.join(provider._include_patterns)}")
            if hasattr(provider, '_exclude_patterns') and provider._exclude_patterns:
                self.line(f"{prefix}Exclude Patterns: {', '.join(provider._exclude_patterns)}")

    def _get_provider(self, config, provider_name: str):
        """Get provider instance by name."""
        for provider_type in ["github", "local"]:
            provider = get_provider(config, provider_type, provider_name)
            if provider:
                return provider
        return None

    def _show_available_providers(self, config):
        """Show available provider names."""
        providers = get_all_providers(config)
        if providers:
            self.line("\nAvailable providers:")
            for provider in providers:
                self.line(f"  - {provider.name}")
        else:
            self.line("\nNo providers configured.")

    def _get_config_manager(self) -> ConfigManager:
        """Get configuration manager."""
        config_dir = Path.cwd() / ".resource-manager"
        return ConfigManager(config_dir)