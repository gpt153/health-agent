# GitHub Secrets Setup Checklist

Quick checklist for setting up GitHub secrets for health-agent.

## 🎯 Quick Start

**Easiest method:**
```bash
cd /home/samuel/.archon/workspaces/health-agent
./scripts/setup-github-secrets.sh
```

The script will walk you through each secret interactively.

---

## ✅ Pre-Setup Checklist

- [ ] GitHub CLI installed (`gh --version`)
- [ ] GitHub CLI authenticated (`gh auth status`)
- [ ] You have access to gpt153/health-agent repository
- [ ] You have the following credentials ready:
  - [ ] Production Telegram bot token (from @BotFather)
  - [ ] OpenAI API key (from platform.openai.com)
  - [ ] Anthropic API key (from console.anthropic.com)
  - [ ] List of authorized Telegram user IDs (from @userinfobot)

---

## 📝 Secrets to Set

### 1. TELEGRAM_BOT_TOKEN
- [ ] Get token from [@BotFather](https://t.me/BotFather)
- [ ] Format: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
- [ ] Set in GitHub secrets
- [ ] Verify it's the PRODUCTION token (not dev/test)

### 2. OPENAI_API_KEY
- [ ] Create key at [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- [ ] Format: `sk-proj-...` (project key) or `sk-...` (legacy)
- [ ] Set in GitHub secrets
- [ ] Set usage limits in OpenAI dashboard (recommended)

### 3. ANTHROPIC_API_KEY
- [ ] Create key at [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)
- [ ] Format: `sk-ant-api03-...`
- [ ] Set in GitHub secrets
- [ ] Monitor usage in Anthropic console

### 4. ALLOWED_TELEGRAM_IDS
- [ ] Get user IDs from [@userinfobot](https://t.me/userinfobot)
- [ ] Format: `7376426503,7538670249,8191393299` (comma-separated, no spaces)
- [ ] Set in GitHub secrets
- [ ] Verify all authorized users are included

---

## ✅ Post-Setup Verification

- [ ] Run `gh secret list --repo gpt153/health-agent`
- [ ] Verify all 4 secrets appear in the list
- [ ] Check secrets in GitHub UI (Settings → Secrets → Actions)
- [ ] Test GitHub Actions workflow (if configured)
- [ ] Update production `.env.production` with same values
- [ ] Restart production bot to apply new secrets

---

## 📅 Maintenance Schedule

Set calendar reminders:

- [ ] Rotate TELEGRAM_BOT_TOKEN (90 days from today)
- [ ] Rotate OPENAI_API_KEY (90 days from today)
- [ ] Rotate ANTHROPIC_API_KEY (90 days from today)
- [ ] Review ALLOWED_TELEGRAM_IDS (monthly)

**Next rotation date:** _______________

---

## 🔄 Secret Rotation Checklist

When rotating a secret:

- [ ] Generate new secret from provider
- [ ] Update GitHub secret (run setup script again)
- [ ] Update production `.env.production`
- [ ] Restart production bot: `docker compose restart health-agent-bot`
- [ ] Verify bot still works
- [ ] Delete old secret from provider
- [ ] Update rotation date above

---

## 📚 Help & Documentation

- **Interactive Setup:** `./scripts/setup-github-secrets.sh`
- **Detailed Guide:** `docs/GITHUB_SECRETS_SETUP.md`
- **Quick Reference:** `docs/SECRETS_REFERENCE.md`

---

## ⚠️ Security Reminders

- ✅ Never commit secrets to git
- ✅ Never share secrets in chat/email
- ✅ Use separate secrets for dev/prod
- ✅ Rotate secrets every 90 days
- ✅ Revoke old secrets after rotation
- ✅ Monitor API usage for anomalies

---

**Setup Date:** _______________
**Completed By:** _______________
**Next Review:** _______________
