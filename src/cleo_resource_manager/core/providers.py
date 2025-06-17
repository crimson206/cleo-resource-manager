"""Resource provider core functionality."""

import re
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Protocol, Tuple, Dict, Any
import requests
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern
from .config import Config


class ResourceProvider(Protocol):
    """Resource provider interface."""

    def get_resources(self, file_pattern: str = "*") -> List[Tuple[str, str]]:
        """
        Get resources from the provider.
        Returns: [(resource_path, resource_content), ...]
        """
        ...

    def is_available(self) -> bool:
        """Check if provider is available."""
        ...

    def get_resource(self, path: str) -> str:
        """Get resource content from the provider"""
        ...

    def exists(self, path: str) -> bool:
        """Check if resource exists"""
        ...


class Provider(ABC):
    """Base provider class."""

    def __init__(self, config: Config, provider_config: Dict[str, Any]):
        self.config = config
        self.provider_config = provider_config
        self.name = provider_config["name"]
        self.enabled = provider_config.get("enabled", True)
        self._include_patterns = config.get("resources.include_patterns", [])
        self._exclude_patterns = config.get("resources.exclude_patterns", [".git", "__pycache__", "*.pyc"])

    @abstractmethod
    def get_resource(self, path: str) -> str:
        """Get resource content from the provider"""
        pass

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if resource exists"""
        pass

    def _filter_resources(self, resources: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """Filter resources based on include/exclude patterns."""
        if not resources:
            return []

        # Convert to relative paths
        files = [path for path, _ in resources]
        
        # Apply include patterns first
        if self._include_patterns:
            include_spec = PathSpec.from_lines(GitWildMatchPattern, self._include_patterns)
            files = [f for f in files if include_spec.match_file(f)]
        
        # Then apply exclude patterns
        if self._exclude_patterns:
            exclude_spec = PathSpec.from_lines(GitWildMatchPattern, self._exclude_patterns)
            files = [f for f in files if not exclude_spec.match_file(f)]
        
        # Return filtered resources
        return [(path, content) for path, content in resources if path in files]

    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Check if filename matches pattern."""
        if pattern == "*":
            return True

        import fnmatch
        return fnmatch.fnmatch(filename, pattern)

    def _format_resource_list(self, resources: List[Tuple[str, str]]) -> str:
        """Format resource list for display."""
        if not resources:
            return "No resources found."
        
        return "\n".join(f"- {path}" for path, _ in sorted(resources))


class GitHubProvider(Provider):
    """GitHub repository resource provider."""

    def __init__(self, config: Config, provider_config: Dict[str, Any]):
        super().__init__(config, provider_config)
        self.url = provider_config["url"]
        
        # Extract owner and repo from URL
        # Expected format: https://github.com/owner/repo
        parts = self.url.rstrip('/').split('/')
        if len(parts) < 5 or parts[2] != 'github.com':
            raise ValueError("Invalid GitHub URL format. Expected: https://github.com/owner/repo")
        
        self.owner = parts[3]
        self.repo = parts[4]
        self.branch = provider_config.get("default_branch", "main")
        self.timeout = provider_config.get("timeout", 10)
        self.resource_dir = provider_config.get("resource_dir", "resources")

    def get_resources(self, file_pattern: str = "*") -> List[Tuple[str, str]]:
        """Get resources from GitHub repository."""
        if not self.enabled:
            return []

        try:
            # Get contents of resource directory
            api_url = f"https://api.github.com/repos/{self.owner}/{self.repo}/contents/{self.resource_dir}"
            response = requests.get(api_url, timeout=self.timeout)
            response.raise_for_status()
            
            files = response.json()
            if not isinstance(files, list):
                return []

            resources = []
            for file_info in files:
                if file_info.get("type") == "file":
                    name = file_info.get("name", "")
                    if self._matches_pattern(name, file_pattern):
                        content = self._download_file_content(
                            file_info.get("download_url")
                        )
                        if content:
                            # Store with relative path
                            rel_path = os.path.join(self.resource_dir, name)
                            resources.append((rel_path, content))

            return self._filter_resources(resources)
        except Exception as e:
            print(f"Warning: Failed to fetch resources from GitHub: {e}")
            return []

    def is_available(self) -> bool:
        """Check if GitHub API is available."""
        if not self.enabled:
            return False

        try:
            response = requests.head(self.url, timeout=5)
            return response.status_code == 200
        except:
            return False

    def get_resource(self, path: str) -> str:
        """Get resource content from GitHub"""
        if not self.enabled:
            raise RuntimeError(f"Provider {self.name} is disabled")

        # If path is empty or just the provider name, list all resources
        if not path or path == self.name:
            resources = self.get_resources()
            if not resources:
                raise FileNotFoundError("No resources found in the repository")
            
            return self._format_resource_list(resources)

        # Otherwise, get specific resource
        if not self.exists(path):
            raise FileNotFoundError(f"Resource not found: {path}")

        api_url = f"https://raw.githubusercontent.com/{self.owner}/{self.repo}/{self.branch}/{path}"
        response = requests.get(api_url, timeout=self.timeout)
        response.raise_for_status()
        return response.text

    def exists(self, path: str) -> bool:
        """Check if resource exists in GitHub"""
        if not self.enabled:
            return False

        try:
            api_url = f"https://api.github.com/repos/{self.owner}/{self.repo}/contents/{path}"
            response = requests.get(api_url, timeout=self.timeout)
            return response.status_code == 200
        except:
            return False

    def _download_file_content(self, download_url: str) -> Optional[str]:
        """Download file content from GitHub."""
        if not download_url:
            return None

        try:
            response = requests.get(download_url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Failed to download file content: {e}")
            return None


class LocalProvider(Provider):
    """Local filesystem resource provider."""

    def __init__(self, config: Config, provider_config: Dict[str, Any]):
        super().__init__(config, provider_config)
        self.base_path = Path(provider_config["path"])

    def get_resources(self, file_pattern: str = "*") -> List[Tuple[str, str]]:
        """Get resources from local filesystem."""
        if not self.enabled or not self.base_path.exists():
            return []

        resources = []
        for file_path in self.base_path.glob(file_pattern):
            if file_path.is_file():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    # Store with relative path
                    rel_path = str(file_path.relative_to(self.base_path))
                    resources.append((rel_path, content))
                except Exception as e:
                    print(f"Warning: Failed to read file {file_path}: {e}")

        return self._filter_resources(resources)

    def is_available(self) -> bool:
        """Check if local path is available."""
        return self.enabled and self.base_path.exists()

    def get_resource(self, path: str) -> str:
        """Get resource content from local filesystem"""
        if not self.enabled:
            raise RuntimeError(f"Provider {self.name} is disabled")

        # If path is empty or just the provider name, list all resources
        if not path or path == self.name:
            resources = self.get_resources()
            if not resources:
                raise FileNotFoundError("No resources found in the local directory")
            
            return self._format_resource_list(resources)

        # Otherwise, get specific resource
        if not self.exists(path):
            raise FileNotFoundError(f"Resource not found: {path}")
        
        file_path = self.base_path / path
        return file_path.read_text()

    def exists(self, path: str) -> bool:
        """Check if resource exists in local filesystem"""
        if not self.enabled:
            return False

        file_path = self.base_path / path
        return file_path.exists()


def get_provider(config: Config, provider_type: str, provider_name: str) -> Optional[Provider]:
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
