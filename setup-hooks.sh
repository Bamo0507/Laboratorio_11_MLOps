#!/bin/bash

# Setup Git Hooks with Husky
# This script installs and configures Husky git hooks for the project

set -e  # Exit on error

echo "🚀 Setting up Git hooks with Husky..."

# Check if we're in a git repository
if [ ! -d ".git" ]; then
  echo "❌ Error: Not a git repository. Please run this script from the project root."
  exit 1
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
  echo "📦 Installing dependencies first..."
  pnpm install
fi

# Configure git to use .husky/ as the hooks directory
echo "⚙️  Configuring Husky..."
pnpm exec husky

# Create/update pre-commit hook
echo "📝 Setting up pre-commit hook..."
cat > .husky/pre-commit << 'EOF'
pnpm run validate
EOF

# Create/update commit-msg hook
echo "📝 Setting up commit-msg hook..."
cat > .husky/commit-msg << 'EOF'
pnpm exec commitlint --edit "$1"
EOF

# Make hooks executable
echo "🔐 Setting execute permissions on hooks..."
chmod +x .husky/pre-commit
chmod +x .husky/commit-msg

# Verify git hooks path is configured
HOOKS_PATH=$(git config core.hooksPath)
echo "✅ Git hooks path configured: $HOOKS_PATH"

# Display hook contents for verification
echo ""
echo "📋 Configured hooks:"
echo ""
echo "=== pre-commit ==="
cat .husky/pre-commit
echo ""
echo "=== commit-msg ==="
cat .husky/commit-msg
echo ""

echo "✅ Husky hooks setup complete!"
echo ""
echo "🎯 Hooks configured:"
echo "  • pre-commit: Runs 'pnpm validate' (lint + typecheck)"
echo "  • commit-msg: Validates conventional commit format"
echo ""
echo "💡 Test with: git commit -m \"test: verify hooks\""
