# Feature: Fix Development Environment Setup - Separate Docker Production from Native Dev API

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

This feature fixes the development environment configuration to clearly separate production (Docker-based) from development (native Python) workflows. The current setup causes conflicts where both Docker containers and manual Python processes can run simultaneously, leading to Telegram API conflicts and outdated code in Docker images. This enhancement establishes clear documentation, configuration examples, and Docker compose comments to prevent these issues.

## User Story

As a developer working on the health-agent project
I want a clear separation between production and development environments
So that I can develop features natively with hot reload while production runs safely in Docker without conflicts

## Problem Statement

The current development setup has several critical issues:

1. **Duplicate bot instances**: Both Docker container and manual Python process can run simultaneously, causing Telegram API conflicts (`telegram.error.Conflict: terminated by other getUpdates request`)
2. **Outdated Docker API image**: The `health-agent-api` container runs old code (3 days behind), missing recent changes like `get_user_xp_level` function
3. **Port mismatch in `.env.example`**: Database URL points to wrong port (5434 instead of 5436)
4. **Duplicate RUN_MODE in `.env.example`**: Lines 28 and 33 both define RUN_MODE, causing confusion
5. **Unclear architecture**: No documentation explaining when to use Docker vs native Python for development

This leads to confusion, wasted time debugging conflicts, and inconsistent development practices.

## Solution Statement

Implement comprehensive documentation and configuration fixes that establish a clear two-mode architecture:

**Production Mode (Docker):**
- Telegram bot runs in Docker container (`health-agent-bot`)
- PostgreSQL runs in Docker container (always running)
- Exposed on localhost:5436 for native development access

**Development Mode (Native Python):**
- Production bot stays running in Docker (no Telegram conflicts)
- Developer runs API server natively with `RUN_MODE=api python -m src.main`
- Code changes picked up immediately (no Docker rebuild needed)
- SCAR/developers test via REST API at localhost:8080

This follows the established SCAR pattern: databases in Docker, application code native for development.

## Feature Metadata

**Feature Type**: Enhancement (Documentation + Configuration Fix)
**Estimated Complexity**: Low
**Primary Systems Affected**:
- Documentation (new DEVELOPMENT.md, updated README.md)
- Configuration files (.env.example, docker-compose.yml)
**Dependencies**: None (documentation and configuration changes only)

---

## CONTEXT REFERENCES

### Relevant Codebase Files - IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `.env.example` (lines 1-34) - Why: Contains incorrect database port (5434) and duplicate RUN_MODE definitions that need fixing
- `docker-compose.yml` (lines 1-59) - Why: Needs clarifying comments to explain production vs development usage patterns
- `README.md` (lines 1-100) - Why: Quick start guide that needs link to new DEVELOPMENT.md
- `API_README.md` (lines 1-658) - Why: Contains detailed API documentation with deployment patterns to reference
- `src/main.py` (lines 100-120) - Why: Shows RUN_MODE logic (bot/api/both) that documentation must explain
- `Dockerfile` (lines 1-24) - Why: Production Docker setup that documentation references

### New Files to Create

- `DEVELOPMENT.md` - Comprehensive development setup guide explaining production vs development modes, SCAR workflow, and troubleshooting

### Relevant Documentation - YOU SHOULD READ THESE BEFORE IMPLEMENTING!

This is primarily a documentation task, so external documentation is minimal:

