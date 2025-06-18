import shutil
import requests
from typing import List, Dict, Any, Optional

from resource_manager.providers.github.github_auth import (
    get_github_token,
    get_token_from_env,
    get_token_from_git_credentials,
)
from resource_manager.core.provider_base import Provider
from resource_manager.core.config import Config

class GitHubProvider(Provider):
    """GitHub repository resource provider."""

    def __init__(self, config: Config, provider_config: Dict[str, Any]):
        super().__init__(config, provider_config)
        self.url = provider_config["url"]

        # Extract owner and repo from URL
        # Expected format: https://github.com/owner/repo
        parts = self.url.rstrip("/").split("/")
        if len(parts) < 5 or parts[2] != "github.com":
            raise ValueError(
                "Invalid GitHub URL format. Expected: https://github.com/owner/repo"
            )

        self.owner = parts[3]
        self.repo = parts[4]
        self.branch = provider_config.get("default_branch", "main")
        self.timeout = provider_config.get("timeout", 10)
        self.resource_dir = provider_config.get("resource_dir", "resources")
        self.target_dir = provider_config.get("target_dir")  # Get target_dir from config

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

    def download_folder(
        self,
        target_dir: str,
        file_pattern: str = "*",
        recursive: bool = True,
        clean: bool = True,
    ) -> List[str]:
        """Download folder contents from GitHub to local directory (recursive)."""
        if not self.enabled:
            return []

        # Use config's target_dir if not provided in command
        if not target_dir and self.target_dir:
            target_dir = self.target_dir

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
            params = {"recursive": "1"}  # Get full tree recursively

            # Add authentication if token is available
            headers = {}
            if self.token:
                headers["Authorization"] = f"token {self.token}"

            response = requests.get(
                api_url, params=params, headers=headers, timeout=self.timeout
            )
            response.raise_for_status()

            tree_data = response.json()
            if "tree" not in tree_data:
                return []

            # Filter files that are in the resource_dir and match pattern
            resource_files = []
            resource_dir_prefix = f"{self.resource_dir}/" if self.resource_dir else ""

            for item in tree_data["tree"]:
                if item.get("type") == "blob":  # It's a file
                    file_path = item.get("path", "")

                    # Check if file is in resource directory
                    if not resource_dir_prefix or file_path.startswith(
                        resource_dir_prefix
                    ):
                        # Get relative path within resource directory
                        if resource_dir_prefix:
                            relative_path = file_path[len(resource_dir_prefix) :]
                        else:
                            relative_path = file_path

                        # Skip if relative_path is empty (shouldn't happen)
                        if not relative_path:
                            continue

                        # recursive 옵션 처리: recursive=False면 하위 폴더 파일 제외
                        if not recursive and "/" in relative_path:
                            continue
                        # Check if filename matches pattern
                        filename = relative_path.split("/")[
                            -1
                        ]  # Get just the filename for pattern matching
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
                params["ref"] = self.branch

            # Add authentication if token is available
            headers = {}
            if self.token:
                headers["Authorization"] = f"token {self.token}"

            response = requests.get(
                api_url, params=params, headers=headers, timeout=self.timeout
            )
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
                headers["Authorization"] = f"token {self.token}"

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
                headers["Authorization"] = f"token {self.token}"

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
                headers["Authorization"] = f"token {self.token}"

            response = requests.get(download_url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Failed to download file content: {e}")
            return None
