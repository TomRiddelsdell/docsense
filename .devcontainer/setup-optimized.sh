#!/bin/bash
# Optimized setup.sh - Only runtime configuration and user-specific settings
set -e

echo "⚡ Portfolio Platform - Quick Runtime Setup..."
echo "📅 $(date)"

# Verify pre-installed tools (these should already be cached in the image)
echo "✅ Verifying cached installations..."
echo "  • Node.js: $(node --version)"
echo "  • npm: $(npm --version)"
echo "  • Doppler: $(doppler --version 2>/dev/null || echo '❌ needs verification')"
echo "  • Wrangler: $(wrangler --version 2>/dev/null || echo '❌ needs verification')"
echo "  • Neon CLI: $(neonctl --version 2>/dev/null || echo '❌ needs verification')"
echo "  • GitHub CLI: $(gh --version 2>/dev/null | head -n1 || echo '❌ needs verification')"
echo "  • Confluent CLI: $(confluent version 2>/dev/null | head -n1 || echo '❌ needs verification')"

# Runtime git configuration (user-specific, can't be cached)
echo "⚙️ Configuring git for current user..."
if [ -n "$GIT_USER_NAME" ]; then
    git config --global user.name "$GIT_USER_NAME"
    echo "  • Git name configured: $GIT_USER_NAME"
fi

if [ -n "$GIT_USER_EMAIL" ]; then
    git config --global user.email "$GIT_USER_EMAIL"
    echo "  • Git email configured: $GIT_USER_EMAIL"
fi

git config --global init.defaultBranch main
git config --global pull.rebase false
git config --global core.editor "code --wait"

# Runtime Doppler configuration (token-specific, can't be cached)
echo "🔐 Setting up Doppler environment variables..."
if [ -n "$DOPPLER_TOKEN" ]; then
    echo "✅ DOPPLER_TOKEN found, configuring automatic secret injection..."
    
    # Add Doppler environment variable injection to bashrc
    cat >> ~/.bashrc << 'EOF'

# Auto-inject Doppler secrets as environment variables from infrastructure project
if command -v doppler &> /dev/null && [ -n "$DOPPLER_TOKEN" ]; then
    # Only inject if not already done (check for marker)
    if [ -z "$DOPPLER_SECRETS_LOADED" ]; then
        eval "$(doppler run --project tomriddelsdell-infra --config dev --command env 2>/dev/null | grep -E '^(CONFLUENT_CLOUD_|CLOUDFLARE_|NEON_|AWS_|GITHUB_TOKEN)' | sed 's/^/export /')"
        export DOPPLER_SECRETS_LOADED=true
    fi
fi
EOF
    
    echo "✅ Doppler secrets will be auto-injected in new shell sessions"
    
    # Also inject for current session
    if doppler whoami > /dev/null 2>&1; then
        echo "🔄 Injecting secrets for current session..."
        eval "$(doppler run --project tomriddelsdell-infra --config dev --command env 2>/dev/null | grep -E '^(CONFLUENT_CLOUD_|CLOUDFLARE_|NEON_|AWS_|GITHUB_TOKEN)' | sed 's/^/export /')"
        export DOPPLER_SECRETS_LOADED=true
        echo "✅ Secrets injected for current session"
    else
        echo "⚠️  Doppler authentication failed, skipping secret injection"
    fi
else
    echo "⚠️  DOPPLER_TOKEN not found, skipping secret injection"
fi

echo ""
echo "⚡ Quick runtime setup complete! (~5 seconds vs ~2 minutes)"
echo "🚀 All cached tools ready for development"