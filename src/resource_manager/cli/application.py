"""Resource manager CLI application."""

from cleo.application import Application

from .commands.config_command import ConfigCommand
from .commands.download_command import DownloadCommand
from .commands.status_command import StatusCommand


class ResourceManagerApplication(Application):
    """Resource Manager CLI application."""

    def __init__(self):
        super().__init__("Resource Manager", "0.1.0")

        self.add(ConfigCommand())
        self.add(DownloadCommand())
        self.add(StatusCommand())


def main():
    """Main entry point."""
    app = ResourceManagerApplication()
    app.run() 