# Continuous Deployment (CD) Setup Guide

## Overview

The health-agent repository now has **automated continuous deployment** configured. When you push to the `main` branch:

1. ✅ GitHub Actions builds a Docker image
2. ✅ Pushes image to GitHub Container Registry (ghcr.io)
3. ✅ **Automatically deploys to production** (new!)

## Current Status

- ✅ CI Pipeline: Fully working
- ✅ Deploy Script: Created and tested (`/home/samuel/odin-health/deploy.sh`)
- ✅ GitHub Workflow: Updated with deployment job
- ⏳ GitHub Secrets: **Need to be configured** (see below)

---

## One-Time Setup Required

### Step 1: Generate SSH Key for Deployment

On your production VM, generate an SSH key that GitHub Actions will use:

```bash
# Generate SSH key (no passphrase for automation)
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy_key -N ""

# Add public key to authorized_keys
cat ~/.ssh/github_deploy_key.pub >> ~/.ssh/authorized_keys

# Set correct permissions
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh

# Display private key (you'll need this for GitHub)
cat ~/.ssh/github_deploy_key
```

### Step 2: Add GitHub Secrets

Go to your repository settings on GitHub:
**https://github.com/gpt153/health-agent/settings/secrets/actions**

Add these 3 secrets:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `DEPLOY_HOST` | Your VM's IP or hostname | e.g., `203.0.113.10` or `vm.example.com` |
| `DEPLOY_USER` | `samuel` | The SSH user on your VM |
| `DEPLOY_SSH_KEY` | Contents of `~/.ssh/github_deploy_key` | The **private** key (entire file) |

**How to add a secret:**
1. Click "New repository secret"
2. Enter the name (exactly as shown above)
3. Paste the value
4. Click "Add secret"

### Step 3: Test SSH Access

Verify that GitHub Actions can SSH to your VM:

```bash
# From another machine or terminal, test the key:
ssh -i ~/.ssh/github_deploy_key samuel@YOUR_VM_IP "echo 'SSH access works!'"
```

If this works, GitHub Actions will be able to deploy.

---

## How It Works

### Deployment Flow

```
Push to main
    ↓
GitHub Actions: Build Docker Image
    ↓
Push to ghcr.io/gpt153/health-agent:main
    ↓
GitHub Actions: SSH to production VM
    ↓
Run /home/samuel/odin-health/deploy.sh
    ↓
Pull latest image → Stop old container → Start new container
    ↓
✅ Deployment Complete!
```

### Deploy Script Features

The deployment script (`/home/samuel/odin-health/deploy.sh`) includes:

- ✅ **Backup before deploy** - Tags current image
- ✅ **Automatic rollback** - If deployment fails, restores previous version
- ✅ **Health checks** - Verifies containers are running
- ✅ **Database safety** - Keeps database running during updates
- ✅ **Cleanup** - Removes old backup images (keeps last 3)
- ✅ **Zero data loss** - Only restarts the app, not the database

### Manual Deployment

You can also trigger deployment manually:

```bash
# Option 1: Run deploy script directly
cd /home/samuel/odin-health
./deploy.sh

# Option 2: Trigger GitHub Actions manually
# Go to: https://github.com/gpt153/health-agent/actions/workflows/docker-build-deploy.yml
# Click "Run workflow"
```

---

## Monitoring Deployments

### GitHub Actions

View deployment status:
**https://github.com/gpt153/health-agent/actions**

Each push to `main` creates a new workflow run showing:
- Build status
- Deploy status
- Deployment logs

### Production Logs

Check deployment on the VM:

```bash
# View deployment logs
cd /home/samuel/odin-health
docker compose logs -f health-agent

# Check container status
docker compose ps

# View recent deployments
docker images odin-health-agent
```

---

## Troubleshooting

### Deployment Fails

**1. Check GitHub Actions logs:**
   - Go to Actions tab → Click failed workflow → View "Deploy to Production" job

**2. Common issues:**

| Error | Solution |
|-------|----------|
| "Permission denied (publickey)" | Check SSH key is correctly added to secrets |
| "deploy.sh: not found" | Ensure script exists at `/home/samuel/odin-health/deploy.sh` |
| "Failed to pull image" | Check GitHub Container Registry permissions |
| "Container not running" | Check container logs: `docker compose logs health-agent` |

### Manual Rollback

If deployment breaks and auto-rollback didn't work:

```bash
cd /home/samuel/odin-health

# List backup images
docker images odin-health-agent

# Use a specific backup
docker tag odin-health-agent:backup-YYYYMMDD-HHMMSS ghcr.io/gpt153/health-agent:main
docker compose up -d
```

### Skip CD for a Commit

If you want to push to `main` without deploying:

```bash
# Add [skip ci] to commit message
git commit -m "Update docs [skip ci]"
```

---

## Security Notes

- SSH private key is stored as a GitHub secret (encrypted)
- Only runs on pushes to `main` branch
- Deploy script requires specific directory structure
- Database credentials remain in `.env` file (never committed)

---

## Next Steps

1. ✅ Complete "One-Time Setup" steps above
2. ✅ Test deployment by pushing a small change to `main`
3. ✅ Monitor deployment via GitHub Actions
4. ✅ Verify health-agent is running with new version

---

## Files Modified

- ✅ `.github/workflows/docker-build-deploy.yml` - Added deployment job
- ✅ `/home/samuel/odin-health/deploy.sh` - Production deployment script

---

**Questions?** Check GitHub Actions logs or review deploy script comments.
