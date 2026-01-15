---
description: Test Suite Runner - Execute Playwright tests for a specific feature area
argument-hint: <project> <url> <deployment-type> <feature-name> <session-id>
---

# UI Test Suite Runner

## Mission

Execute Playwright E2E tests for a specific feature area. Generate test code from plan requirements, run tests, capture evidence on failures, and report results.

**Context Usage**: ~20-30k tokens (feature-specific, exits after reporting)

**Lifecycle**: Spawn → Test → Report → Exit

## Arguments

- **$1**: Project name (e.g., "consilio")
- **$2**: Deployment URL (e.g., "http://localhost:3002")
- **$3**: Deployment type (docker|native|production)
- **$4**: Feature name (e.g., "User Authentication")
- **$5**: Session ID (e.g., "ui-test-1736621400")

## Task Flow

### Step 1: Setup Test Environment

```bash
PROJECT=$1
URL=$2
DEPLOY_TYPE=$3
FEATURE=$4
SESSION=$5

# Create feature-specific directory
FEATURE_SLUG=$(echo "$FEATURE" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
TEST_DIR=".agents/ui-testing/session-$SESSION/runners/$FEATURE_SLUG"
mkdir -p $TEST_DIR

echo "Testing feature: $FEATURE"
echo "URL: $URL"
echo "Type: $DEPLOY_TYPE"
```

### Step 2: Read Plan Requirements

Extract requirements for this specific feature:

```bash
# Find implementation plan
PLAN_FILE=$(find .agents/plans -name "*frontend*" -o -name "*implementation*" -o -name "*ui*" 2>/dev/null | head -1)

if [ -z "$PLAN_FILE" ]; then
  PLAN_FILE=$(find . -maxdepth 2 -name "*PLAN.md" 2>/dev/null | head -1)
fi

echo "Reading plan: $PLAN_FILE"
```

**Search for feature section:**

Look for patterns like:
- "## $FEATURE"
- "### $FEATURE"
- Feature name in bullet points or headers

**Extract requirements:**

Example for "User Authentication":
```markdown
## Requirements Extracted

**Feature**: User Authentication

**User Stories**:
1. User can log in with email and password
2. User can reset password via email
3. User session persists across page refreshes
4. User can log out

**Acceptance Criteria**:
- Login form validates email format
- Password must be 8+ characters
- Failed login shows error message
- Successful login redirects to dashboard
- Logout clears session and redirects to login

**UI Elements**:
- Login form at /login
- Email input field
- Password input field
- Submit button
- "Forgot password" link
- Error message display area
```

Save to: `$TEST_DIR/requirements.md`

### Step 3: Generate Playwright Test Code

Based on requirements, create test specification:

