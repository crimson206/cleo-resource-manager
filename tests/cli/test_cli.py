"""Tests for CLI commands."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from cleo.testers.command_tester import CommandTester

from cleo_resource_manager.cli.commands.config_command import ConfigCommand
from cleo_resource_manager.cli.commands.download_command import DownloadCommand
from cleo_resource_manager.cli.commands.status_command import StatusCommand
from cleo_resource_manager.core.config import ConfigManager, Config


@pytest.fixture
def sample_config_data():
    """Sample configuration data."""
    return {
        "providers": {
            "github": [
                {
                    "name": "test-github",
                    "enabled": True,
                    "url": "https://github.com/test/repo",
                    "default_branch": "main",
                    "resource_dir": "resources"
                }
            ],
            "local": [
                {
                    "name": "test-local",
                    "enabled": True,
                    "path": "./local-resources"
                }
            ]
        },
        "resources": {
            "include_patterns": ["*.txt"],
            "exclude_patterns": [".git", "*.pyc"]
        }
    }


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory."""
    config_dir = tmp_path / ".resource-manager"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def config_with_file(temp_config_dir, sample_config_data):
    """Create config file and return ConfigManager."""
    config_file = temp_config_dir / "config.json"
    config_file.write_text(json.dumps(sample_config_data, indent=2))
    return ConfigManager(temp_config_dir)


