# Resource Manager

A powerful Python CLI tool for managing and downloading resources from various providers including GitHub repositories and local filesystems.

## Features

- **Multiple Provider Support**: Download resources from GitHub repositories and local directories
- **Flexible Authentication**: Support for multiple GitHub authentication methods (environment variables, git credentials, etc.)
- **Pattern Matching**: Filter downloads using file patterns and include/exclude rules
- **Recursive Downloads**: Support for recursive directory downloads with configurable depth
- **Configuration Management**: JSON-based configuration with validation
- **Status Monitoring**: Check provider availability and connection status

## Installation

### Requirements

- Python 3.10 or higher
- Git (for GitHub authentication via git credentials)

### Install from source

```bash
git clone https://github.com/crimson206/resource-manager
cd resource-manager
pip install -e .
```

## Quick Start

1. **Initialize configuration**:
```bash
resource-manager config init
```

2. **Configure providers** by editing `.resource-manager/config.json`:
```json
{
  "auth": {
    "github": {
      "method": "auto"
    }
  },
  "providers": {
    "github": [
      {
        "name": "my-repo",
        "enabled": true,
        "url": "https://github.com/owner/repo",
        "default_branch": "main",
        "resource_dir": "resources",
        "timeout": 10
      }
    ],
    "local": [
      {
        "name": "local-resources",
        "enabled": true,
        "path": "./local-resources"
      }
    ]
  },
  "resources": {
    "include_patterns": ["*.txt", "*.md"],
    "exclude_patterns": [".git", "__pycache__", "*.pyc"]
  }
}
```

3. **Download resources**:
```bash
resource-manager download my-repo ./downloaded-resources
```

## Usage

### Configuration Commands

#### Initialize configuration
```bash
resource-manager config init [--force]
```

#### Show current configuration
```bash
resource-manager config show [--pretty]
```

#### Validate configuration
```bash
resource-manager config validate
```

### Download Commands

#### Download from specific provider
```bash
resource-manager download <provider_name> <target_dir> [options]
```

#### Download from all providers
```bash
resource-manager download all <target_dir> [options]
```

**Options:**
- `--pattern, -p`: File pattern to match (e.g., `*.txt`)
- `--force, -f`: Force download even if target directory exists and is not empty
- `--no-recursive`: Do not download recursively (only top-level files)
- `--no-clean`: Do not clean target directory before download

**Examples:**
```bash
# Download all files from a specific provider
resource-manager download my-repo ./resources

# Download only markdown files
resource-manager download my-repo ./docs --pattern "*.md"

# Download from all providers
resource-manager download all ./all-resources

# Download without cleaning target directory
resource-manager download my-repo ./resources --no-clean
```

### Status Commands

#### Check all providers
```bash
resource-manager status [--check-connection]
```

#### Check specific provider
```bash
resource-manager status <provider_name> [--check-connection]
```

## Configuration

### Provider Types

#### GitHub Provider
```json
{
  "name": "provider-name",
  "enabled": true,
  "url": "https://github.com/owner/repo",
  "default_branch": "main",
  "resource_dir": "resources",
  "timeout": 10
}
```

**Fields:**
- `name`: Unique provider name
- `enabled`: Whether the provider is active
- `url`: GitHub repository URL
- `default_branch`: Branch to download from (default: "main")
- `resource_dir`: Subdirectory within the repo to download from
- `timeout`: Request timeout in seconds

#### Local Provider
```json
{
  "name": "provider-name",
  "enabled": true,
  "path": "./local-resources"
}
```

**Fields:**
- `name`: Unique provider name
- `enabled`: Whether the provider is active
- `path`: Local directory path

### Authentication

#### GitHub Authentication Methods

The tool supports multiple authentication methods for GitHub:

1. **Auto** (default): Tries environment variables first, then git credentials
2. **Environment variables only**: Uses `GITHUB_TOKEN`, `GH_TOKEN`, etc.
3. **Git credentials only**: Uses git credential helper
4. **No authentication**: Public repositories only

Set authentication method in config:
```json
{
  "auth": {
    "github": {
      "method": "auto"  // "auto", "dotenv", "gitcli", "default"
    }
  }
}
```

#### Environment Variables

Set any of these environment variables:
- `GITHUB_TOKEN`
- `GH_TOKEN`
- `GITHUB_ACCESS_TOKEN`
- `GH_ACCESS_TOKEN`

### Resource Filtering

Configure global include/exclude patterns:
```json
{
  "resources": {
    "include_patterns": ["*.txt", "*.md", "*.json"],
    "exclude_patterns": [".git", "__pycache__", "*.pyc", "node_modules"]
  }
}
```

Patterns support:
- Wildcards (`*`, `?`)
- Directory patterns (`dir/`, `**/pattern`)
- Gitignore-style patterns

## Examples

### Basic GitHub Repository Download
```bash
# Initialize config
resource-manager config init

# Edit config to add GitHub provider
# Download resources
resource-manager download my-github-repo ./downloaded
```

### Multiple Providers with Filtering
```bash
# Download only Python files from all providers
resource-manager download all ./python-files --pattern "*.py"

# Check provider status
resource-manager status --check-connection
```

### Local Development Workflow
```bash
# Add local development resources
# Configure local provider in config.json
resource-manager download local-dev ./current-resources --no-clean
```

## Error Handling

The tool provides detailed error messages and suggestions:

- **Configuration errors**: Validation with specific error messages
- **Network errors**: Timeout and connection handling for GitHub
- **Authentication errors**: Clear messages about token issues
- **File system errors**: Permission and path validation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license information here]

## Author

**Sisung Kim** - sisung.kim1@gmail.com

## Changelog

### 1.0.0
- Initial release
- GitHub and local provider support
- CLI interface with config, download, and status commands
- Multiple authentication methods
- Pattern-based filtering
- Recursive downloads