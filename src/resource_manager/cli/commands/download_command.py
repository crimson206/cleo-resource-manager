"""Download command implementation."""

import os
from pathlib import Path
from cleo.commands.command import Command
from cleo.helpers import argument, option

from resource_manager.core.config import ConfigManager
from resource_manager.core.provider_getter import get_provider, get_all_providers


class DownloadCommand(Command):
    """Download resources from configured providers."""

    name = "download"
    description = "Download resources from configured providers"

    arguments = [
        argument(
            "provider_name",
            "Provider name to download from (or 'all' for all providers)",
            optional=False,
        ),
        argument(
            "target_dir",
            "Target directory to download resources to",
            optional=False,
        ),
    ]

    options = [
        option(
            "pattern",
            "p",
            "File pattern to match (e.g. *.txt)",
            flag=False,
            value_required=True,
        ),
        option(
            "force",
            "f",
            "Force download even if target directory exists and not empty",
            flag=True,
        ),
        option(
            "no-recursive",
            None,
            "Do not download recursively (only top-level files)",
            flag=True,
        ),
        option(
            "no-clean",
            None,
            "Do not clean target directory before download",
            flag=True,
        ),
    ]

    def handle(self):
        """Handle the command."""
        try:
            config_manager = self._get_config_manager()
            config = config_manager.load_config()

            if not config:
                self.line_error(
                    "No configuration found. Use 'config init' to create configuration."
                )
                return 1

            provider_name = self.argument("provider_name")
            target_dir = self.argument("target_dir")
            pattern = self.option("pattern") or "*"

            # Validate target directory
            if not self._validate_target_dir(target_dir):
                return 1

            if provider_name.lower() == "all":
                return self._download_from_all_providers(config, target_dir, pattern)
            else:
                return self._download_from_provider(
                    config, provider_name, target_dir, pattern
                )

        except Exception as e:
            self.line_error(f"Error: {str(e)}")
            return 1

    def _download_from_provider(
        self, config, provider_name: str, target_dir: str, pattern: str
    ) -> int:
        """Download from a specific provider."""
        provider = self._get_provider(config, provider_name)
        if not provider:
            self.line_error(f"Provider not found: {provider_name}")
            self._show_available_providers(config)
            return 1

        if not provider.is_available():
            self.line_error(f"Provider '{provider_name}' is not available")
            return 1

        # 옵션 처리
        recursive = not self.option("no-recursive")
        clean = not self.option("no-clean")

        try:
            if not self.option("quiet"):
                self.info(f"Downloading from '{provider_name}' to '{target_dir}'...")
                if pattern != "*":
                    self.line(f"Pattern: {pattern}")
                self.line(f"Recursive: {recursive}, Clean: {clean}")

            downloaded_files = provider.download_folder(
                target_dir, pattern, recursive=recursive, clean=clean
            )

            if downloaded_files:
                if not self.option("quiet"):
                    self.info(f"Downloaded {len(downloaded_files)} files:")
                    for file_path in sorted(downloaded_files):
                        self.line(f"  - {file_path}")
                return 0
            else:
                self.line(
                    "No files downloaded (no matching files found or all files filtered out)"
                )
                return 0

        except Exception as e:
            self.line_error(f"Failed to download from '{provider_name}': {str(e)}")
            return 1

    def _download_from_all_providers(
        self, config, target_dir: str, pattern: str
    ) -> int:
        """Download from all enabled providers."""
        providers = get_all_providers(config)

        if not providers:
            self.line_error("No providers configured")
            return 1

        enabled_providers = [p for p in providers if p.enabled and p.is_available()]
        if not enabled_providers:
            self.line_error("No enabled and available providers found")
            return 1

        # 옵션 처리
        recursive = not self.option("no-recursive")
        clean = not self.option("no-clean")

        if not self.option("quiet"):
            self.info(
                f"Downloading from {len(enabled_providers)} providers to '{target_dir}'..."
            )
            if pattern != "*":
                self.line(f"Pattern: {pattern}")
            self.line(f"Recursive: {recursive}, Clean: {clean}")

        total_downloaded = 0
        failed_providers = []

        for provider in enabled_providers:
            try:
                if not self.option("quiet"):
                    self.line(f"\n<comment>Provider: {provider.name}</comment>")

                downloaded_files = provider.download_folder(
                    target_dir, pattern, recursive=recursive, clean=clean
                )

                if downloaded_files:
                    total_downloaded += len(downloaded_files)
                    if not self.option("quiet"):
                        self.info(f"Downloaded {len(downloaded_files)} files:")
                        for file_path in sorted(downloaded_files):
                            self.line(f"  - {file_path}")
                else:
                    if not self.option("quiet"):
                        self.line("No files downloaded")

            except Exception as e:
                failed_providers.append((provider.name, str(e)))
                self.line_error(f"Failed to download from '{provider.name}': {str(e)}")

        # Summary
        if not self.option("quiet"):
            self.line(f"\n<info>Summary:</info>")
            self.line(f"Total files downloaded: {total_downloaded}")
            if failed_providers:
                self.line(f"Failed providers: {len(failed_providers)}")
                for name, error in failed_providers:
                    self.line(f"  - {name}: {error}")

        return 0 if not failed_providers else 1

    def _get_provider(self, config, provider_name: str):
        """Get provider instance by name."""
        for provider_type in ["github", "local"]:
            provider = get_provider(config, provider_type, provider_name)
            if provider:
                return provider
        return None

    def _show_available_providers(self, config):
        """Show available providers."""
        providers = get_all_providers(config)
        if providers:
            self.line("\nAvailable providers:")
            for provider in providers:
                status = "enabled" if provider.enabled else "disabled"
                available = "available" if provider.is_available() else "unavailable"
                self.line(f"  - {provider.name} ({status}, {available})")

    def _validate_target_dir(self, target_dir: str) -> bool:
        """Validate target directory."""
        target_path = Path(target_dir)

        # Check if target exists and is not empty
        if target_path.exists():
            if target_path.is_file():
                self.line_error(f"Target path is a file, not a directory: {target_dir}")
                return False

            if any(target_path.iterdir()) and not self.option("force"):
                self.line_error(f"Target directory is not empty: {target_dir}")
                self.line("Use --force to download anyway")
                return False

        return True

    def _get_config_manager(self) -> ConfigManager:
        """Get configuration manager."""
        config_dir = Path.cwd() / ".resource-manager"
        return ConfigManager(config_dir)
