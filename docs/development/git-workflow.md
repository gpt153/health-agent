# Git Workflow

Git branching strategy and workflow for the Health Agent project.

---

## Branch Strategy

```
main (production-ready)
├── feature/add-water-tracking
├── fix/reminder-timezone-bug
└── docs/api-documentation
```

### Branch Types

- **`main`** - Production-ready code, always deployable
- **`feature/*`** - New features (`feature/challenge-system`)
- **`fix/*`** - Bug fixes (`fix/xp-calculation-error`)
- **`docs/*`** - Documentation updates (`docs/deployment-guide`)
- **`refactor/*`** - Code refactoring (`refactor/database-layer`)

---

## Workflow Steps

### 1. Create Feature Branch

```bash
git checkout main
git pull origin main
git checkout -b feature/water-tracking
```

### 2. Make Changes

```bash
# Edit files
# Run tests: pytest
# Format code: black src/
# Check linting: ruff check src/
```

### 3. Commit Changes

```bash
git add src/tracking/water_tracker.py
git commit -m "Add water intake tracking feature

- Created water tracking category
- Added daily water goal setting
- Implemented XP rewards for hydration goals

Part of #123"
```

**Commit Message Format**:
```
<type>: <subject>

<body>

<footer>
```

**Types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### 4. Push Branch

```bash
git push -u origin feature/water-tracking
```

### 5. Create Pull Request

```bash
gh pr create --title "Add water intake tracking" --body "Implements water tracking feature with daily goals and XP rewards"
```

Or use GitHub web UI.

### 6. Review and Merge

- CI/CD runs tests automatically
- Code review by team
- Merge when approved and CI passes

### 7. Delete Branch

```bash
git branch -d feature/water-tracking
git push origin --delete feature/water-tracking
```

---

## Commit Message Guidelines

### Good Commit Messages

```
feat: Add multi-agent nutrition consensus

Implements 3-agent + moderator system for food photo analysis.
Reduces hallucination by 30% compared to single model.

- Conservative, moderate, and optimistic agents analyze in parallel
- Moderator synthesizes estimates with USDA verification
- Confidence level returned with each analysis

Closes #42
```

### Bad Commit Messages

```
Update stuff
Fixed bug
WIP
```

---

## Pull Request Process

### PR Template

```markdown
## Description
Brief description of changes

## Changes
- List of key changes
- What was added/modified/removed

## Testing
- How was this tested?
- Test cases added/updated

## Screenshots (if UI changes)

## Checklist
- [ ] Tests pass locally
- [ ] Code formatted with Black
- [ ] Docstrings updated
- [ ] CHANGELOG.md updated (if applicable)
```

---

## Handling Conflicts

### Merge Conflicts

```bash
# Update your branch with latest main
git checkout feature/my-feature
git fetch origin
git rebase origin/main

# Resolve conflicts in files
# Edit conflicted files, then:
git add <resolved-files>
git rebase --continue

# Force push (rebase rewrites history)
git push --force-with-lease
```

---

## Code Review Guidelines

### For Reviewers

- ✅ Check code follows style guide
- ✅ Verify tests are present and passing
- ✅ Ensure documentation is updated
- ✅ Look for security issues
- ✅ Suggest improvements, not just criticize

### For Authors

- ✅ Respond to all comments
- ✅ Make requested changes or explain why not
- ✅ Keep PRs small and focused (<500 lines)
- ✅ Update PR description if scope changes

---

## Release Process

### Versioning

Semantic Versioning: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes

### Creating a Release

```bash
# Tag release
git tag -a v1.2.0 -m "Release v1.2.0: Add challenge system"
git push origin v1.2.0

# GitHub Actions builds and deploys automatically
```

---

## SCAR Integration

### Isolated Worktrees

When SCAR works on GitHub issues, it creates isolated worktrees:

```
~/.archon/worktrees/
└── health-agent-issue-83/
    ├── src/
    ├── tests/
    └── ...
```

**Benefits**:
- Main codebase stays clean
- Multiple issues worked on in parallel
- Easy to switch between features

---

## Git Hooks

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Run Black formatter
black src/ tests/

# Run Ruff linter
ruff check src/

# Run tests
pytest tests/unit/

# If any fail, abort commit
if [ $? -ne 0 ]; then
    echo "Pre-commit checks failed. Fix errors and try again."
    exit 1
fi
```

Install:
```bash
chmod +x .git/hooks/pre-commit
```

---

## Useful Git Commands

### View Branch Graph

```bash
git log --oneline --graph --all
```

### Undo Last Commit (Keep Changes)

```bash
git reset --soft HEAD~1
```

### Stash Changes

```bash
git stash  # Save changes
git stash pop  # Restore changes
```

### Cherry-Pick Commit

```bash
git cherry-pick <commit-hash>
```

### Interactive Rebase (Clean History)

```bash
git rebase -i HEAD~5  # Last 5 commits
```

---

## Best Practices

- ✅ **Commit often** - Small, logical commits
- ✅ **Write clear messages** - Explain why, not what
- ✅ **Keep branches up to date** - Rebase regularly
- ✅ **Review your own code** - Before creating PR
- ✅ **Delete merged branches** - Keep repository clean

---

## Related Documentation

- **Adding Features**: [adding-features.md](adding-features.md) - Feature development workflow
- **CI/CD**: [/docs/deployment/ci-cd.md](../deployment/ci-cd.md) - Automated testing and deployment

## Revision History

- 2025-01-18: Initial git workflow guide created for Phase 3.7
