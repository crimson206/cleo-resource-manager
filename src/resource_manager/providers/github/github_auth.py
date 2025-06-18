"""GitHub authentication utilities."""

import os
import subprocess
import re
from typing import Optional

try:
    from dotenv import load_dotenv

    load_dotenv()  # Load .env file if it exists
except ImportError:
    pass  # dotenv not available, skip


def get_github_token() -> Optional[str]:
    """
    Get GitHub token from various sources in order of preference.

    Priority:
    1. Environment variables (GITHUB_TOKEN, GH_TOKEN, etc.)
    2. Git credential helper

    Returns:
        GitHub token if found, None otherwise
    """
    # Try environment variables first
    token = get_token_from_env()
    if token:
        return token

    # Try git credential helper
    token = get_token_from_git_credentials()
    if token:
        return token

    return None


def get_token_from_env() -> Optional[str]:
    """
    Get GitHub token from environment variables.

    Checks the following environment variables in order:
    - GITHUB_TOKEN
    - GH_TOKEN
    - GITHUB_ACCESS_TOKEN
    - GH_ACCESS_TOKEN

    Returns:
        GitHub token if found, None otherwise
    """
    env_vars = ["GITHUB_TOKEN", "GH_TOKEN", "GITHUB_ACCESS_TOKEN", "GH_ACCESS_TOKEN"]

    for env_var in env_vars:
        token = os.getenv(env_var)
        if token and _is_valid_github_token(token):
            return token

    return None


def get_token_from_git_credentials() -> Optional[str]:
    """
    Get GitHub token from git credential helper.

    Uses 'git credential fill' to get credentials for github.com.

    Returns:
        GitHub token if available, None otherwise
    """
    try:
        # Prepare input for git credential fill
        credential_input = "protocol=https\nhost=github.com\n\n"

        # Run git credential fill
        result = subprocess.run(
            ["git", "credential", "fill"],
            input=credential_input,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and result.stdout:
            # Parse the output to extract password (which should be the token)
            for line in result.stdout.split("\n"):
                if line.startswith("password="):
                    token = line.split("=", 1)[1]
                    if _is_valid_github_token(token):
                        return token

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        # git not available or credential helper failed
        pass

    return None


def get_token_from_git_config() -> Optional[str]:
    """
    Get GitHub token from git config.

    Checks git config for github.token or credential.helper settings.

    Returns:
        GitHub token if found, None otherwise
    """
    try:
        # Try to get token from git config
        result = subprocess.run(
            ["git", "config", "--global", "github.token"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0 and result.stdout.strip():
            token = result.stdout.strip()
            if _is_valid_github_token(token):
                return token

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        pass

    return None


def _is_valid_github_token(token: str) -> bool:
    """
    Basic validation for GitHub token format.

    GitHub tokens typically:
    - Are 40+ characters long
    - Start with specific prefixes (ghp_, gho_, ghu_, ghs_, ghr_)
    - Contain only alphanumeric characters and underscores

    Args:
        token: Token to validate

    Returns:
        True if token appears to be a valid GitHub token
    """
    if not token or len(token) < 20:
        return False

    # Check for GitHub token prefixes
    github_prefixes = ["ghp_", "gho_", "ghu_", "ghs_", "ghr_"]

    # New format tokens (start with specific prefixes)
    if any(token.startswith(prefix) for prefix in github_prefixes):
        return len(token) >= 36  # New tokens are typically 36+ chars

    # Classic tokens (40 character hex strings)
    if len(token) == 40 and re.match(r"^[a-f0-9]{40}$", token):
        return True

    # Fine-grained personal access tokens (start with github_pat_)
    if token.startswith("github_pat_"):
        return len(token) >= 50

    # If it's long enough and contains reasonable characters, accept it
    # (to handle future token formats)
    if len(token) >= 20 and re.match(r"^[a-zA-Z0-9_-]+$", token):
        return True

    return False


def validate_token(token: str) -> bool:
    """
    Validate GitHub token by making a test API call.

    Args:
        token: GitHub token to validate

    Returns:
        True if token is valid and has access, False otherwise
    """
    if not token:
        return False

    try:
        import requests

        headers = {"Authorization": f"token {token}"}
        response = requests.get(
            "https://api.github.com/user", headers=headers, timeout=10
        )

        return response.status_code == 200

    except Exception:
        return False


def get_authenticated_user(token: str) -> Optional[dict]:
    """
    Get information about the authenticated user.

    Args:
        token: GitHub token

    Returns:
        User information dict if successful, None otherwise
    """
    if not token:
        return None

    try:
        import requests

        headers = {"Authorization": f"token {token}"}
        response = requests.get(
            "https://api.github.com/user", headers=headers, timeout=10
        )

        if response.status_code == 200:
            return response.json()

    except Exception:
        pass

    return None


def check_token_scopes(token: str) -> list:
    """
    Check what scopes/permissions the token has.

    Args:
        token: GitHub token

    Returns:
        List of scopes if successful, empty list otherwise
    """
    if not token:
        return []

    try:
        import requests

        headers = {"Authorization": f"token {token}"}
        response = requests.get(
            "https://api.github.com/user", headers=headers, timeout=10
        )

        if response.status_code == 200:
            # GitHub returns scopes in the X-OAuth-Scopes header
            scopes_header = response.headers.get("X-OAuth-Scopes", "")
            if scopes_header:
                return [scope.strip() for scope in scopes_header.split(",")]

    except Exception:
        pass

    return []
