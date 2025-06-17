"""Resource manager CLI application."""

from cleo.application import Application

from .commands.cache_command import CacheCommand
from .commands.config_command import ConfigCommand
from .commands.get_command import GetCommand


class ResourceManagerApplication(Application):
    """Resource Manager CLI application."""

    def __init__(self):
        super().__init__("Resource Manager", "0.1.0")

        self.add(CacheCommand())
        self.add(ConfigCommand())
        self.add(GetCommand())


def main():
    """Main entry point."""
    app = ResourceManagerApplication()
    app.run() 