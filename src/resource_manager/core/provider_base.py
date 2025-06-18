"""Resource provider core functionality."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Protocol, Dict, Any
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern
from .config import Config


class ResourceProvider(Protocol):
    """Resource provider interface for folder download/sync operations."""

    def download_folder(
        self,
        target_dir: str,
        file_pattern: str = "*",
        recursive: bool = True,
        clean: bool = True,
    ) -> List[str]:
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
        self._exclude_patterns = config.get(
            "resources.exclude_patterns", [".git", "__pycache__", "*.pyc"]
        )

    @abstractmethod
    def download_folder(
        self,
        target_dir: str,
        file_pattern: str = "*",
        recursive: bool = True,
        clean: bool = True,
    ) -> List[str]:
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
            include_spec = PathSpec.from_lines(
                GitWildMatchPattern, self._include_patterns
            )
            files = [f for f in files if include_spec.match_file(f)]

        # Then apply exclude patterns
        if self._exclude_patterns:
            exclude_spec = PathSpec.from_lines(
                GitWildMatchPattern, self._exclude_patterns
            )
            files = [f for f in files if not exclude_spec.match_file(f)]

        return files

    def _save_file(self, target_path: Path, content: str) -> bool:
        """Save content to file. Returns True if successful."""
        try:
            # Ensure parent directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content to file
            target_path.write_text(content, encoding="utf-8")
            return True
        except Exception as e:
            print(f"Warning: Failed to save file {target_path}: {e}")
            return False

    def _should_update_file(self, target_path: Path, remote_content: str) -> bool:
        """Check if local file should be updated with remote content."""
        if not target_path.exists():
            return True

        try:
            local_content = target_path.read_text(encoding="utf-8")
            return local_content != remote_content
        except Exception:
            # If we can't read local file, assume we should update
            return True
