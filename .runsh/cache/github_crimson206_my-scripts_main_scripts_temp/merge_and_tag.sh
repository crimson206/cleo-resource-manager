#!/bin/bash

# @description: Merge branches and optionally create git tag
# @arg tag_name [optional]: Tag name to create (e.g., v2.0.2)
# @option from: Source branch to merge from
# @option to: Target branch to merge to
# @option force,f [flag]: Force re-tag if tag already exists
# @option dry-run,d [flag]: Preview changes without executing
# @option no-push,n [flag]: Don't push to remote (local only)

# USER SETTING
# Set default values for branch names
FROM=${FROM:-dev}
TO=${TO:-main}

# Function to log messages
log() {
    echo "[$(date '+%H:%M:%S')] $1"
}

# Function to run command or show what would be executed
run_cmd() {
    if [ "$DRY_RUN" = "1" ]; then
        echo "DRY RUN: $1"
    else
        log "Executing: $1"
        eval "$1"
        return $?
    fi
}

# Validate tag name format if provided
if [ -n "$TAG_NAME" ]; then
    if [[ ! "$TAG_NAME" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo "Error: Tag name must follow semantic versioning format (e.g., v2.0.2)"
        exit 1
    fi
    log "Starting merge and tag process for $TAG_NAME"
else
    log "Starting merge process (no tag specified)"
fi

# Check if we're in a git repository
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "Error: Not in a git repository"
    exit 1
fi

# Check if working directory is clean
if ! git diff --quiet; then
    echo "Error: Working directory has uncommitted changes"
    echo "Please commit or stash your changes first"
    echo ""
    echo "Current status:"
    git status --porcelain
    echo ""
    exit 1
fi

# Check if branches exist (only in actual run)
if [ "$DRY_RUN" != "1" ]; then
    if ! git show-ref --verify --quiet refs/heads/$FROM; then
        echo "Error: Source branch '$FROM' does not exist"
        exit 1
    fi
    
    if ! git show-ref --verify --quiet refs/heads/$TO; then
        echo "Error: Target branch '$TO' does not exist"
        exit 1
    fi
fi

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)
log "Current branch: $CURRENT_BRANCH"

# Step 1: Switch to target branch
log "Switching to $TO branch"
run_cmd "git checkout $TO"
if [ $? -ne 0 ] && [ "$DRY_RUN" != "1" ]; then
    echo "Error: Failed to checkout $TO branch"
    exit 1
fi

# Step 2: Pull latest target branch
log "Pulling latest $TO"
run_cmd "git pull origin $TO"
if [ $? -ne 0 ] && [ "$DRY_RUN" != "1" ]; then
    echo "Error: Failed to pull latest $TO"
    exit 1
fi

# Step 3: Merge source branch
log "Merging $FROM into $TO"
run_cmd "git merge $FROM"
if [ $? -ne 0 ] && [ "$DRY_RUN" != "1" ]; then
    echo "Error: Failed to merge $FROM into $TO"
    echo ""
    echo "This is likely due to merge conflicts."
    echo "To resolve:"
    echo "  1. Fix conflicts in the affected files"
    echo "  2. Run: git add <resolved-files>"
    echo "  3. Run: git commit"
    echo "  4. Run: git push origin $TO"
    echo ""
    echo "Or to abort the merge:"
    echo "  git merge --abort"
    echo "  git checkout $CURRENT_BRANCH"
    echo ""
    echo "Current status:"
    git status --porcelain
    exit 1
fi

# Step 4: Create tag using runsh git_tag (if tag name provided)
if [ -n "$TAG_NAME" ]; then
    log "Creating tag $TAG_NAME"
    if [ "$FORCE" = "1" ]; then
        run_cmd "runsh git_tag --re-tag $TAG_NAME"
    else
        run_cmd "runsh git_tag $TAG_NAME"
    fi

    if [ $? -ne 0 ] && [ "$DRY_RUN" != "1" ]; then
        echo "Error: Failed to create tag $TAG_NAME"
        exit 1
    fi
else
    log "Skipping tag creation (no tag name provided)"
fi

# Step 5: Push to remote (unless --no-push is specified)
if [ "$NO_PUSH" != "1" ]; then
    log "Pushing $TO to remote"
    run_cmd "git push origin $TO"
    
    if [ -n "$TAG_NAME" ]; then
        log "Pushing tag $TAG_NAME to remote"
        run_cmd "git push origin $TAG_NAME"
    fi
else
    log "Skipping push to remote (--no-push specified)"
fi

# Step 6: Return to original branch if different
if [ "$CURRENT_BRANCH" != "$TO" ]; then
    log "Returning to original branch: $CURRENT_BRANCH"
    run_cmd "git checkout $CURRENT_BRANCH"
fi

if [ "$DRY_RUN" = "1" ]; then
    echo ""
    echo "DRY RUN COMPLETE - No actual changes were made"
    echo "Run without --dry-run to execute the commands"
else
    echo ""
    if [ -n "$TAG_NAME" ]; then
        log "Successfully merged $FROM to $TO and created tag $TAG_NAME"
        echo "✓ Branch merged: $FROM → $TO"
        echo "✓ Tag created: $TAG_NAME"
    else
        log "Successfully merged $FROM to $TO"
        echo "✓ Branch merged: $FROM → $TO"
    fi
    
    if [ "$NO_PUSH" != "1" ]; then
        echo "✓ Changes pushed to remote"
    fi
fi