```typescript
// File: $TEST_DIR/test-spec.ts

import { test, expect } from '@playwright/test';

test.describe('$FEATURE', () => {
  // Generate test cases based on requirements

  test('should load login page', async ({ page }) => {
    await page.goto('$URL/login');
    await expect(page).toHaveURL(/.*login/);
    await expect(page.locator('form')).toBeVisible();
  });

  test('should login with valid credentials', async ({ page }) => {
    await page.goto('$URL/login');

    // Fill form
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'password123');

    // Submit
    await page.click('button[type="submit"]');

    // Verify redirect
    await expect(page).toHaveURL(/.*dashboard/);

    // Verify user is logged in (check for user element)
    await expect(page.locator('.user-name, [data-testid="user-name"]')).toBeVisible();
  });

  test('should reject invalid credentials', async ({ page }) => {
    await page.goto('$URL/login');

    await page.fill('input[name="email"]', 'wrong@example.com');
    await page.fill('input[type="password"]', 'wrongpass');
    await page.click('button[type="submit"]');

    // Should stay on login page
    await expect(page).toHaveURL(/.*login/);

    // Should show error
    await expect(page.locator('.error, .error-message, [role="alert"]')).toBeVisible();
  });

  test('should validate email format', async ({ page }) => {
    await page.goto('$URL/login');

    await page.fill('input[name="email"]', 'not-an-email');
    await page.fill('input[type="password"]', 'password123');
    await page.click('button[type="submit"]');

    // Should show validation error
    await expect(page.locator('.error, [data-testid="email-error"]')).toBeVisible();
  });

  test('should handle password reset flow', async ({ page }) => {
    await page.goto('$URL/login');

    // Click forgot password link
    await page.click('a:has-text("Forgot"), a:has-text("Reset")');

    // Should navigate to reset page
    await expect(page).toHaveURL(/.*reset|forgot/);

    // Fill email
    await page.fill('input[name="email"]', 'test@example.com');
    await page.click('button[type="submit"]');

    // Should show confirmation
    await expect(page.locator('.success, .confirmation')).toBeVisible();
  });

  test('should persist session after refresh', async ({ page }) => {
    // Login first
    await page.goto('$URL/login');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'password123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/.*dashboard/);

    // Refresh page
    await page.reload();

    // Should still be logged in
    await expect(page).toHaveURL(/.*dashboard/);
    await expect(page.locator('.user-name')).toBeVisible();
  });

  test('should logout successfully', async ({ page }) => {
    // Login first
    await page.goto('$URL/login');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'password123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/.*dashboard/);

    // Logout
    await page.click('button:has-text("Logout"), a:has-text("Logout"), [data-testid="logout"]');

    // Should redirect to login
    await expect(page).toHaveURL(/.*login/);

    // Trying to access dashboard should redirect back to login
    await page.goto('$URL/dashboard');
    await expect(page).toHaveURL(/.*login/);
  });
});
```

**Adapt test code based on:**
- Actual plan requirements
- Feature complexity
- UI patterns mentioned in plan
- Acceptance criteria listed

Write test file to: `tests/$FEATURE_SLUG.spec.ts`

### Step 4: Run Playwright Tests

```bash
# Determine test command based on deployment type
if [ "$DEPLOY_TYPE" = "docker" ]; then
  TEST_CMD="npm run test:e2e:docker -- tests/$FEATURE_SLUG.spec.ts"
else
  TEST_CMD="npm run test:e2e -- tests/$FEATURE_SLUG.spec.ts"
fi

echo "Running tests: $TEST_CMD"

# Run tests and capture output
$TEST_CMD > $TEST_DIR/test-output.log 2>&1
TEST_EXIT_CODE=$?

# Also capture to see results
cat $TEST_DIR/test-output.log
```

### Step 5: Analyze Results

```bash
# Parse test results
TESTS_RUN=$(grep -c "✓\|✗" $TEST_DIR/test-output.log || echo "0")
TESTS_PASSED=$(grep -c "✓" $TEST_DIR/test-output.log || echo "0")
TESTS_FAILED=$(grep -c "✗" $TEST_DIR/test-output.log || echo "0")

echo "Tests run: $TESTS_RUN"
echo "Passed: $TESTS_PASSED"
echo "Failed: $TESTS_FAILED"

if [ $TEST_EXIT_CODE -eq 0 ]; then
  RESULT_STATUS="passed"
else
  RESULT_STATUS="failed"
fi
```

### Step 6A: Handle Success

If all tests passed:

```markdown
## ✅ Feature Test Results: $FEATURE

**Status**: PASSED
**Tests Run**: $TESTS_RUN
**All Passed**: ✅

**Test Cases**:
- Load login page ✅
- Login with valid credentials ✅
- Reject invalid credentials ✅
- Validate email format ✅
- Password reset flow ✅
- Session persistence ✅
- Logout ✅

**Evidence**: $TEST_DIR/test-output.log

---

**Recommendation**: Feature is working as expected per plan requirements.
```

Save to: `$TEST_DIR/results.md`

**Report to supervisor:**

Update test-state.json (use atomic update):
```json
{
  "features": {
    "$FEATURE_SLUG": {
      "status": "passed",
      "tests_run": $TESTS_RUN,
      "tests_passed": $TESTS_PASSED,
      "tests_failed": 0,
      "all_passed": true,
      "completed": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
      "evidence": "$TEST_DIR/results.md"
    }
  }
}
```

