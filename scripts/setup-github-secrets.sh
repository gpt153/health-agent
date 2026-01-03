#!/bin/bash
set -e

# Health Agent - GitHub Secrets Setup Script
# This script helps you securely add all required secrets to your GitHub repository

echo "======================================================"
echo "  Health Agent - GitHub Secrets Setup"
echo "======================================================"
echo ""
echo "This script will help you add the following secrets:"
echo "  1. TELEGRAM_BOT_TOKEN (Production bot token)"
echo "  2. OPENAI_API_KEY (GPT-4 Vision API)"
echo "  3. ANTHROPIC_API_KEY (Claude API)"
echo "  4. ALLOWED_TELEGRAM_IDS (Authorized user IDs)"
echo ""
echo "⚠️  IMPORTANT:"
echo "  - Use PRODUCTION credentials only"
echo "  - Never share these values"
echo "  - Values are encrypted by GitHub"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "======================================================"
echo "Checking GitHub CLI authentication..."
echo "======================================================"

if ! gh auth status &>/dev/null; then
    echo "❌ GitHub CLI not authenticated."
    echo "   Run: gh auth login"
    exit 1
fi

echo "✅ Authenticated as: $(gh api user -q .login)"
echo ""

# Get repository info
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
echo "📦 Repository: $REPO"
echo ""

# Function to set a secret
set_secret() {
    local secret_name=$1
    local description=$2
    local example=$3
    local current_value=""

    echo "──────────────────────────────────────────────────"
    echo "Setting: $secret_name"
    echo "Description: $description"
    if [ -n "$example" ]; then
        echo "Example: $example"
    fi
    echo ""

    # Check if secret already exists
    if gh secret list | grep -q "^$secret_name"; then
        echo "⚠️  Secret already exists!"
        read -p "Update it? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "⏭️  Skipped."
            echo ""
            return
        fi
    fi

    # Prompt for value (hidden input)
    read -s -p "Enter value (input hidden): " secret_value
    echo ""

    if [ -z "$secret_value" ]; then
        echo "⏭️  Empty value - skipped."
        echo ""
        return
    fi

    # Set the secret
    if echo "$secret_value" | gh secret set "$secret_name" --repo "$REPO"; then
        echo "✅ Secret '$secret_name' set successfully!"
    else
        echo "❌ Failed to set secret '$secret_name'"
    fi
    echo ""
}

# Set each secret
echo "======================================================"
echo "  Step 1: Telegram Bot Token"
echo "======================================================"
set_secret \
    "TELEGRAM_BOT_TOKEN" \
    "Production Telegram bot token from @BotFather" \
    "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"

echo "======================================================"
echo "  Step 2: OpenAI API Key"
echo "======================================================"
set_secret \
    "OPENAI_API_KEY" \
    "OpenAI API key for GPT-4 Vision (platform.openai.com)" \
    "sk-proj-..."

echo "======================================================"
echo "  Step 3: Anthropic API Key"
echo "======================================================"
set_secret \
    "ANTHROPIC_API_KEY" \
    "Anthropic API key for Claude (console.anthropic.com)" \
    "sk-ant-api03-..."

echo "======================================================"
echo "  Step 4: Allowed Telegram User IDs"
echo "======================================================"
set_secret \
    "ALLOWED_TELEGRAM_IDS" \
    "Comma-separated list of authorized user IDs (from @userinfobot)" \
    "7376426503,7538670249,8191393299"

echo ""
echo "======================================================"
echo "  ✅ Setup Complete!"
echo "======================================================"
echo ""
echo "Verifying secrets..."
echo ""
gh secret list --repo "$REPO"
echo ""
echo "Next steps:"
echo "  1. Verify all 4 secrets appear above"
echo "  2. Test GitHub Actions workflow (if configured)"
echo "  3. Update production .env.production file"
echo "  4. See docs/GITHUB_SECRETS_SETUP.md for usage guide"
echo ""
echo "To rotate a secret later, run this script again."
echo ""
