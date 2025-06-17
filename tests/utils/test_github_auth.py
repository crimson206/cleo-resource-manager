# tests/utils/test_github_auth.py (새 파일)
import pytest
from unittest.mock import patch, MagicMock
from cleo_resource_manager.utils.github_auth import (
    get_github_token,
    get_token_from_env, 
    get_token_from_git_credentials,
    _is_valid_github_token
)

def test_get_token_from_git_credentials_real():
    """Test getting token from git credentials (real execution)."""
    from cleo_resource_manager.utils.github_auth import get_token_from_git_credentials
    
    token = get_token_from_git_credentials()
    
    if token:
        # 실제 토큰이 있으면 형식만 검증
        assert isinstance(token, str)
        assert len(token) >= 20  # 최소 길이
        # GitHub 토큰 형식 검증
        assert (token.startswith('ghp_') or 
                token.startswith('gho_') or 
                token.startswith('github_pat_') or
                len(token) == 40)  # Classic token
    else:
        # 토큰이 없으면 None 확인
        assert token is None

def test_get_github_token_real():
    """Test main get_github_token function (real execution)."""
    from cleo_resource_manager.utils.github_auth import get_github_token
    
    token = get_github_token()
    
    if token:
        # 토큰이 있으면 유효한 형식인지만 확인
        assert isinstance(token, str)
        assert len(token) >= 20
        # 기본적인 GitHub 토큰 형식
        assert any([
            token.startswith('ghp_'),
            token.startswith('gho_'), 
            token.startswith('github_pat_'),
            len(token) == 40 and token.isalnum()
        ])
    else:
        # 토큰이 없어도 정상 (환경에 따라 다름)
        assert token is None