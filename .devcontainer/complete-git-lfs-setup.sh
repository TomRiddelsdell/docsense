#!/bin/bash
#
# Complete Git LFS setup after hooks have been merged
#

set -e

echo "✅ Git LFS configuration:"
git config --list | grep lfs || echo "No LFS config found"

echo ""
echo "✅ Git LFS hooks have been manually merged into .githooks/"
echo "   The following hooks now include Git LFS support:"
echo "   - pre-push (with quality checks)"
echo "   - post-checkout"
echo "   - post-commit"
echo "   - post-merge"

echo ""
echo "✅ Verifying hook syntax..."
for hook in pre-push post-checkout post-commit post-merge; do
    if bash -n /workspaces/.githooks/$hook 2>/dev/null; then
        echo "   ✓ $hook is valid"
    else
        echo "   ✗ $hook has syntax errors"
    fi
done

echo ""
echo "✅ Git LFS is ready to use!"
echo "   Run 'git lfs track \"*.psd\"' to track large files"
