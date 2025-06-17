#!/bin/bash

# @description: Check files that will be included in Python package publish
# @arg project_path [optional] [default=.]: Project directory path
# @option verbose [flag]: Show detailed build output and file info
# @option build-only,b [flag]: Only build package, don't check contents

# USER SETTING
# (이 스크립트에서 사용할 추가 설정이 있으면 여기에)

cd "$PROJECT_PATH"

[ "$VERBOSE" = "1" ] && echo "Working in: $(pwd)"

# 기존 빌드 파일 정리
rm -rf build/ dist/ *.egg-info/

# 패키지 빌드
if [ "$VERBOSE" = "1" ]; then
    echo "Building package..."
    python -m build --sdist
else
    echo "Building package..."
    python -m build --sdist > /dev/null 2>&1
fi

if [ "$BUILD_ONLY" = "1" ]; then
    echo "Build completed. Files in dist/:"
    ls -la dist/
    exit 0
fi

# 내용 확인
echo
echo "Files to be published:"
tar -tzf dist/*.tar.gz | sort

if [ "$VERBOSE" = "1" ]; then
    echo
    echo "File count: $(tar -tzf dist/*.tar.gz | wc -l)"
    echo "Package size: $(du -h dist/*.tar.gz | cut -f1)"
fi