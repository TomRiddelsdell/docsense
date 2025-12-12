#!/bin/bash
# Setup script to add missing secrets to Doppler

echo "🔧 Setting up Doppler secrets for docsense project"
echo ""

# Check if doppler is configured
if ! doppler secrets > /dev/null 2>&1; then
    echo "❌ Doppler is not configured. Please run: doppler setup --project docsense --config dev"
    exit 1
fi

echo "📝 Adding missing secrets to Doppler..."
echo ""

# Add DATABASE_URL
echo "Setting DATABASE_URL..."
doppler secrets set DATABASE_URL="postgresql://docsense:docsense_local_dev@localhost:5432/docsense" --silent

# Check for AI API keys
echo ""
echo "⚠️  AI Provider API Keys:"
echo ""
echo "The following secrets need to be set if you want to use multiple AI providers:"
echo ""
echo "For Google Gemini:"
echo "  doppler secrets set AI_INTEGRATIONS_GEMINI_API_KEY=<your-key>"
echo "  doppler secrets set AI_INTEGRATIONS_GEMINI_BASE_URL=<base-url> (optional)"
echo ""
echo "For OpenAI:"
echo "  doppler secrets set AI_INTEGRATIONS_OPENAI_API_KEY=<your-key>"
echo "  doppler secrets set AI_INTEGRATIONS_OPENAI_BASE_URL=<base-url> (optional)"
echo ""
echo "✅ Core secrets configured!"
echo ""
echo "Current Doppler secrets:"
doppler secrets

echo ""
echo "🚀 You can now start the application with: ./run.sh"
