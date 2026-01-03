# GitHub Secrets Reference

Quick reference for all required GitHub secrets in the health-agent project.

## 📋 Required Secrets

### 1. TELEGRAM_BOT_TOKEN

**Description:** Production Telegram bot token for the health agent
**Format:** `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
**Length:** ~46 characters
**Get from:** [@BotFather](https://t.me/BotFather) on Telegram

**How to get:**
1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/mybots`
3. Select your health agent bot
4. Click "API Token"
5. Copy the token (format: `NNNNNNNNNN:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`)

**⚠️ Important:**
- Use PRODUCTION bot token (not dev/test)
- Never commit this to git
- Rotate if compromised

---

### 2. OPENAI_API_KEY

**Description:** OpenAI API key for GPT-4 Vision (food photo analysis)
**Format:** `sk-proj-...` or `sk-...`
**Length:** ~164 characters (project keys) or ~51 characters (legacy)
**Get from:** [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

**How to get:**
1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Click **"Create new secret key"**
3. Name it: "health-agent-production"
4. (Optional) Restrict to specific project
5. Copy the key immediately (shown only once!)

**⚠️ Important:**
- Project keys (sk-proj-) are recommended for better security
- Never share or commit to git
- Set usage limits in OpenAI dashboard to prevent unexpected bills
- Rotate every 90 days

**Usage in project:**
- Food photo analysis (GPT-4 Vision)
- Multi-agent food validation
- Vision model: `openai:gpt-4o-mini`

---

### 3. ANTHROPIC_API_KEY

**Description:** Anthropic API key for Claude (multi-agent consensus)
**Format:** `sk-ant-api03-...`
**Length:** ~108 characters
**Get from:** [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)

**How to get:**
1. Go to [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)
2. Click **"Create Key"**
3. Name it: "health-agent-production"
4. Copy the key immediately (shown only once!)

**⚠️ Important:**
- Keys start with `sk-ant-api03-`
- Never share or commit to git
- Monitor usage in Anthropic console
- Rotate every 90 days

**Usage in project:**
- Multi-agent food debate (Optimist, Pessimist, Realist)
- Conversation handling
- Agent model: `anthropic:claude-sonnet-4-5-20250929`

---

### 4. ALLOWED_TELEGRAM_IDS

**Description:** Comma-separated list of authorized Telegram user IDs
**Format:** `7376426503,7538670249,8191393299,8288122596,8352041023`
**Get from:** [@userinfobot](https://t.me/userinfobot) on Telegram

**How to get user IDs:**
1. Each user opens Telegram
2. Message [@userinfobot](https://t.me/userinfobot)
3. Bot replies with user info including ID (a number like `7376426503`)
4. Collect all user IDs
5. Join with commas (no spaces)

**⚠️ Important:**
- No spaces between IDs
- Only numeric IDs (not usernames)
- Anyone not on this list cannot use the bot
- Update this list when adding/removing users

**Current authorized users:**
- `7376426503` - Primary admin
- `7538670249` - User 2
- `8191393299` - User 3
- `8288122596` - User 4
- `8352041023` - User 5

---

## 🔧 Optional Secrets

These are optional but recommended for production deployments:

### DATABASE_URL

**Description:** PostgreSQL connection string (for cloud deployments)
**Format:** `postgresql://user:password@host:5432/dbname`
**Get from:** Your database provider (Supabase, Neon, AWS RDS, etc.)

**Example:**
```
postgresql://postgres:Secr3tP@ssw0rd@db.example.com:5432/health_agent
```

**⚠️ When needed:**
- Only if deploying to cloud (not local Docker)
- For managed database services
- For CI/CD deployments

**⚠️ When NOT needed:**
- Local development (use .env)
- Docker Compose deployments (DATABASE_URL in compose file)

---

## 📝 Setup Methods

### Method 1: Interactive Script (Recommended)

Run the setup script that walks you through each secret:

```bash
cd /home/samuel/.archon/workspaces/health-agent
./scripts/setup-github-secrets.sh
```

**Pros:**
- ✅ Interactive prompts for each secret
- ✅ Hidden input (values not visible)
- ✅ Validates authentication
- ✅ Shows current status
- ✅ Can update existing secrets

---

### Method 2: GitHub CLI (Manual)

Set secrets one by one using GitHub CLI:

```bash
# Format: echo "SECRET_VALUE" | gh secret set SECRET_NAME

# 1. Telegram Bot Token
echo "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz" | \
  gh secret set TELEGRAM_BOT_TOKEN --repo gpt153/health-agent

# 2. OpenAI API Key
echo "sk-proj-..." | \
  gh secret set OPENAI_API_KEY --repo gpt153/health-agent

# 3. Anthropic API Key
echo "sk-ant-api03-..." | \
  gh secret set ANTHROPIC_API_KEY --repo gpt153/health-agent

# 4. Allowed User IDs
echo "7376426503,7538670249,8191393299" | \
  gh secret set ALLOWED_TELEGRAM_IDS --repo gpt153/health-agent

# Verify
gh secret list --repo gpt153/health-agent
```

**Pros:**
- ✅ Fast for bulk updates
- ✅ Scriptable
- ✅ Can be automated

**Cons:**
- ⚠️ Values visible in shell history
- ⚠️ No validation

---

### Method 3: GitHub Web UI (Manual)

Set secrets through the GitHub website:

**Steps:**
1. Go to [github.com/gpt153/health-agent](https://github.com/gpt153/health-agent)
2. Click **Settings** (top menu)
3. Click **Secrets and variables** → **Actions** (left sidebar)
4. Click **New repository secret**
5. Fill in:
   - **Name:** `TELEGRAM_BOT_TOKEN`
   - **Secret:** `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
6. Click **Add secret**
7. Repeat for each secret

**Pros:**
- ✅ Visual interface
- ✅ No CLI tools needed
- ✅ Easy to verify

**Cons:**
- ⚠️ Manual and time-consuming
- ⚠️ Need to copy-paste each value

---

## ✅ Verification Checklist

After setting secrets, verify everything is correct:

### Check via GitHub CLI

```bash
gh secret list --repo gpt153/health-agent
```

**Expected output:**
```
ALLOWED_TELEGRAM_IDS    Updated YYYY-MM-DD
ANTHROPIC_API_KEY       Updated YYYY-MM-DD
OPENAI_API_KEY          Updated YYYY-MM-DD
TELEGRAM_BOT_TOKEN      Updated YYYY-MM-DD
```

### Check via GitHub UI

1. Go to Settings → Secrets and variables → Actions
2. You should see 4 secrets listed
3. Click "Update" on any secret to verify (don't save changes)

### Test in GitHub Actions

If you have workflows configured:

1. Go to **Actions** tab
2. Trigger a workflow manually (if available)
3. Check logs - secrets should appear as `***`
4. Verify workflow can access secrets

---

## 🔄 Rotation Schedule

Set reminders to rotate secrets regularly:

| Secret | Frequency | Next Rotation |
|--------|-----------|---------------|
| TELEGRAM_BOT_TOKEN | 90 days | [Add date] |
| OPENAI_API_KEY | 90 days | [Add date] |
| ANTHROPIC_API_KEY | 90 days | [Add date] |
| ALLOWED_TELEGRAM_IDS | As needed | N/A |

**How to rotate:**
1. Generate new secret from provider
2. Run `./scripts/setup-github-secrets.sh` again
3. Update production `.env.production`
4. Restart production bot
5. Delete old secret from provider

---

## 🆘 Troubleshooting

### "gh: command not found"

Install GitHub CLI:
```bash
# Ubuntu/Debian
sudo apt install gh

# macOS
brew install gh

# Then authenticate
gh auth login
```

### "Authentication required"

Authenticate GitHub CLI:
```bash
gh auth login
# Follow prompts to authenticate with GitHub
```

### "Secret not found" in workflows

1. Check secret name matches exactly (case-sensitive)
2. Verify secret exists: `gh secret list`
3. Ensure workflow uses `${{ secrets.NAME }}`
4. Check workflow has permission to access secrets

### Values appear in logs

**This is normal!** GitHub automatically masks secret values in logs:
- Input: `My token is sk-proj-ABC123...`
- Output: `My token is ***`

If you see actual values, you're likely viewing them locally, not in GitHub Actions.

---

## 📚 Additional Resources

- [Complete Setup Guide](GITHUB_SECRETS_SETUP.md) - Detailed guide with security practices
- [GitHub Encrypted Secrets Docs](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- Setup Script: `scripts/setup-github-secrets.sh`

---

**Last Updated:** 2026-01-02
