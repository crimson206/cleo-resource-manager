#!/bin/bash

# @description: Publish Python package to PyPI
# @option test,t [flag]: Upload to TestPyPI instead of PyPI
# @option skip-build,s [flag]: Skip building, use existing dist files

# USER SETTING
# (추가 설정이 필요하면 여기에)

set -e

echo "=== PyPI Publishing ==="

# 빌드
if [ "$SKIP_BUILD" != "1" ]; then
    echo "Building package..."
    rm -rf build/ dist/ *.egg-info/
    python -m build
    echo "✓ Build completed"
else
    echo "Using existing dist files"
fi

# 검증
echo "Validating package..."
twine check dist/*
echo "✓ Package validation passed"

# 업로드 대상 선택
if [ "$TEST" = "1" ]; then
    REPO_ARG="--repository testpypi"
    echo "Target: TestPyPI"
else
    REPO_ARG=""
    echo "Target: PyPI (production)"
fi

# 파일 목록 표시
echo
echo "Files to upload:"
ls -la dist/

# 확인
echo
read -p "Continue with upload? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 0
fi

# PyPI 토큰 입력 받기
echo
if [ -z "$TWINE_PASSWORD" ]; then
    echo "Enter your PyPI API token:"
    read -s TWINE_PASSWORD
    export TWINE_PASSWORD
fi

export TWINE_USERNAME=__token__

# 업로드
echo
echo "Uploading..."
twine upload $REPO_ARG dist/*

echo "✅ Published successfully!"