- [FastAPI Deployment Best Practices](https://fastapi.tiangolo.com/deployment/concepts/)
  - Specific section: Development vs Production
  - Why: Reference for API development patterns
- [Docker Compose Best Practices](https://docs.docker.com/compose/production/)
  - Specific section: Using Compose in production
  - Why: Guidance on production container usage
- [Python dotenv Documentation](https://pypi.org/project/python-dotenv/)
  - Specific section: .env.example patterns
  - Why: Standard patterns for environment variable examples

### Patterns to Follow

**Environment Variable Documentation Pattern (from .env.example):**
```bash
# Clear section headers
# Variable with inline comment
VARIABLE_NAME=example_value  # Explanation of purpose
```

**Docker Compose Comment Pattern (from existing docker-compose.yml):**
```yaml
services:
  service-name:
    # Brief explanation of service purpose
    environment:
      VARIABLE: value  # Inline explanation
```

**Markdown Documentation Pattern (from README.md and API_README.md):**
```markdown
## Section Header

Brief introduction paragraph.

### Subsection

**Bold labels** for important terms
- Bullet lists for steps or items
- Code blocks with syntax highlighting

**Status indicators:**
- ✅ Working/Completed
- ⚠️ Attention required
- ❌ Not working/Deprecated
```

**RUN_MODE Configuration (from src/main.py lines 100-120):**
```python
run_mode = os.getenv("RUN_MODE", "bot").lower()

if run_mode == "both":
    # Run both bot and API
elif run_mode == "api":
    # Run only API server
elif run_mode == "bot":
    # Run only Telegram bot (default)
```

**Port Configuration Pattern:**
- Docker internal port: 5432 (standard PostgreSQL)
- Docker exposed port: 5436 (custom mapping to avoid conflicts)
- Native development connects to: localhost:5436

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation - Fix Configuration Files

Fix incorrect and duplicate configuration in `.env.example` to provide correct template for developers.

**Tasks:**

- Fix DATABASE_URL port from 5434 to 5436
- Remove duplicate RUN_MODE definition (keep only one at line 29)
- Add clear comment explaining RUN_MODE options
- Ensure all configuration values are correct defaults

### Phase 2: Core Implementation - Create DEVELOPMENT.md

Create comprehensive development setup guide that explains the two-mode architecture and prevents common mistakes.

**Tasks:**

- Document production mode setup (Docker bot + PostgreSQL)
- Document development mode setup (native API for SCAR testing)
- Explain the two-mode architecture clearly
- Provide troubleshooting section for common issues
- Include SCAR workflow integration examples
- Add quick reference section

### Phase 3: Integration - Update Existing Documentation

Update existing documentation to reference new development guide and clarify usage patterns.

**Tasks:**

- Add "Development" section to README.md linking to DEVELOPMENT.md
- Update docker-compose.yml with clarifying comments
- Ensure consistency across all documentation files

### Phase 4: Testing & Validation

Verify that documentation is clear, configuration is correct, and developer workflow is well-explained.

**Tasks:**

- Verify all file references are accurate
- Validate all commands in documentation are executable
- Check markdown formatting renders correctly
- Ensure no broken links or references
- Confirm configuration examples match actual usage patterns

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### UPDATE .env.example

**Goal:** Fix incorrect database port and remove duplicate RUN_MODE configuration

- **IMPLEMENT**: Change DATABASE_URL port from 5432 to 5436 (line 6)
- **PATTERN**: Keep existing comment structure, only change port number
- **GOTCHA**: Don't change the internal Docker connection string - this is the localhost connection example
- **VALIDATE**: `grep "DATABASE_URL.*5436" .env.example`

- **IMPLEMENT**: Remove duplicate RUN_MODE at line 33
- **PATTERN**: Keep only the first RUN_MODE definition with enhanced comment
- **VALIDATE**: `grep -c "^RUN_MODE=" .env.example` (should output "1")

- **IMPLEMENT**: Enhance RUN_MODE comment to explain all three modes (bot/api/both)
- **PATTERN**: Use inline comment with clear explanation
- **EXAMPLE**: `RUN_MODE=bot  # bot (Telegram only), api (REST API only), or both (Telegram + API)`
- **VALIDATE**: `grep "RUN_MODE.*bot.*api.*both" .env.example`

### CREATE DEVELOPMENT.md

**Goal:** Create comprehensive development setup documentation

- **IMPLEMENT**: Create DEVELOPMENT.md with full development guide
- **STRUCTURE**: Use this outline:
  - Overview (architecture explanation)
  - Quick Start (TL;DR for experienced devs)
  - Production Mode Setup
  - Development Mode Setup (native API)
  - SCAR Integration Workflow
  - Docker vs Native Decision Matrix
  - Troubleshooting Common Issues
  - FAQ
- **PATTERN**: Follow markdown patterns from README.md and API_README.md
- **CONTENT**: Include these key sections:
  - Why this architecture (databases in Docker, app native for dev)
  - Step-by-step production setup
  - Step-by-step development setup
  - How SCAR uses the REST API for testing
  - Common error scenarios and fixes
  - Port reference table (5436 PostgreSQL, 8080 API)
- **VALIDATE**: `test -f DEVELOPMENT.md && wc -l DEVELOPMENT.md` (should be substantial, 200+ lines)

- **IMPLEMENT**: Add "Two-Mode Architecture" diagram in ASCII/markdown
- **PATTERN**: Use markdown code blocks or simple text diagrams
- **EXAMPLE**:
```
Production Mode:          Development Mode:
┌─────────────────┐      ┌─────────────────┐
│ Docker Bot      │      │ Docker Bot      │ (still running)
│ (Telegram)      │      │ (Telegram)      │
└────────┬────────┘      └─────────────────┘
         │
    ┌────▼────────┐      ┌─────────────────┐
    │ PostgreSQL  │◄─────┤ Native API      │ (development)
    │ (Docker)    │      │ (localhost:8080)│
    └─────────────┘      └─────────────────┘
```
- **VALIDATE**: `grep -A5 "Production Mode" DEVELOPMENT.md`

- **IMPLEMENT**: Add troubleshooting section with actual error messages and fixes
- **PATTERN**: Use code blocks for errors, step-by-step fixes
- **INCLUDE**: These common issues:
  - "Conflict: terminated by other getUpdates request" → Explain how to check for duplicate bots
  - "Connection refused" → Check PostgreSQL is running
  - "Module not found" → Verify virtual environment activation
  - Port already in use → How to check what's using port 8080
- **VALIDATE**: `grep -i "conflict.*getUpdates" DEVELOPMENT.md`

- **IMPLEMENT**: Add SCAR workflow integration section
- **PATTERN**: Code examples showing how SCAR tests implementations
- **CONTENT**: Explain that SCAR:
  - Works on GitHub issues in isolated worktrees
  - Tests implementations via REST API at localhost:8080
  - Requires native API running (not Docker) for code changes
  - Benefits from hot reload during iterative development
- **VALIDATE**: `grep -i "scar" DEVELOPMENT.md`

- **IMPLEMENT**: Add "Quick Reference" section at top
- **PATTERN**: Table format with commands and descriptions
- **CONTENT**:
```markdown
| Task | Command |
|------|---------|
| Start production bot | `docker compose up -d health-agent-bot postgres` |
| Start dev API | `RUN_MODE=api python -m src.main` |
| Check PostgreSQL | `docker compose ps postgres` |
| Test API | `curl http://localhost:8080/api/health` |
```
- **VALIDATE**: `grep -A5 "Quick Reference" DEVELOPMENT.md`

### UPDATE README.md

**Goal:** Add link to DEVELOPMENT.md for detailed development setup

- **IMPLEMENT**: Add "Development" section after "🚀 Quick Start" section (around line 40)
- **PATTERN**: Match existing README.md section structure with emoji headers
- **CONTENT**:
```markdown
## 🛠️ Development

For detailed development setup, architecture explanation, and SCAR integration:

**[📖 See DEVELOPMENT.md](DEVELOPMENT.md)**

This covers:
- Production vs Development modes
- Native API setup for fast iteration
- SCAR testing workflow
- Troubleshooting common issues
```
- **VALIDATE**: `grep -A3 "See DEVELOPMENT.md" README.md`

### UPDATE docker-compose.yml

**Goal:** Add clarifying comments explaining production vs development usage

- **IMPLEMENT**: Add service-level comment for health-agent-bot
- **PATTERN**: YAML comment above service definition
- **CONTENT**:
```yaml
  # Production Telegram Bot (always running)
  # Polls Telegram API for user messages
  # RUN_MODE=bot ensures no conflicts with dev API
  health-agent-bot:
```
- **VALIDATE**: `grep -B1 "health-agent-bot:" docker-compose.yml | grep "Production Telegram Bot"`

- **IMPLEMENT**: Add service-level comment for health-agent-api
- **PATTERN**: YAML comment above service definition
- **CONTENT**:
```yaml
  # Optional: API Server (Docker mode)
  # For CI/testing only - developers should run natively for hot reload
  # See DEVELOPMENT.md for native setup instructions
  health-agent-api:
```
- **VALIDATE**: `grep -B1 "health-agent-api:" docker-compose.yml | grep "Optional"`

- **IMPLEMENT**: Add comment explaining postgres port mapping
- **PATTERN**: Inline YAML comment
- **CONTENT**:
```yaml
    ports:
      - "5436:5432"  # Host:Container - Use localhost:5436 from native dev environment
```
- **VALIDATE**: `grep "5436.*Host:Container" docker-compose.yml`

- **IMPLEMENT**: Add header comment explaining overall architecture
- **PATTERN**: Multi-line comment at top after version
- **CONTENT**:
```yaml
version: '3.8'

# Health Agent Docker Compose Configuration
#
# Production Setup (always running):
#   - postgres: Database accessible at localhost:5436
#   - health-agent-bot: Telegram bot (RUN_MODE=bot)
#
# Development Setup (RECOMMENDED):
#   - Keep postgres + health-agent-bot running
#   - Run API natively: RUN_MODE=api python -m src.main
#   - See DEVELOPMENT.md for details
```
- **VALIDATE**: `head -15 docker-compose.yml | grep "DEVELOPMENT.md"`

---

## TESTING STRATEGY

This is primarily a documentation and configuration task, so testing focuses on validation of accuracy and usability.

### Documentation Validation

**Scope:** Verify all documentation is accurate, complete, and renders correctly

- **Markdown rendering**: Ensure all markdown syntax is valid
- **Command accuracy**: Verify all example commands are executable
- **File references**: Check all file paths and line numbers are accurate
- **Link validation**: Ensure internal links work
- **Consistency**: Verify consistency across all documentation files

### Configuration Validation

**Scope:** Verify configuration files have correct values and no duplicates

- **Port numbers**: Confirm database port is 5436 in all references
- **RUN_MODE**: Ensure only one RUN_MODE definition exists
- **Syntax**: Validate .env.example syntax is correct
- **Docker compose**: Verify docker-compose.yml is valid YAML

### Manual Testing

**Scope:** Verify developer can follow documentation successfully

- **Fresh clone simulation**: Documentation should work for new developer
- **Command execution**: All commands in docs should execute without error
- **Troubleshooting section**: Common issues should have working solutions

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Configuration File Validation

**Verify .env.example has correct database port:**

```bash
grep "DATABASE_URL.*localhost:5436" .env.example
```

**Expected:** Line showing `DATABASE_URL=postgresql://postgres:postgres@localhost:5436/health_agent`

**Why:** Prevents developers from using wrong port and failing to connect to Docker PostgreSQL

**Verify only one RUN_MODE in .env.example:**

```bash
grep -c "^RUN_MODE=" .env.example
```

**Expected:** `1`

**Why:** Ensures no duplicate configuration causing confusion

**Validate docker-compose.yml syntax:**

```bash
docker compose config --quiet
```

**Expected:** No output (silent success)

**Why:** Confirms YAML syntax is valid before developers try to use it

### Level 2: Documentation Existence

**Verify DEVELOPMENT.md exists:**

```bash
test -f DEVELOPMENT.md && echo "✓ DEVELOPMENT.md exists" || echo "✗ Missing"
```

**Expected:** `✓ DEVELOPMENT.md exists`

**Why:** Core deliverable of this feature

**Verify README.md links to DEVELOPMENT.md:**

```bash
grep -i "DEVELOPMENT.md" README.md
```

**Expected:** Line containing markdown link to DEVELOPMENT.md

**Why:** Ensures discoverability of new documentation

### Level 3: Documentation Content Validation

**Verify DEVELOPMENT.md explains two-mode architecture:**

```bash
grep -i "production mode\|development mode" DEVELOPMENT.md | head -2
```

**Expected:** Multiple lines explaining production and development modes

**Why:** Core concept that must be documented

**Verify troubleshooting section exists:**

```bash
grep -i "troubleshooting\|common issues" DEVELOPMENT.md
```

**Expected:** Section header for troubleshooting

**Why:** Helps developers resolve problems independently

**Verify SCAR workflow is documented:**

```bash
grep -i "scar" DEVELOPMENT.md
```

**Expected:** References to SCAR testing workflow

**Why:** Critical for GitHub issue-based development workflow

### Level 4: Docker Compose Comments Validation

**Verify health-agent-bot has clarifying comment:**

```bash
grep -B3 "health-agent-bot:" docker-compose.yml | grep -i "production"
```

**Expected:** Comment explaining production bot usage

**Why:** Prevents confusion about which container to use for development

**Verify health-agent-api has clarifying comment:**

```bash
grep -B3 "health-agent-api:" docker-compose.yml | grep -i "optional\|native"
```

**Expected:** Comment explaining to use native for development

**Why:** Guides developers to correct development workflow

**Verify postgres port has comment:**

```bash
grep "5436.*#" docker-compose.yml
```

**Expected:** Port mapping with inline comment

**Why:** Clarifies which port to use from native development environment

### Level 5: Markdown Rendering Validation

**Check for broken markdown syntax:**

```bash
# Verify no unclosed code blocks in DEVELOPMENT.md
python3 -c "
import re
with open('DEVELOPMENT.md') as f:
    content = f.read()
    code_blocks = re.findall(r'```', content)
    if len(code_blocks) % 2 == 0:
        print('✓ All code blocks properly closed')
    else:
        print('✗ Unclosed code block found')
        exit(1)
"
```

**Expected:** `✓ All code blocks properly closed`

**Why:** Prevents broken rendering on GitHub

**Verify headers are properly formatted:**

```bash
grep "^#" DEVELOPMENT.md | head -5
```

**Expected:** Multiple lines starting with # (markdown headers)

**Why:** Ensures proper document structure

### Level 6: Manual Validation Steps

**Test database connection with documented port:**

```bash
# Verify postgres is accessible on port 5436 as documented
docker compose ps postgres && echo "✓ PostgreSQL running" || echo "✗ PostgreSQL not running"
```

**Expected:** `✓ PostgreSQL running`

**Why:** Confirms documented port matches actual Docker configuration

**Verify API can start in development mode:**

```bash
# This is a dry-run check - we don't actually start the server
python3 -c "
import os
os.environ['RUN_MODE'] = 'api'
# Just verify imports work, don't actually start server
from src.config import validate_config
print('✓ API mode imports successful')
"
```

**Expected:** `✓ API mode imports successful`

**Why:** Confirms documented development mode actually works

---

## ACCEPTANCE CRITERIA

- [ ] `.env.example` has correct database port (5436) and single RUN_MODE definition
- [ ] DEVELOPMENT.md exists with comprehensive development guide (200+ lines)
- [ ] DEVELOPMENT.md explains two-mode architecture clearly
- [ ] DEVELOPMENT.md includes troubleshooting section with common errors
- [ ] DEVELOPMENT.md documents SCAR workflow integration
- [ ] DEVELOPMENT.md includes quick reference table
- [ ] README.md links to DEVELOPMENT.md in Development section
- [ ] docker-compose.yml has clarifying comments for all services
- [ ] docker-compose.yml has header comment explaining architecture
- [ ] All validation commands pass successfully
- [ ] Markdown syntax is valid (all code blocks closed)
- [ ] All file references are accurate
- [ ] Configuration examples match actual usage
- [ ] No duplicate or conflicting configuration
- [ ] Documentation is clear enough for new developer to follow

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Documentation reviewed for clarity and completeness
- [ ] Configuration files have no syntax errors
- [ ] Markdown renders correctly on GitHub
- [ ] Links and references are accurate
- [ ] Code examples are executable
- [ ] Troubleshooting section is comprehensive
- [ ] SCAR workflow is clearly documented

---

## NOTES

### Design Decisions

**Two-Mode Architecture Rationale:**
- Follows SCAR pattern: databases in Docker, application code native for development
- Prevents Telegram bot conflicts (only one bot instance polling API)
- Enables hot reload for fast development iteration
- Keeps production environment isolated and stable

**Documentation Structure:**
- DEVELOPMENT.md is comprehensive and standalone
- README.md stays concise with link to detailed docs
- API_README.md focuses on API-specific usage (unchanged)
- Separation of concerns keeps each doc focused

**Configuration Fixes:**
- Port 5436 matches actual Docker compose configuration
- Single RUN_MODE prevents override confusion
- Enhanced comments guide developers to correct choices

### Trade-offs

**Docker API Container:**
- Kept in docker-compose.yml for CI/testing use cases
- Added comments discouraging for development
- Alternative: Could remove entirely, but useful for deployment testing

**Documentation Length:**
- DEVELOPMENT.md will be substantial (200+ lines)
- Trade-off: Comprehensive vs concise
- Decision: Comprehensive to prevent all common issues

### Future Enhancements

Potential follow-up improvements (out of scope for this feature):

- Add Makefile with common development commands
- Create development Docker compose override file
- Add pre-commit hooks to validate .env against .env.example
- Create video walkthrough of development setup
- Add VS Code launch.json configurations

### Related Issues

This fix addresses the root cause discovered in:
- Telegram bot conflict errors
- Outdated Docker API container missing recent code
- Developer confusion about when to use Docker vs native
