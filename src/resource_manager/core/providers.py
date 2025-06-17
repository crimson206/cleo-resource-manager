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
import shutil
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..utils.github_auth import get_github_token, get_token_from_env, get_token_from_git_credentials




class ResourceProvider(Protocol):
    """Resource provider interface for folder download/sync operations."""

    def download_folder(self, target_dir: str, file_pattern: str = "*", recursive: bool = True, clean: bool = True) -> List[str]:
        """
        Download folder contents to local directory.
        
        Args:
            target_dir: Local directory path to download files to
            file_pattern: File pattern to filter downloads (default: "*" for all files)
            recursive: Download recursively (default: True)
            clean: Clean target directory before download (default: True)
        Returns:
            List of downloaded file paths (relative to target_dir)
        """
        ...


    def exists(self, path: str) -> bool:
        """
        Check if resource exists in the provider.
        
        Args:
            path: Resource path to check
            
        Returns:
            True if resource exists, False otherwise
        """
        ...

    def is_available(self) -> bool:
        """
        Check if provider is available and accessible.
        
        Returns:
            True if provider is available, False otherwise
        """
        ...




class Provider(ABC):
    """Base provider class for folder download/sync operations."""

    def __init__(self, config: Config, provider_config: Dict[str, Any]):
        self.config = config
        self.provider_config = provider_config
        self.name = provider_config["name"]
        self.enabled = provider_config.get("enabled", True)
        self._include_patterns = config.get("resources.include_patterns", [])
        self._exclude_patterns = config.get("resources.exclude_patterns", [".git", "__pycache__", "*.pyc"])

    @abstractmethod
    def download_folder(self, target_dir: str, file_pattern: str = "*", recursive: bool = True, clean: bool = True) -> List[str]:
        """Download folder contents to local directory."""
        pass


    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if resource exists."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available."""
        pass

    def _ensure_target_dir(self, target_dir: str) -> Path:
        """Ensure target directory exists and return Path object."""
        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)
        return target_path

    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Check if filename matches pattern."""
        if pattern == "*":
            return True

        import fnmatch
        return fnmatch.fnmatch(filename, pattern)

    def _filter_file_paths(self, file_paths: List[str]) -> List[str]:
        """Filter file paths based on include/exclude patterns."""
        if not file_paths:
            return []

        files = file_paths.copy()
        
        # Apply include patterns first
        if self._include_patterns:
            include_spec = PathSpec.from_lines(GitWildMatchPattern, self._include_patterns)
            files = [f for f in files if include_spec.match_file(f)]
        
        # Then apply exclude patterns
        if self._exclude_patterns:
            exclude_spec = PathSpec.from_lines(GitWildMatchPattern, self._exclude_patterns)
            files = [f for f in files if not exclude_spec.match_file(f)]
        
        return files

    def _save_file(self, target_path: Path, content: str) -> bool:
        """Save content to file. Returns True if successful."""
        try:
            # Ensure parent directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content to file
            target_path.write_text(content, encoding='utf-8')
            return True
        except Exception as e:
            print(f"Warning: Failed to save file {target_path}: {e}")
            return False

    def _should_update_file(self, target_path: Path, remote_content: str) -> bool:
        """Check if local file should be updated with remote content."""
        if not target_path.exists():
            return True
        
        try:
            local_content = target_path.read_text(encoding='utf-8')
            return local_content != remote_content
        except Exception:
            # If we can't read local file, assume we should update
            return True


import shutil
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..utils.github_auth import get_github_token, get_token_from_env, get_token_from_git_credentials


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
        
        # Get GitHub token based on auth configuration
        auth_method = config.get("auth.github.method", "auto")
        
        if auth_method == "default":
            self.token = None  # No authentication
        elif auth_method == "auto":
            self.token = get_github_token()  # Try env → git-credentials
        elif auth_method == "dotenv":
            self.token = get_token_from_env()  # Environment variables only
        elif auth_method == "gitcli":
            self.token = get_token_from_git_credentials()  # Git credentials only
        else:
            self.token = None

    def download_folder(self, target_dir: str, file_pattern: str = "*", recursive: bool = True, clean: bool = True) -> List[str]:
        """Download folder contents from GitHub to local directory (recursive)."""
        if not self.enabled:
            return []

        target_path = self._ensure_target_dir(target_dir)
        downloaded_files = []

        # clean 옵션 처리: 타겟 디렉터리 비우기
        if clean and target_path.exists():
            for item in target_path.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

        try:
            # Use Trees API to get all files recursively in one API call
            api_url = f"https://api.github.com/repos/{self.owner}/{self.repo}/git/trees/{self.branch}"
            params = {'recursive': '1'}  # Get full tree recursively
            
            # Add authentication if token is available
            headers = {}
            if self.token:
                headers['Authorization'] = f'token {self.token}'
            
            response = requests.get(api_url, params=params, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            tree_data = response.json()
            if 'tree' not in tree_data:
                return []

            # Filter files that are in the resource_dir and match pattern
            resource_files = []
            resource_dir_prefix = f"{self.resource_dir}/" if self.resource_dir else ""
            
            for item in tree_data['tree']:
                if item.get('type') == 'blob':  # It's a file
                    file_path = item.get('path', '')
                    
                    # Check if file is in resource directory
                    if not resource_dir_prefix or file_path.startswith(resource_dir_prefix):
                        # Get relative path within resource directory
                        if resource_dir_prefix:
                            relative_path = file_path[len(resource_dir_prefix):]
                        else:
                            relative_path = file_path
                        
                        # Skip if relative_path is empty (shouldn't happen)
                        if not relative_path:
                            continue
                        
                        # recursive 옵션 처리: recursive=False면 하위 폴더 파일 제외
                        if not recursive and '/' in relative_path:
                            continue
                        # Check if filename matches pattern
                        filename = relative_path.split('/')[-1]  # Get just the filename for pattern matching
                        if self._matches_pattern(filename, file_pattern):
                            resource_files.append(relative_path)

            # Apply include/exclude pattern filtering
            filtered_files = self._filter_file_paths(resource_files)

            # Download each filtered file using Raw URL (no additional API calls)
            for relative_path in filtered_files:
                content = self._download_file_content_raw(relative_path)
                if content is not None:
                    # Preserve directory structure in target
                    file_path = target_path / relative_path
                    if self._save_file(file_path, content):
                        downloaded_files.append(relative_path)

            return downloaded_files

        except Exception as e:
            print(f"Warning: Failed to download folder from GitHub: {e}")
            return []

    def exists(self, path: str = None) -> bool:
        """Check if resource exists in GitHub"""
        if not self.enabled:
            return False

        try:
            # resource_dir을 고려하여 경로 설정
            full_path = f"{self.resource_dir}/{path}" if self.resource_dir else path
            api_url = f"https://api.github.com/repos/{self.owner}/{self.repo}/contents/{full_path}"
            
            # 브랜치 지정
            params = {}
            if self.branch:
                params['ref'] = self.branch
            
            # Add authentication if token is available
            headers = {}
            if self.token:
                headers['Authorization'] = f'token {self.token}'
                
            response = requests.get(api_url, params=params, headers=headers, timeout=self.timeout)
            return response.status_code == 200
        except:
            return False

    def is_available(self) -> bool:
        """Check if GitHub API is available."""
        if not self.enabled:
            return False

        try:
            # Add authentication if token is available
            headers = {}
            if self.token:
                headers['Authorization'] = f'token {self.token}'
                
            response = requests.head(self.url, headers=headers, timeout=5)
            return response.status_code == 200
        except:
            return False

    def _download_file_content_raw(self, relative_path: str) -> Optional[str]:
        """Download file content using Raw URL (no API rate limit)."""
        if not relative_path:
            return None

        try:
            # Construct Raw URL with full relative path
            if self.resource_dir:
                full_path = f"{self.resource_dir}/{relative_path}"
            else:
                full_path = relative_path
                
            raw_url = f"https://raw.githubusercontent.com/{self.owner}/{self.repo}/{self.branch}/{full_path}"
            
            # Add authentication if token is available
            headers = {}
            if self.token:
                headers['Authorization'] = f'token {self.token}'
            
            response = requests.get(raw_url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            return response.text
            
        except Exception as e:
            print(f"Failed to download file content for {relative_path}: {e}")
            return None

    def _download_file_content(self, download_url: str) -> Optional[str]:
        """Download file content from GitHub (legacy method - still used by exists())."""
        if not download_url:
            return None

        try:
            # Add authentication if token is available
            headers = {}
            if self.token:
                headers['Authorization'] = f'token {self.token}'
                
            response = requests.get(download_url, headers=headers, timeout=self.timeout)
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

    def download_folder(self, target_dir: str, file_pattern: str = "*", recursive: bool = True, clean: bool = True) -> List[str]:
        """Copy folder contents from source to target directory (recursive)."""
        if not self.enabled or not self.base_path.exists():
            return []

        target_path = self._ensure_target_dir(target_dir)
        copied_files = []

        # clean 옵션 처리: 타겟 디렉터리 비우기
        if clean and target_path.exists():
            for item in target_path.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

        try:
            # recursive 옵션 처리
            if recursive:
                if file_pattern == "*":
                    glob_pattern = "**/*"  # All files recursively
                else:
                    glob_pattern = f"**/{file_pattern}"  # Pattern in any subdirectory
            else:
                if file_pattern == "*":
                    glob_pattern = "*"  # Only top-level files
                else:
                    glob_pattern = file_pattern  # Only top-level matching files
            
            matching_files = []
            for file_path in self.base_path.glob(glob_pattern):
                if file_path.is_file():
                    rel_path = str(file_path.relative_to(self.base_path))
                    matching_files.append(rel_path)

            # Filter files based on include/exclude patterns
            filtered_files = self._filter_file_paths(matching_files)

            # Copy each filtered file
            for rel_path in filtered_files:
                source_file = self.base_path / rel_path
                target_file = target_path / rel_path
                
                try:
                    # Ensure target directory exists
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    # Copy file
                    shutil.copy2(source_file, target_file)
                    copied_files.append(rel_path)
                except Exception as e:
                    print(f"Warning: Failed to copy file {rel_path}: {e}")

            return copied_files

        except Exception as e:
            print(f"Warning: Failed to copy folder: {e}")
            return []

    def exists(self, path: str) -> bool:
        """Check if resource exists in local filesystem"""
        if not self.enabled:
            return False

        file_path = self.base_path / path
        return file_path.exists()

    def is_available(self) -> bool:
        """Check if local path is available."""
        return self.enabled and self.base_path.exists()


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