**Exit with success code 0**

### Step 6B: Handle Failure

If any tests failed:

**1. Capture Evidence**

```bash
# Find screenshot files (Playwright auto-generates on failure)
SCREENSHOTS=$(find playwright-report test-results -name "*.png" 2>/dev/null)

# Copy screenshots to session directory
for img in $SCREENSHOTS; do
  cp "$img" "$TEST_DIR/screenshots/"
done

# Find video files
VIDEOS=$(find playwright-report test-results -name "*.webm" 2>/dev/null)

for vid in $VIDEOS; do
  cp "$vid" "$TEST_DIR/screenshots/"
done

echo "Evidence captured:"
ls -lh $TEST_DIR/screenshots/
```

**2. Extract Failure Details**

Parse test output for:
- Which tests failed
- Error messages
- Stack traces
- Timeout errors

Example output parsing:
```bash
# Extract failed test names
grep "✗" $TEST_DIR/test-output.log | sed 's/✗//' > $TEST_DIR/failed-tests.txt

# Extract error messages
grep -A 5 "Error:" $TEST_DIR/test-output.log > $TEST_DIR/errors.txt
```

**3. Create GitHub Issue**

```bash
# Create issue with evidence
gh issue create \
  --repo "gpt153/$PROJECT" \
  --title "UI Test Failure: $FEATURE" \
  --label "bug,ui-test-failure,$FEATURE_SLUG" \
  --body "$(cat <<EOF
## 🐛 UI Test Failure: $FEATURE

**Feature**: $FEATURE
**Environment**: $DEPLOY_TYPE ($URL)
**Detected**: $(date -u +%Y-%m-%dT%H:%M:%SZ)
**Session**: $SESSION

---

## Test Results

**Tests Run**: $TESTS_RUN
**Passed**: $TESTS_PASSED ✅
**Failed**: $TESTS_FAILED ❌

---

## Failed Tests

$(cat $TEST_DIR/failed-tests.txt)

---

## Error Details

\`\`\`
$(head -100 $TEST_DIR/errors.txt)
\`\`\`

---

## Evidence

**Screenshots**: Available in test artifacts
**Test Output**: $TEST_DIR/test-output.log
**Plan Reference**: See \`$PLAN_FILE\` - section on "$FEATURE"

---

## Reproduction

\`\`\`bash
# Navigate to project
cd \$(pwd)

# Run test
$TEST_CMD
\`\`\`

---

## Recommended Action

@scar please investigate and fix this UI test failure:

1. Run root cause analysis: \`/command-invoke rca {ISSUE_NUMBER}\`
2. Implement fix: \`/command-invoke fix-rca {ISSUE_NUMBER}\`

---

**Created by**: UI Test Suite Runner (automated)
EOF
)"

# Capture issue number
ISSUE_NUM=$(gh issue list --repo "gpt153/$PROJECT" --limit 1 --json number -q '.[0].number')

echo "Created issue #$ISSUE_NUM"
```

**4. Report Failure to Supervisor**

```markdown
## ❌ Feature Test Results: $FEATURE

**Status**: FAILED
**Tests Run**: $TESTS_RUN
**Passed**: $TESTS_PASSED
**Failed**: $TESTS_FAILED

**GitHub Issue**: #$ISSUE_NUM

**Failed Tests**:
$(cat $TEST_DIR/failed-tests.txt)

**Evidence**:
- Test output: $TEST_DIR/test-output.log
- Screenshots: $TEST_DIR/screenshots/
- Errors: $TEST_DIR/errors.txt

---

**Action Taken**: Created issue #$ISSUE_NUM for SCAR to investigate and fix.
```

Save to: `$TEST_DIR/results.md`

