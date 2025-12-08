#!/bin/bash
# Test script to verify CLI installations work in current environment
set -e

echo "=== Testing CLI installations manually ==="

# Test Wrangler installation
echo "📦 Installing Wrangler..."
npm install -g wrangler@latest
wrangler --version
echo "✅ Wrangler installed successfully"

# Test Neon CLI installation  
echo "📦 Installing Neon CLI..."
npm install -g neonctl@latest
neonctl --version
echo "✅ Neon CLI installed successfully"

echo "=== All CLI tools installed successfully ==="