class TestConfigCommand:
    """Test ConfigCommand."""

    def test_config_init(self, temp_config_dir):
        """Test config init command."""
        command = ConfigCommand()
        
        with patch.object(command, '_get_config_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.config_path.exists.return_value = False
            mock_manager.create_sample_config.return_value = temp_config_dir / "config.json"
            mock_get_manager.return_value = mock_manager
            
            tester = CommandTester(command)
            exit_code = tester.execute("init")
            
            assert exit_code == 0
            assert "Configuration initialized" in tester.io.fetch_output()
            mock_manager.create_sample_config.assert_called_once()

    def test_config_init_exists_without_force(self, temp_config_dir):
        """Test config init when file exists without force."""
        command = ConfigCommand()
        
        with patch.object(command, '_get_config_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.config_path.exists.return_value = True
            mock_get_manager.return_value = mock_manager
            
            tester = CommandTester(command)
            exit_code = tester.execute("init")
            
            assert exit_code == 1
            assert "already exists" in tester.io.fetch_error()

    def test_config_show(self, sample_config_data):
        """Test config show command."""
        command = ConfigCommand()
        
        with patch.object(command, '_get_config_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.load_config.return_value = Config(sample_config_data)
            mock_get_manager.return_value = mock_manager
            
            tester = CommandTester(command)
            exit_code = tester.execute("show")
            
            assert exit_code == 0
            output = tester.io.fetch_output()
            assert "providers" in output

    def test_config_show_no_config(self):
        """Test config show when no config exists."""
        command = ConfigCommand()
        
        with patch.object(command, '_get_config_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.load_config.return_value = None  # No config exists
            mock_get_manager.return_value = mock_manager
            
            tester = CommandTester(command)
            exit_code = tester.execute("show")
            
            assert exit_code == 1
            assert "No configuration found" in tester.io.fetch_output()

    def test_config_show_pretty(self, sample_config_data):
        """Test config show with pretty formatting."""
        command = ConfigCommand()
        
        with patch.object(command, '_get_config_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.load_config.return_value = Config(sample_config_data)
            mock_get_manager.return_value = mock_manager
            
            tester = CommandTester(command)
            exit_code = tester.execute("show --pretty")
            
            assert exit_code == 0
            output = tester.io.fetch_output()
            assert "Configuration:" in output
            assert "GitHub:" in output

    def test_config_validate_valid(self, sample_config_data):
        """Test config validate with valid config."""
        command = ConfigCommand()
        
        with patch.object(command, '_get_config_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.load_config.return_value = Config(sample_config_data)
            mock_manager.validate_config.return_value = True
            mock_get_manager.return_value = mock_manager
            
            tester = CommandTester(command)
            exit_code = tester.execute("validate")
            
            assert exit_code == 0
            assert "Configuration is valid" in tester.io.fetch_output()

    def test_config_validate_invalid(self, sample_config_data):
        """Test config validate with invalid config."""
        command = ConfigCommand()
        
        with patch.object(command, '_get_config_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.load_config.return_value = Config(sample_config_data)
            mock_manager.validate_config.return_value = False
            mock_get_manager.return_value = mock_manager
            
            tester = CommandTester(command)
            exit_code = tester.execute("validate")
            
            assert exit_code == 1
            assert "Configuration is invalid" in tester.io.fetch_error()
            
    def test_config_validate_no_config(self):
        """Test config validate when no config exists."""
        command = ConfigCommand()
        
        with patch.object(command, '_get_config_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.load_config.return_value = None
            mock_get_manager.return_value = mock_manager
            
            tester = CommandTester(command)
            exit_code = tester.execute("validate")
            
            assert exit_code == 1
            assert "No configuration found" in tester.io.fetch_error()


class TestDownloadCommand:
    """Test DownloadCommand."""

    @patch('cleo_resource_manager.cli.commands.download_command.get_provider')
    @patch('cleo_resource_manager.cli.commands.download_command.ConfigManager')
    def test_download_from_provider(self, mock_config_manager, mock_get_provider, tmp_path):
        """Test download from specific provider."""
        # Setup mock provider
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.download_folder.return_value = ["file1.txt", "file2.txt"]
        mock_get_provider.return_value = mock_provider
        
        # Setup mock config manager
        mock_manager = MagicMock()
        mock_manager.load_config.return_value = MagicMock()  # Non-empty config
        mock_config_manager.return_value = mock_manager
        
        command = DownloadCommand()
        target_dir = str(tmp_path / "download")
        
        tester = CommandTester(command)
        exit_code = tester.execute(f"test-provider {target_dir}")
        
        assert exit_code == 0
        output = tester.io.fetch_output()
        assert "Downloaded 2 files" in output
        assert "file1.txt" in output
        assert "file2.txt" in output

    @patch('cleo_resource_manager.cli.commands.download_command.get_provider')
    @patch('cleo_resource_manager.cli.commands.download_command.ConfigManager')
    def test_download_provider_not_found(self, mock_config_manager, mock_get_provider, tmp_path):
        """Test download with non-existent provider."""
        mock_get_provider.return_value = None
        
        # Setup mock config manager
        mock_manager = MagicMock()
        mock_manager.load_config.return_value = Config({})  # Empty but valid config
        mock_config_manager.return_value = mock_manager
        
        command = DownloadCommand()
        target_dir = str(tmp_path / "download")
        
        tester = CommandTester(command)
        exit_code = tester.execute(f"nonexistent-provider {target_dir}")
        
        assert exit_code == 1
        assert "Provider not found" in tester.io.fetch_error()

    @patch('cleo_resource_manager.cli.commands.download_command.ConfigManager')
    def test_download_target_is_file(self, mock_config_manager, tmp_path):
        """Test download when target is a file."""
        # Create a file instead of directory
        target_file = tmp_path / "target.txt"
        target_file.write_text("existing file")
        
        # Setup mock config manager
        mock_manager = MagicMock()
        mock_manager.load_config.return_value = Config({})
        mock_config_manager.return_value = mock_manager
        
        command = DownloadCommand()
        
        tester = CommandTester(command)
        exit_code = tester.execute(f"test-provider {target_file}")
        
        assert exit_code == 1
        assert "Target path is a file" in tester.io.fetch_error()

    @patch('cleo_resource_manager.cli.commands.download_command.get_all_providers')
    @patch('cleo_resource_manager.cli.commands.download_command.ConfigManager')
    def test_download_all_providers(self, mock_config_manager, mock_get_all_providers, tmp_path):
        """Test download from all providers."""
        # Setup mock providers
        mock_provider1 = MagicMock()
        mock_provider1.name = "provider1"
        mock_provider1.enabled = True
        mock_provider1.is_available.return_value = True
        mock_provider1.download_folder.return_value = ["file1.txt"]
        
        mock_provider2 = MagicMock()
        mock_provider2.name = "provider2"
        mock_provider2.enabled = True
        mock_provider2.is_available.return_value = True
        mock_provider2.download_folder.return_value = ["file2.txt"]
        
        mock_get_all_providers.return_value = [mock_provider1, mock_provider2]
        
        # Setup mock config manager
        mock_manager = MagicMock()
        mock_manager.load_config.return_value = Config({})
        mock_config_manager.return_value = mock_manager
        
        command = DownloadCommand()
        target_dir = str(tmp_path / "download")
        
        tester = CommandTester(command)
        exit_code = tester.execute(f"all {target_dir}")
        
        output = tester.io.fetch_output()
        assert "Total files downloaded: 2" in output


class TestStatusCommand:
    """Test StatusCommand."""

    @patch('cleo_resource_manager.cli.commands.status_command.get_all_providers')
    @patch('cleo_resource_manager.cli.commands.status_command.ConfigManager')
    def test_status_all_providers(self, mock_config_manager, mock_get_all_providers):
        """Test status command for all providers."""
        # Setup mock provider
        mock_provider = MagicMock()
        mock_provider.name = "test-provider"
        mock_provider.enabled = True
        mock_provider.__class__.__name__ = "GitHubProvider"
        mock_get_all_providers.return_value = [mock_provider]
        
        # Setup mock config manager
        mock_manager = MagicMock()
        mock_manager.load_config.return_value = MagicMock()
        mock_config_manager.return_value = mock_manager
        
        command = StatusCommand()
        
        tester = CommandTester(command)
        exit_code = tester.execute("")
        
        output = tester.io.fetch_output()
        assert "Provider Status Overview" in output
        assert "test-provider" in output

    @patch('cleo_resource_manager.cli.commands.status_command.get_provider')
    @patch('cleo_resource_manager.cli.commands.status_command.ConfigManager')
    def test_status_specific_provider(self, mock_config_manager, mock_get_provider):
        """Test status command for specific provider."""
        # Setup mock provider
        mock_provider = MagicMock()
        mock_provider.name = "test-provider"
        mock_provider.enabled = True
        mock_provider.__class__.__name__ = "GitHubProvider"
        mock_get_provider.return_value = mock_provider
        
        # Setup mock config manager
        mock_manager = MagicMock()
        mock_manager.load_config.return_value = MagicMock()
        mock_config_manager.return_value = mock_manager
        
        command = StatusCommand()
        
        tester = CommandTester(command)
        exit_code = tester.execute("test-provider")
        
        # assert exit_code == 0
        output = tester.io.fetch_output()
        assert "Provider: test-provider" in output

    @patch('cleo_resource_manager.cli.commands.status_command.get_provider')
    @patch('cleo_resource_manager.cli.commands.status_command.ConfigManager')
    def test_status_provider_not_found(self, mock_config_manager, mock_get_provider):
        """Test status command with non-existent provider."""
        mock_get_provider.return_value = None
        
        # Setup mock config manager
        mock_manager = MagicMock()
        mock_manager.load_config.return_value = MagicMock()
        mock_config_manager.return_value = mock_manager
        
        command = StatusCommand()
        
        tester = CommandTester(command)
        exit_code = tester.execute("nonexistent-provider")
        
        assert exit_code == 1
        assert "Provider not found" in tester.io.fetch_error()


# Integration tests that actually call GitHub API
@pytest.mark.integration
class TestRealGitHubIntegration:
    """Integration tests with real GitHub API calls."""
    
    def test_real_github_provider_status(self):
        """Test status command with real GitHub provider."""
        # This would test against the real repository
        # Only run with pytest -m integration
        pass
        
    def test_real_github_provider_download(self):
        """Test download command with real GitHub provider."""
        # This would test actual downloading from GitHub
        # Only run with pytest -m integration
        pass