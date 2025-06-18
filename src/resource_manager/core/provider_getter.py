"""Resource provider core functionality."""


from typing import List, Optional
from .config import Config
from resource_manager.providers.github.core import GitHubProvider
from resource_manager.providers.local import LocalProvider
from resource_manager.core.provider_base import Provider


def get_provider(
    config: Config, provider_type: str, provider_name: str
) -> Optional[Provider]:
    """Get provider instance by type and name."""
    providers = config.get_providers(provider_type)

    for provider_config in providers:
        if provider_config.get("name") == provider_name:
            if provider_type == "github":
                return GitHubProvider(config, provider_config)
            elif provider_type == "local":
                return LocalProvider(config, provider_config)

    return None


def get_all_providers(config: Config) -> List[Provider]:
    """Get all enabled providers."""
    providers = []

    # Get GitHub providers
    for provider_config in config.get_enabled_providers("github"):
        providers.append(GitHubProvider(config, provider_config))

    # Get local providers
    for provider_config in config.get_enabled_providers("local"):
        providers.append(LocalProvider(config, provider_config))

    return providers
