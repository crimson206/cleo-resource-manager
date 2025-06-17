"""Resource manager library application."""

from cleo.application import Application

from .cli.commands.cache_command import CacheCommand
from .cli.commands.config_command import ConfigCommand


class ResourceManagerApplication:
    """Resource manager library application for integrating with other CLIs."""

    @staticmethod
    def add_commands(application: Application) -> None:
        """Add resource manager commands to an application."""
        application.add(CacheCommand())
        application.add(ConfigCommand()) 