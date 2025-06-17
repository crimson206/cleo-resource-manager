#!/bin/bash

# @description: Create and push git tag
# @arg tag_name: Tag name to create
# @option re-tag,r [flag]: Force re-tag if tag already exists

# USER SETTING
# (추가 설정이 필요하면 여기에)

set -e

echo "=== Git Tagging ==="

# 태그명 확인
if [ -z "$TAG_NAME" ]; then
    echo "Error: Tag name is required"
    echo "Usage: git_tag <tag_name>"
    exit 1
fi

# 현재 브랜치 확인
BRANCH=$(git branch --show-current)
echo "Current branch: $BRANCH"

# 변경사항 확인
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "Warning: You have uncommitted changes"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled"
        exit 0
    fi
fi

# 기존 태그 확인
if git tag -l | grep -q "^$TAG_NAME$"; then
    if [ "$RE_TAG" = "1" ]; then
        echo "Deleting existing tag: $TAG_NAME"
        git tag -d "$TAG_NAME"
        git push origin ":refs/tags/$TAG_NAME" 2>/dev/null || true
    else
        echo "Error: Tag '$TAG_NAME' already exists"
        echo "Use --re-tag to overwrite"
        exit 1
    fi
fi

# 태그 생성
echo "Creating tag: $TAG_NAME"
git tag "$TAG_NAME"

# 푸시
echo "Pushing tag to origin..."
git push origin "$TAG_NAME"

echo "✅ Tag '$TAG_NAME' created and pushed successfully!"
