# GitHub Secrets Setup Guide

Complete guide to managing sensitive credentials securely for the Health Agent project.

## 📋 Table of Contents

- [Overview](#overview)
- [Why Use GitHub Secrets?](#why-use-github-secrets)
- [Setting Up Secrets](#setting-up-secrets)
- [Using Secrets in GitHub Actions](#using-secrets-in-github-actions)
- [Local Development vs Production](#local-development-vs-production)
- [Secret Rotation](#secret-rotation)
- [Security Best Practices](#security-best-practices)

---

## Overview

**GitHub Secrets** are encrypted environment variables stored in your GitHub repository settings. They allow CI/CD workflows (GitHub Actions) to access sensitive credentials without exposing them in code.

**⚠️ Important Distinction:**
- **GitHub Secrets** → Used by GitHub Actions (CI/CD workflows)
- **Local `.env` files** → Used for local development (gitignored)
- **Production `.env.production`** → Used by production deployment (gitignored)

All three serve different purposes and are managed separately.

---

## Why Use GitHub Secrets?

### ✅ Benefits

1. **Never commit secrets to git** - API keys stay out of version control
2. **Encrypted at rest** - GitHub encrypts secrets using [libsodium sealed boxes](https://docs.github.com/en/actions/security-guides/encrypted-secrets#about-encrypted-secrets)
3. **Audit trail** - Track when secrets are added/updated/deleted
4. **Granular access** - Limit secret usage to specific workflows
5. **Environment-specific** - Separate dev/staging/production secrets

### ❌ What NOT to Store in Secrets

- Public information (API endpoints, port numbers)
- Configuration that changes frequently
- Large files or binary data
- Values that need to be shared with frontend (use public env vars instead)

---

## Setting Up Secrets

### Step 1: Navigate to Repository Secrets

1. Go to your GitHub repository: `https://github.com/gpt153/health-agent`
2. Click **Settings** (top menu)
3. In left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret**

### Step 2: Add Required Secrets

Add these secrets one by one:

#### **TELEGRAM_BOT_TOKEN**
- **Value:** Your production Telegram bot token
- **Format:** `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
- **Get from:** [@BotFather](https://t.me/BotFather) on Telegram

#### **OPENAI_API_KEY**
- **Value:** OpenAI API key for GPT-4 Vision
- **Format:** `sk-proj-...` (starts with `sk-proj-` or `sk-`)
- **Get from:** [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

#### **ANTHROPIC_API_KEY**
- **Value:** Anthropic API key for Claude
- **Format:** `sk-ant-api03-...`
- **Get from:** [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)

#### **DATABASE_URL** (Optional - for cloud deployments)
- **Value:** PostgreSQL connection string
- **Format:** `postgresql://user:password@host:5432/dbname`
- **Note:** Only needed if deploying to cloud with managed database

#### **ALLOWED_TELEGRAM_IDS**
- **Value:** Comma-separated user IDs
- **Format:** `7376426503,7538670249,8191393299`
- **Get from:** [@userinfobot](https://t.me/userinfobot)

### Step 3: Verify Secrets

After adding secrets:
1. Click **Actions** tab in repository
2. Trigger a workflow manually (if available)
3. Check workflow logs - secrets will appear as `***`

---

## Using Secrets in GitHub Actions

### Basic Usage

Create or update `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:  # Allow manual trigger

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Build Docker image
        run: docker build -t health-agent .

      - name: Deploy to server
        env:
          # Reference secrets with ${{ secrets.SECRET_NAME }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          ALLOWED_TELEGRAM_IDS: ${{ secrets.ALLOWED_TELEGRAM_IDS }}
        run: |
          # Deploy script can access secrets via environment variables
          echo "Deploying with bot token: ${TELEGRAM_BOT_TOKEN:0:10}***"
          ./deploy.sh
```

### Creating `.env.production` from Secrets

For deployments that need `.env.production` file:

```yaml
- name: Generate .env.production
  run: |
    cat > .env.production << EOF
    TELEGRAM_BOT_TOKEN=${{ secrets.TELEGRAM_BOT_TOKEN }}
    OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }}
    ANTHROPIC_API_KEY=${{ secrets.ANTHROPIC_API_KEY }}
    ALLOWED_TELEGRAM_IDS=${{ secrets.ALLOWED_TELEGRAM_IDS }}
    DATABASE_URL=postgresql://postgres:postgres@postgres:5432/health_agent
    VISION_MODEL=openai:gpt-4o-mini
    AGENT_MODEL=anthropic:claude-sonnet-4-5-20250929
    DATA_PATH=/app/data
    LOG_LEVEL=INFO
    TELEGRAM_TOPIC_FILTER=all
    RUN_MODE=bot
    EOF

- name: Deploy with Docker Compose
  run: docker compose up -d --build
```

### Security in Workflows

**✅ Good practices:**
```yaml
# Secrets are automatically masked in logs
- run: echo "Token: ${{ secrets.TELEGRAM_BOT_TOKEN }}"
# Output: "Token: ***"

# Use secrets only in secure contexts
- name: Deploy
  if: github.ref == 'refs/heads/main'  # Only on main branch
  env:
    API_KEY: ${{ secrets.OPENAI_API_KEY }}
  run: ./deploy.sh
```

**❌ Bad practices:**
```yaml
# DON'T: Write secrets to files that get uploaded as artifacts
- run: echo "${{ secrets.API_KEY }}" > key.txt
- uses: actions/upload-artifact@v4
  with:
    path: key.txt  # ⚠️ Secret now in artifact!

# DON'T: Use secrets in pull requests from forks
on:
  pull_request:  # ⚠️ Secrets not available in fork PRs (by design)
```

---

## Local Development vs Production

### Three-Tier Secret Management

```
┌─────────────────────────────────────────────────┐
│ GitHub Secrets (Encrypted)                      │
│ - Used by: GitHub Actions workflows             │
│ - Access: Repository settings → Secrets         │
│ - Format: Key-value pairs in GitHub UI          │
└─────────────────────────────────────────────────┘
                       ↓ (Referenced in workflows)
┌─────────────────────────────────────────────────┐
│ Production .env.production (Gitignored)         │
│ - Used by: Production Docker containers         │
│ - Access: Server filesystem only                │
│ - Format: Standard .env file                    │
│ - Created by: Deployment script or manually     │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ Local .env (Gitignored)                         │
│ - Used by: Local development                    │
│ - Access: Your machine only                     │
│ - Format: Standard .env file                    │
│ - Created by: Copy from .env.example            │
└─────────────────────────────────────────────────┘
```

### Setup Process

#### For Local Development

1. Copy example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your **development** credentials:
   ```bash
   # Use TEST bot token (not production!)
   TELEGRAM_BOT_TOKEN=8493420276:AAGkP5Jkdz2xnZWO_3xe5LeXAG2wgLSqbKQ

   # Use your own API keys (can be same as production or separate)
   OPENAI_API_KEY=sk-proj-...
   ANTHROPIC_API_KEY=sk-ant-...

   # Only your user ID for testing
   ALLOWED_TELEGRAM_IDS=7376426503
   ```

3. **NEVER commit `.env`** - It's in `.gitignore`

#### For Production Deployment

**Option 1: Manual (One-time setup)**

1. SSH to production server
2. Create `.env.production`:
   ```bash
   cd /path/to/health-agent
   nano .env.production
   ```
3. Paste production credentials
4. Save and exit

**Option 2: Automated (CI/CD)**

Use GitHub Action to generate `.env.production` from secrets (see example above).

#### For GitHub Actions

1. Add secrets to repository settings (see [Setting Up Secrets](#setting-up-secrets))
2. Reference in workflows with `${{ secrets.SECRET_NAME }}`
3. Never hardcode secrets in `.github/workflows/*.yml`

---

## Secret Rotation

### When to Rotate

Rotate secrets immediately if:
- ✅ Secret was accidentally committed to git
- ✅ Secret appeared in logs or public artifacts
- ✅ Team member with access leaves
- ✅ Suspected compromise or unauthorized access

Rotate secrets periodically (recommended every 90 days):
- 🔄 API keys (OpenAI, Anthropic)
- 🔄 Bot tokens (Telegram)
- 🔄 Database passwords

### How to Rotate

#### 1. Telegram Bot Token

1. Message [@BotFather](https://t.me/BotFather)
2. Send `/revoke` and select your bot
3. Copy new token
4. Update in 3 places:
   - GitHub Secrets → `TELEGRAM_BOT_TOKEN`
   - Server `.env.production`
   - Local `.env` (if using same bot)
5. Restart bot: `docker compose restart health-agent-bot`

#### 2. OpenAI API Key

1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Click **Create new secret key**
3. Copy new key
4. Update in:
   - GitHub Secrets → `OPENAI_API_KEY`
   - Server `.env.production`
   - Local `.env`
5. Restart bot to apply new key
6. **Delete old key** from OpenAI dashboard

#### 3. Anthropic API Key

1. Go to [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)
2. Create new key
3. Update in:
   - GitHub Secrets → `ANTHROPIC_API_KEY`
   - Server `.env.production`
   - Local `.env`
4. Restart bot
5. Delete old key from Anthropic console

### Rotation Checklist

```markdown
- [ ] Generate new secret from provider
- [ ] Update GitHub Secrets
- [ ] Update production .env.production
- [ ] Update local .env (if needed)
- [ ] Restart production bot
- [ ] Test bot functionality
- [ ] Delete old secret from provider
- [ ] Document rotation in ops log
```

---

## Security Best Practices

### ✅ DO

1. **Use separate secrets for dev/staging/prod**
   - Development: Test bot token, separate API keys
   - Production: Production bot token, production API keys

2. **Minimize secret scope**
   - Grant least privilege (read-only when possible)
   - Use scoped tokens (e.g., OpenAI project-specific keys)

3. **Monitor secret usage**
   - Review GitHub Actions logs regularly
   - Check API usage dashboards (OpenAI, Anthropic)
   - Set up billing alerts

4. **Document secret owners**
   - Who created each secret?
   - Who has access?
   - When was it last rotated?

5. **Use environment-specific secrets**
   ```yaml
   # Good: Separate secrets per environment
   secrets:
     PROD_API_KEY
     STAGING_API_KEY
     DEV_API_KEY
   ```

### ❌ DON'T

1. **Never commit secrets to git**
   ```bash
   # Bad
   git add .env.production  # ⚠️ Contains secrets!

   # Good
   git add .env.example     # ✅ No secrets, just template
   ```

2. **Never log secrets**
   ```python
   # Bad
   logger.info(f"API Key: {api_key}")  # ⚠️ Exposes secret!

   # Good
   logger.info(f"API Key: {api_key[:8]}***")  # ✅ Masked
   ```

3. **Never share secrets in chat/email**
   - Use password managers (1Password, Bitwarden)
   - Use GitHub Secrets for team sharing
   - Use encrypted channels if absolutely necessary

4. **Never reuse secrets across projects**
   - Each project should have unique credentials
   - Compromising one project shouldn't affect others

5. **Never store secrets in code**
   ```python
   # Bad
   OPENAI_API_KEY = "sk-proj-ABC123..."  # ⚠️ Hardcoded!

   # Good
   OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # ✅ From environment
   ```

---

## Troubleshooting

### "Secret not found" in GitHub Actions

**Problem:** Workflow fails with "secret not found"

**Solution:**
1. Check secret name matches exactly (case-sensitive)
2. Verify secret exists in Settings → Secrets → Actions
3. Ensure you're using `${{ secrets.NAME }}`, not `${{ env.NAME }}`

### "Invalid API Key" in production

**Problem:** Bot starts but API calls fail

**Solution:**
1. Check `.env.production` has correct keys
2. Verify no extra spaces or quotes in values
3. Test keys manually: `curl -H "Authorization: Bearer $OPENAI_API_KEY" ...`
4. Rotate keys if potentially compromised

### Secrets work locally but not in CI

**Problem:** Local development works, GitHub Actions fail

**Solution:**
1. Verify secrets are set in repository settings
2. Check workflow syntax: `${{ secrets.NAME }}`
3. Ensure workflow has permission to access secrets (not a fork PR)

---

## Quick Reference

### Commands

```bash
# View local .env (never commit this!)
cat .env

# Generate .env from template
cp .env.example .env
nano .env

# Check if .env is gitignored
git check-ignore .env
# Should output: .env

# Verify Docker container can access secrets
docker compose exec health-agent-bot env | grep TELEGRAM
```

### File Locations

| File | Purpose | Committed? | Contains Secrets? |
|------|---------|-----------|-------------------|
| `.env.example` | Template | ✅ Yes | ❌ No (placeholders) |
| `.env` | Local dev | ❌ No | ✅ Yes (gitignored) |
| `.env.production` | Production | ❌ No | ✅ Yes (gitignored) |
| `GitHub Secrets` | CI/CD | N/A | ✅ Yes (encrypted) |

### Secret Hierarchy

```
Most Secure → GitHub Secrets (encrypted, access-controlled)
              ↓
Secure       → .env.production (gitignored, server only)
              ↓
Less Secure  → .env (gitignored, local machine)
              ↓
NEVER        → Committed to git ❌
```

---

## Next Steps

After setting up secrets:

1. ✅ Add all required secrets to GitHub repository
2. ✅ Verify `.gitignore` excludes `.env*` files
3. ✅ Update GitHub Actions workflows to use secrets
4. ✅ Test deployment with secrets
5. ✅ Document rotation schedule
6. ✅ Set calendar reminder for 90-day rotation

---

## Resources

- [GitHub Encrypted Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [OpenAI API Keys Best Practices](https://platform.openai.com/docs/guides/production-best-practices)
- [Anthropic Security Best Practices](https://docs.anthropic.com/claude/reference/security)
- [12-Factor App: Config](https://12factor.net/config)

---

**Last Updated:** 2026-01-02
**Author:** Health Agent Team