Update test-state.json:
```json
{
  "features": {
    "$FEATURE_SLUG": {
      "status": "failed",
      "tests_run": $TESTS_RUN,
      "tests_passed": $TESTS_PASSED,
      "tests_failed": $TESTS_FAILED,
      "bug_issue": $ISSUE_NUM,
      "locked_for_fix": true,
      "completed": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
      "evidence": "$TEST_DIR/results.md"
    }
  },
  "bugs": {
    "$ISSUE_NUM": {
      "feature": "$FEATURE_SLUG",
      "title": "UI Test Failure: $FEATURE",
      "created": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
      "status": "pending_rca",
      "tests_failed": $TESTS_FAILED
    }
  }
}
```

**Exit with code 1 (failure)**

## Test Generation Guidelines

### Selector Strategies

Use resilient selectors that work across different implementations:

```typescript
// ✅ GOOD - Multiple fallbacks
await page.locator('.user-name, [data-testid="user-name"], .header .name').first()

// ✅ GOOD - Role-based
await page.getByRole('button', { name: /login|sign in/i })

// ✅ GOOD - Text-based with regex
await page.locator('button:has-text("Login"), button:has-text("Sign In")')

// ❌ AVOID - Too specific
await page.locator('#user-name-display-element')

// ❌ AVOID - Fragile CSS
await page.locator('div > div > span.name')
```

### Timeout Handling

```typescript
// Allow reasonable timeouts for async operations
await expect(page.locator('.dashboard')).toBeVisible({ timeout: 10000 });

// For API-dependent features, be generous
await expect(page.locator('.chat-messages')).toContainText(/Welcome/, { timeout: 15000 });
```

### Test Data

Use consistent test data:

```typescript
// Standard test credentials
const TEST_USER = {
  email: 'test@example.com',
  password: 'password123'
};

// Use in all tests for consistency
await page.fill('input[name="email"]', TEST_USER.email);
```

### Error Handling

```typescript
// Gracefully handle optional elements
try {
  await page.click('.cookie-banner button:has-text("Accept")', { timeout: 2000 });
} catch {
  // Cookie banner not present, continue
}

// Test main flow
await page.goto('/login');
// ...
```

## Special Cases

### Feature Depends on Authentication

If feature requires being logged in:

```typescript
test.describe('$FEATURE (requires auth)', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('$URL/login');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'password123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/.*dashboard/);
  });

  // Now test the actual feature
  test('should access feature X', async ({ page }) => {
    await page.goto('$URL/feature-x');
    // ...
  });
});
```

### Feature Has API Dependencies

If feature needs external API:

```typescript
test('should load data from API', async ({ page }) => {
  await page.goto('$URL/dashboard');

  // Wait for API call to complete (indicated by loading spinner disappearing)
  await expect(page.locator('.loading-spinner')).not.toBeVisible({ timeout: 15000 });

  // Verify data displayed
  await expect(page.locator('.data-table tr')).toHaveCount(5, { timeout: 5000 });
});
```

If API requires secrets (e.g., Stripe):

```markdown
⚠️ **Note in test results**: This feature requires external API access.

If tests fail with "API key invalid" or similar:
1. Verify secrets are set: `/secret-check STRIPE_SECRET_KEY`
2. Sync to workspace: `/secret-sync`
3. Restart deployment with secrets
4. Rerun tests
```

## Output Format

Always produce:

1. **requirements.md** - Extracted requirements from plan
2. **test-spec.ts** - Generated Playwright test code
3. **test-output.log** - Raw test execution output
4. **results.md** - Formatted test results
5. **screenshots/** - Evidence if tests failed
6. **Update to test-state.json** - Atomic state update

## Communication

**To Supervisor**: Only report results via test-state.json updates and results.md

**To User**: None (runner is invisible to user, only supervisor sees results)

**To GitHub**: Only if failure (create issue with evidence)

## Success Criteria

- ✅ Tests generated correctly from plan requirements
- ✅ All tests executed successfully
- ✅ Results accurately reported to supervisor
- ✅ Evidence captured for any failures
- ✅ GitHub issue created with actionable information
- ✅ Context freed after completion (exit)

---

**Execute tests and report** - this runner completes and exits after reporting results.
