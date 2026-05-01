#!/bin/sh
# Pattern Mirror — install git hooks
# Run once after cloning: sh scripts/install-hooks.sh

cp scripts/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
echo "✅ Git hooks installed."
