#!/bin/bash

# Security validation script for credential leak prevention
# Usage: Run before commits to check for exposed credentials

set -e

echo "🔍 Running security validation checks..."

# Define patterns for various credential types
AWS_KEY_PATTERN="AKIA[0-9A-Z]{16}"
AWS_SECRET_PATTERN="[A-Za-z0-9+/]{40}"
GITHUB_TOKEN_PATTERN="ghp_[a-zA-Z0-9]{36}"
GITHUB_CLASSIC_PATTERN="gh[pousr]_[A-Za-z0-9]{36}"
NEON_API_KEY_PATTERN="napi_[a-zA-Z0-9]+"
CLOUDFLARE_TOKEN_PATTERN="[a-f0-9]{40}"
CONFLUENT_KEY_PATTERN="[A-Z0-9]{16}"
CONFLUENT_SECRET_PATTERN="[A-Za-z0-9+/]{64}"
DOPPLER_TOKEN_PATTERN="dp\.(st|pt)\.[a-zA-Z0-9]+"
GENERIC_KEY_PATTERN="['\"]?[A-Za-z0-9+/]{32,}['\"]?"

# Directories to scan
SCAN_DIRS=(
    "/workspaces/docs"
    "/workspaces/services" 
    "/workspaces/apps"
    "/workspaces/contracts"
    "/workspaces/infra"
)

# Files to always exclude
EXCLUDE_PATTERNS=(
    "*.log"
    "*.tar.gz"
    "*.zip"
    "**/node_modules/**"
    "**/dist/**"
    "**/build/**"
    "**/.git/**"
    "**/doppler.env"
    "**/*.key"
    "**/*.pem"
    "**/.terraform/**"           # Exclude terraform providers and cache
    "**/*.lock.hcl"             # Exclude terraform lock files
    "**/.devcontainer/validate-security.sh"  # Exclude this script itself
)

# Build exclude arguments for grep
EXCLUDE_ARGS=""
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    EXCLUDE_ARGS="$EXCLUDE_ARGS --exclude=$pattern"
done

VIOLATIONS_FOUND=0

# Function to check for pattern in files
check_pattern() {
    local pattern="$1"
    local description="$2"
    local color="$3"
    
    echo -n "  Checking for $description... "
    
    local matches
    matches=$(grep -r $EXCLUDE_ARGS -E "$pattern" "${SCAN_DIRS[@]}" 2>/dev/null | grep -v ".terraform" | grep -v ".lock.hcl" || true)
    
    if [[ -n "$matches" ]]; then
        echo -e "${color}VIOLATIONS FOUND!${NC}"
        echo "$matches"
        echo ""
        ((VIOLATIONS_FOUND++))
        return 1
    else
        echo -e "${GREEN}✓${NC}"
        return 0
    fi
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "🔒 Scanning for credential patterns..."

# Check each credential type
check_pattern "$AWS_KEY_PATTERN" "AWS Access Keys" "$RED"
check_pattern "$GITHUB_TOKEN_PATTERN" "GitHub Personal Access Tokens" "$RED"
check_pattern "$GITHUB_CLASSIC_PATTERN" "GitHub Classic Tokens" "$RED"
check_pattern "$NEON_API_KEY_PATTERN" "Neon API Keys" "$RED"
check_pattern "$DOPPLER_TOKEN_PATTERN" "Doppler Tokens" "$RED"

# Check for common secret environment variable patterns
echo -n "  Checking for exposed environment variables... "
ENV_VIOLATIONS=$(grep -r $EXCLUDE_ARGS -E "(AWS_SECRET_ACCESS_KEY|GITHUB_TOKEN|NEON_API_KEY|CONFLUENT_CLOUD_API_SECRET|CLOUDFLARE_API_KEY|DOPPLER_TOKEN).*=" "${SCAN_DIRS[@]}" 2>/dev/null | grep -v ".terraform" | grep -v ".lock.hcl" | grep -v "export.*\*\*\*" | grep -v "example\|placeholder\|redacted\|\*\*\*\*\|<.*>" || true)

if [[ -n "$ENV_VIOLATIONS" ]]; then
    echo -e "${RED}VIOLATIONS FOUND!${NC}"
    echo "$ENV_VIOLATIONS"
    echo ""
    ((VIOLATIONS_FOUND++))
else
    echo -e "${GREEN}✓${NC}"
fi

# Check for hardcoded credentials in config files
echo -n "  Checking configuration files for hardcoded values... "
CONFIG_VIOLATIONS=$(find "${SCAN_DIRS[@]}" -name "*.json" -o -name "*.yaml" -o -name "*.yml" -o -name "*.toml" -o -name "*.ini" | xargs grep -l -E "(password|secret|key|token).*['\"].*[A-Za-z0-9]{20,}" 2>/dev/null | head -5 || true)

if [[ -n "$CONFIG_VIOLATIONS" ]]; then
    echo -e "${YELLOW}POTENTIAL ISSUES FOUND${NC}"
    echo "Please review these configuration files manually:"
    echo "$CONFIG_VIOLATIONS"
    echo ""
else
    echo -e "${GREEN}✓${NC}"
fi

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ $VIOLATIONS_FOUND -eq 0 ]]; then
    echo -e "${GREEN}✅ No credential violations found!${NC}"
    echo ""
    echo "🛡️  Security validation passed. Safe to commit."
else
    echo -e "${RED}❌ Found $VIOLATIONS_FOUND credential violations!${NC}"
    echo ""
    echo "🚫 DO NOT COMMIT until violations are resolved!"
    echo ""
    echo "🔧 Recommended actions:"
    echo "   • Remove hardcoded credentials from files"
    echo "   • Use Doppler secrets or environment variables"
    echo "   • Add sensitive files to .gitignore"
    echo "   • Replace real values with placeholder examples in docs"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

exit $VIOLATIONS_FOUND