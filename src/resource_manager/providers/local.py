from pathlib import Path
from typing import List, Dict, Any
import shutil

from resource_manager.core.provider_base import Provider
from resource_manager.core.config import Config


class LocalProvider(Provider):
    """Local filesystem resource provider."""

    def __init__(self, config: Config, provider_config: Dict[str, Any]):
        super().__init__(config, provider_config)
        self.base_path = Path(provider_config["path"])

    def download_folder(
        self,
        target_dir: str,
        file_pattern: str = "*",
        recursive: bool = True,
        clean: bool = True,
    ) -> List[str]:
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
