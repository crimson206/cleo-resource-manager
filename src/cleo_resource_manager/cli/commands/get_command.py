"""Get command implementation."""

import os
from pathlib import Path
from typing import Optional, Tuple
from cleo.commands.command import Command
from cleo.helpers import option, argument

from ...core.config import ConfigManager
from ...core.providers import get_provider, get_all_providers
from ...core.cache import CacheManager


class GetCommand(Command):
    """Get resource from configured providers."""

    name = "get"
    description = "Get resource from configured providers"

    arguments = [
        argument(
            "resource_path",
            "Resource path to get (e.g. github:path/to/file.txt)",
            optional=True,
        )
    ]

    options = [
        option(
            "list",
            "l",
            "List available resources",
            flag=True,
        ),
        option(
            "output",
            "o",
            "Output file path",
            flag=False,
            value_required=True,
        ),
        option(
            "no-cache",
            "C",
            "Disable cache for this request",
            flag=True,
        ),
        option(
            "pattern",
            "p",
            "File pattern to match (e.g. *.txt)",
            flag=False,
            value_required=True,
        ),
    ]

    def handle(self):
        """Handle the command."""
        config_manager = ConfigManager()
        config = config_manager.load_config()

        # If no resource path provided, show available providers
        if not self.argument("resource_path"):
            self._show_providers(config)
            return 0

        # Parse resource path
        resource_path = self.argument("resource_path")
        provider_name, path = self._parse_resource_path(resource_path)

        # Get provider
        provider = self._get_provider(config, provider_name)
        if not provider:
            self.line_error(f"Provider not found: {provider_name}")
            return 1

        try:
            # Get resource content
            content = self._get_resource_content(provider, path)
            if not content:
                self.line_error("No content found")
                return 1

            # Output content
            output_path = self.option("output")
            if output_path:
                self._output_content(content, output_path)
            else:
                self.line(content)

            return 0
        except FileNotFoundError as e:
            self.line_error(str(e))
            return 1
        except Exception as e:
            self.line_error(f"Error getting resource: {e}")
            return 1

    def _parse_resource_path(self, resource_path: str) -> Tuple[str, str]:
        """Parse resource path into provider and path."""
        if ":" in resource_path:
            provider_name, path = resource_path.split(":", 1)
        else:
            provider_name = resource_path
            path = ""

        return provider_name, path

    def _get_provider(self, config, provider_name: str):
        """Get provider instance."""
        for provider_type in ["github", "local"]:
            provider = get_provider(config, provider_type, provider_name)
            if provider:
                return provider
        return None

    def _get_resource_content(self, provider, path: str) -> Optional[str]:
        """Get resource content with caching."""
        # Check if cache is enabled
        if not self.option("no-cache"):
            cache_manager = self._get_cache_manager()
            cache_path = cache_manager.get_cache_path(provider.url)

            # Try to get from cache first
            if cache_manager.is_cache_valid(cache_path):
                resources = cache_manager.load_from_cache(cache_path)
                for cached_path, content in resources:
                    if cached_path == path:
                        return content

        # Get from provider
        content = provider.get_resource(path)

        # Cache the result if caching is enabled
        if not self.option("no-cache"):
            cache_manager = self._get_cache_manager()
            cache_path = cache_manager.get_cache_path(provider.url)
            cache_manager.save_to_cache(
                cache_path,
                [(path, content)],
                {
                    "provider_type": provider.__class__.__name__,
                    "url": provider.url,
                }
            )

        return content

    def _show_providers(self, config):
        """Show available providers."""
        providers = get_all_providers(config)
        if not providers:
            self.line("No providers configured. Use 'config init' to create configuration.")
            return

        self.line("Available providers:")
        for provider in providers:
            status = "enabled" if provider.enabled else "disabled"
            self.line(f"- {provider.name} ({provider.__class__.__name__}) [{status}]")

    def _output_content(self, content: str, output_path: str):
        """Output content to file or stdout."""
        if output_path == "-":
            self.line(content)
            return

        # Create directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # Write content to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

    def _get_cache_manager(self) -> CacheManager:
        """Get cache manager instance."""
        cache_dir = Path.cwd() / ".resource-manager" / "cache"
        return CacheManager(cache_dir) 