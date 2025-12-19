# Implementation Plan: Master Code Feature + Production Deployment Fix

**GitHub Issue**: #12
**Status**: Open
**Priority**: High
**Created**: 2024-12-19

---

## Executive Summary

This plan addresses two critical items:

1. **Deploy existing fix to production** - The admin recognition and invite code collision fixes are on branch `issue-12` but NOT merged to `main`, so they're not deployed to production
2. **Add master code feature** - Create a special reusable invite code for friends/family with full access

---

## Problem Analysis

### Issue 1: Fix Not Deployed
**Root Cause**: Commit `96fd2cf` with the fix is on `origin/issue-12` branch but has NOT been merged to `origin/main`. Production runs from `main` branch.

**Evidence**:
```bash
# Fix commit exists on issue-12 branch
git log origin/main..origin/issue-12
> 96fd2cf fix(auth): resolve GitHub issue #12 - invite code generation and admin recognition

# This commit is NOT on main branch yet
```

**Impact**: All the admin recognition fixes and collision retry logic are not active in production.

### Issue 2: No Master Code Support
**Current Limitation**: All invite codes have `max_uses` that limits how many times they can be redeemed. Once used up, the code becomes invalid.

**User Request**: Create a special "master-code" that:
- Can be reused indefinitely (unlimited uses)
- Can be shared with close friends and family
- Grants full access (premium tier)
- Never expires

---

## Implementation Plan

### Phase 1: Deploy Existing Fix (URGENT - 15 minutes)

**Goal**: Merge fix to main and deploy to production

**Steps**:
1. ✅ Verify fix is complete and tested on issue-12 branch
2. Create pull request from `issue-12` to `main`
3. Review PR (ensure all tests pass)
4. Merge PR to main
5. Deploy main to production
6. Verify admin can generate codes in production

**Files Already Fixed** (on issue-12 branch):
- `src/utils/auth.py` - Type normalization for admin check
- `src/agent/__init__.py` - Collision retry logic

**Tests Already Created**:
- `tests/unit/test_auth.py` - Admin check tests
- `tests/integration/test_invite_codes.py` - Full invite code workflow tests

**Acceptance Criteria**:
- ✅ Admin (ID: 7376426503) can generate invite codes in production
- ✅ No type mismatch errors
- ✅ Collision retries work correctly

---

### Phase 2: Master Code Feature (30-45 minutes)

**Goal**: Add support for permanent, reusable master codes

#### 2.1 Database Schema Enhancement

**File**: `migrations/004_master_code_support.sql` (NEW)

**Changes**:
```sql
-- Add master code support
ALTER TABLE invite_codes ADD COLUMN IF NOT EXISTS is_master_code BOOLEAN DEFAULT false;
ALTER TABLE invite_codes ADD COLUMN IF NOT EXISTS description TEXT;

-- Create index for master codes
CREATE INDEX IF NOT EXISTS idx_invite_codes_master ON invite_codes(is_master_code) WHERE is_master_code = true;

-- Add comment
COMMENT ON COLUMN invite_codes.is_master_code IS 'true for permanent reusable codes, false for regular codes';
COMMENT ON COLUMN invite_codes.description IS 'Human-readable description of the code purpose (e.g., "Family & Friends Master Code")';
```

**Rationale**:
- `is_master_code` flag distinguishes master codes from regular codes
- `description` helps admin track what each master code is for
- Index optimizes lookups for master codes

#### 2.2 Code Generation Enhancement

**File**: `src/agent/__init__.py`

**Changes to `generate_invite_code` function**:
```python
async def generate_invite_code(
    ctx,
    count: int = 1,
    tier: str = 'free',
    trial_days: int = 7,
    max_uses: Optional[int] = 1,
    is_master_code: bool = False,  # NEW PARAMETER
    description: Optional[str] = None  # NEW PARAMETER
) -> InviteCodeResult:
    """
    Generate invite codes (ADMIN ONLY)

    New Parameters:
        is_master_code: If true, creates unlimited-use permanent code (ignores max_uses)
        description: Human-readable description for the code purpose
    """
    # ... existing validation ...

    # Master code validation
    if is_master_code:
        # Force unlimited uses for master codes
        max_uses = None
        # Default description if not provided
        if description is None:
            description = f"Master Code ({tier.title()} tier)"

        logger.info(f"Admin {deps.telegram_id} creating MASTER CODE: {description}")

    # ... existing code generation logic ...

    # Create code in database with new fields
    await create_invite_code(
        code=code,
        created_by=deps.telegram_id,
        max_uses=max_uses,
        tier=tier,
        trial_days=trial_days,
        is_master_code=is_master_code,  # NEW
        description=description  # NEW
    )
```

**Response Format Enhancement**:
```python
if is_master_code:
    message = f"""✅ **Master Code Created**

🔑 **Code:** `{codes[0]}`
📝 **Description:** {description}

**Details:**
• Type: **Master Code (Unlimited Uses)**
• Tier: {tier.title()}
• Trial: {trial_days} days
• Expires: Never

⚠️ This code can be reused indefinitely. Share only with trusted friends and family."""
else:
    # ... existing single/multiple code message ...
```

#### 2.3 Database Query Enhancement

**File**: `src/db/queries.py`

**Update `create_invite_code` function**:
```python
async def create_invite_code(
    code: str,
    created_by: str,
    max_uses: Optional[int] = None,
    tier: str = 'free',
    trial_days: int = 0,
    expires_at: Optional[datetime] = None,
    is_master_code: bool = False,  # NEW
    description: Optional[str] = None  # NEW
) -> str:
    """Create a new invite code"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO invite_codes
                (code, created_by, max_uses, tier, trial_days, expires_at, is_master_code, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (code, created_by, max_uses, tier, trial_days, expires_at, is_master_code, description)
            )
            result = await cur.fetchone()
            await conn.commit()

            if is_master_code:
                logger.info(f"Created MASTER CODE: {code} - {description}")
            else:
                logger.info(f"Created invite code: {code}")

            return str(result[0])
```

**Update `validate_invite_code` function**:
```python
async def validate_invite_code(code: str) -> Optional[dict]:
    """
    Validate an invite code and return its details if valid
    Returns None if code is invalid, expired, or used up
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, code, max_uses, uses_count, tier, trial_days,
                       expires_at, active, is_master_code, description
                FROM invite_codes
                WHERE code = %s
                """,
                (code,)
            )
            result = await cur.fetchone()

            if not result:
                return None

            # Check if code is active
            if not result['active']:
                logger.warning(f"Invite code {code} is inactive")
                return None

            # Check expiration
            if result['expires_at'] and datetime.now() > result['expires_at']:
                logger.warning(f"Invite code {code} has expired")
                return None

            # Check max uses (SKIP for master codes)
            if not result['is_master_code']:  # NEW LOGIC
                if result['max_uses'] is not None and result['uses_count'] >= result['max_uses']:
                    logger.warning(f"Invite code {code} has reached max uses ({result['max_uses']})")
                    return None
            else:
                logger.info(f"Validating MASTER CODE: {code} (unlimited uses)")

            return dict(result)
```

**Add new query to list master codes**:
```python
async def get_master_codes() -> list:
    """Get all active master codes"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT code, tier, trial_days, description, uses_count, created_at
                FROM invite_codes
                WHERE is_master_code = true AND active = true
                ORDER BY created_at DESC
                """
            )
            return await cur.fetchall()
```

#### 2.4 Usage Tracking (Important!)

**File**: `src/db/queries.py`

**Update `use_invite_code` function** (or create if doesn't exist):
```python
async def use_invite_code(code: str) -> bool:
    """
    Mark an invite code as used (increment use counter)
    Returns True if successful, False if code is invalid or exhausted
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Validate code first
            code_data = await validate_invite_code(code)
            if not code_data:
                return False

            # Increment use counter
            await cur.execute(
                """
                UPDATE invite_codes
                SET uses_count = uses_count + 1
                WHERE code = %s
                RETURNING uses_count, is_master_code, max_uses
                """,
                (code,)
            )
            result = await cur.fetchone()
            await conn.commit()

            if result['is_master_code']:
                logger.info(
                    f"Master code {code} used (total uses: {result['uses_count']}, unlimited)"
                )
            else:
                logger.info(
                    f"Invite code {code} used ({result['uses_count']}/{result['max_uses'] or 'unlimited'})"
                )

            return True
```

#### 2.5 Testing

**File**: `tests/integration/test_master_codes.py` (NEW)

```python
"""Integration tests for master code functionality"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.agent import generate_invite_code, AgentDeps
from src.db.queries import validate_invite_code, use_invite_code
from src.memory.file_manager import MemoryFileManager


@pytest.fixture
def admin_deps():
    """Create AgentDeps for admin user"""
    memory_manager = Mock(spec=MemoryFileManager)
    return AgentDeps(
        telegram_id="7376426503",
        memory_manager=memory_manager,
        user_memory={},
        reminder_manager=None,
        bot_application=None,
    )


class TestMasterCodes:
    """Test suite for master code feature"""

    @pytest.mark.asyncio
    async def test_generate_master_code_as_admin(self, admin_deps):
        """Test that admin can generate master codes"""
        ctx = Mock()
        ctx.deps = admin_deps

        with patch('src.agent.create_invite_code', new_callable=AsyncMock) as mock_create:
            result = await generate_invite_code(
                ctx,
                count=1,
                tier='premium',
                trial_days=0,
                is_master_code=True,
                description="Family & Friends Code"
            )

            assert result.success is True
            assert result.code is not None
            assert "Master Code Created" in result.message
            assert "Unlimited Uses" in result.message

            # Verify create_invite_code was called with correct params
            call_args = mock_create.call_args
            assert call_args.kwargs['is_master_code'] is True
            assert call_args.kwargs['description'] == "Family & Friends Code"
            assert call_args.kwargs['max_uses'] is None  # Unlimited

    @pytest.mark.asyncio
    async def test_master_code_unlimited_uses(self):
        """Test that master codes can be used unlimited times"""
        # This test would use a real database or mock
        # Simulate using the same master code 100 times
        master_code = "family-friends-premium"

        # Mock validation to return master code data
        with patch('src.db.queries.validate_invite_code', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = {
                'code': master_code,
                'is_master_code': True,
                'max_uses': None,
                'uses_count': 99,  # Already used 99 times
                'active': True,
                'tier': 'premium',
                'trial_days': 0,
                'expires_at': None
            }

            # Validate should succeed even after 99 uses
            result = await validate_invite_code(master_code)
            assert result is not None
            assert result['is_master_code'] is True

    @pytest.mark.asyncio
    async def test_regular_code_vs_master_code(self):
        """Test that regular codes still have max_uses limit"""
        # Regular code: should fail after max_uses
        regular_code_data = {
            'code': 'regular-code-123',
            'is_master_code': False,
            'max_uses': 1,
            'uses_count': 1,  # Exhausted
            'active': True,
            'expires_at': None
        }

        # Master code: should work even with high uses_count
        master_code_data = {
            'code': 'master-code-456',
            'is_master_code': True,
            'max_uses': None,
            'uses_count': 100,  # Used 100 times, still valid
            'active': True,
            'expires_at': None
        }

        with patch('src.db.queries.db.connection') as mock_conn:
            # Test regular code (should fail)
            mock_conn.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value.fetchone.return_value = regular_code_data
            result = await validate_invite_code('regular-code-123')
            assert result is None  # Should be invalid (exhausted)

            # Test master code (should succeed)
            mock_conn.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value.fetchone.return_value = master_code_data
            result = await validate_invite_code('master-code-456')
            assert result is not None  # Should be valid
            assert result['is_master_code'] is True

    @pytest.mark.asyncio
    async def test_master_code_default_description(self, admin_deps):
        """Test that master codes get default description if not provided"""
        ctx = Mock()
        ctx.deps = admin_deps

        with patch('src.agent.create_invite_code', new_callable=AsyncMock) as mock_create:
            result = await generate_invite_code(
                ctx,
                count=1,
                tier='premium',
                is_master_code=True
                # No description provided
            )

            # Should have auto-generated description
            call_args = mock_create.call_args
            assert call_args.kwargs['description'] == "Master Code (Premium tier)"
```

**Add tests to existing file**: `tests/integration/test_invite_codes.py`

```python
# Add these test methods to the existing TestInviteCodeGeneration class

@pytest.mark.asyncio
async def test_generate_master_code_forces_unlimited_uses(self, admin_deps):
    """Test that is_master_code=True overrides max_uses parameter"""
    ctx = Mock()
    ctx.deps = admin_deps

    with patch('src.agent.create_invite_code', new_callable=AsyncMock) as mock_create:
        # Try to create master code with max_uses=5 (should be ignored)
        result = await generate_invite_code(
            ctx,
            count=1,
            tier='premium',
            max_uses=5,  # This should be overridden to None
            is_master_code=True
        )

        # Verify max_uses was forced to None (unlimited)
        call_args = mock_create.call_args
        assert call_args.kwargs['max_uses'] is None
```

#### 2.6 User Experience

**How admin generates master code**:

1. **Via natural language** (preferred):
   - "create a master code for friends and family"
   - "generate unlimited premium code"
   - "make reusable code for close friends"

2. **Via explicit parameters**:
   - `generate_invite_code(count=1, tier='premium', is_master_code=True, description="VIP Friends")`

**Example conversation**:
```
User: "create one master-code that i can reuse with close friends and family that is a full access code"

Bot: ✅ **Master Code Created**

🔑 **Code:** `tiger-coral-moon`
📝 **Description:** Full Access Code for Friends & Family

**Details:**
• Type: **Master Code (Unlimited Uses)**
• Tier: Premium
• Trial: 0 days
• Expires: Never

⚠️ This code can be reused indefinitely. Share only with trusted friends and family.
```

**Master code validation flow**:
1. Friend receives code: `tiger-coral-moon`
2. Friend sends `/start` in bot
3. Bot prompts for invite code
4. Friend enters: `tiger-coral-moon`
5. Bot validates (checks `is_master_code=true`, ignores `max_uses`)
6. Increments `uses_count` for tracking
7. Activates friend's account with premium tier
8. Code remains valid for next person

---

## Implementation Sequence

### Step 1: Deploy Current Fix (Immediate)
1. Create PR: `issue-12` → `main`
2. Run tests: `pytest tests/integration/test_invite_codes.py -v`
3. Merge PR
4. Deploy to production
5. Test in production with admin user

**Estimated Time**: 15 minutes

### Step 2: Implement Master Code Feature
1. Create migration `migrations/004_master_code_support.sql`
2. Run migration in dev database
3. Update `src/db/queries.py` (add params, update validation)
4. Update `src/agent/__init__.py` (add params, update messages)
5. Create `tests/integration/test_master_codes.py`
6. Run all tests: `pytest tests/integration/test_*codes.py -v`
7. Manual testing in dev
8. Commit changes
9. Create PR
10. Deploy to production

**Estimated Time**: 45 minutes

### Step 3: Create Master Code for User
1. Deploy to production
2. Admin generates master code:
   ```
   "create a premium master code for friends and family with no trial period"
   ```
3. Bot creates code (e.g., `family-premium-access`)
4. Admin shares code with friends/family
5. Monitor usage via logs

**Estimated Time**: 5 minutes

---

## Testing Strategy

### Unit Tests
- ✅ Admin check with various input types (already exists)
- ✅ Invite code collision retry (already exists)
- 🆕 Master code creation
- 🆕 Master code validation
- 🆕 Master code unlimited uses

### Integration Tests
- ✅ End-to-end invite code generation (already exists)
- 🆕 End-to-end master code generation
- 🆕 Master code reusability (multiple uses)
- 🆕 Regular code vs master code behavior

### Manual Tests
- Deploy fix and test admin can generate regular codes
- Generate master code and share with test user
- Test user redeems master code
- Second test user redeems same master code
- Verify both users activated successfully

---

## Rollback Plan

### If Fix Deployment Fails
1. Revert merge commit on main
2. Investigate issue in dev environment
3. Fix and redeploy

### If Master Code Feature Fails
1. Feature is additive (doesn't break existing functionality)
2. Worst case: admin generates regular codes instead
3. Can disable master code feature by:
   - Setting all `is_master_code=false` in database
   - Removing `is_master_code` parameter from function calls

---

## Success Criteria

### Phase 1 (Fix Deployment)
- ✅ PR merged to main
- ✅ Deployed to production
- ✅ Admin (7376426503) can generate invite codes
- ✅ No type mismatch errors
- ✅ Collision retry works

### Phase 2 (Master Code)
- ✅ Migration applied successfully
- ✅ Admin can generate master codes
- ✅ Master codes have unlimited uses
- ✅ Master codes can be reused by multiple users
- ✅ Regular codes still behave normally
- ✅ All tests pass
- ✅ User has working master code for friends/family

---

## Files Modified

### Phase 1: Fix Deployment (NO NEW CHANGES - already on issue-12 branch)
- `src/utils/auth.py` - Admin check normalization
- `src/agent/__init__.py` - Collision retry logic
- `tests/unit/test_auth.py` - Admin check tests
- `tests/integration/test_invite_codes.py` - Integration tests

### Phase 2: Master Code Feature (NEW CHANGES)
- `migrations/004_master_code_support.sql` - NEW FILE
- `src/db/queries.py` - Add is_master_code, description params
- `src/agent/__init__.py` - Add is_master_code, description params
- `tests/integration/test_master_codes.py` - NEW FILE
- `tests/integration/test_invite_codes.py` - Add master code tests

**Total Files**: 8 files (2 new, 6 modified)

---

## Deployment Commands

### Dev Environment
```bash
# Apply migration
psql -U your_user -d health_agent_dev -f migrations/004_master_code_support.sql

# Run tests
pytest tests/integration/test_invite_codes.py -v
pytest tests/integration/test_master_codes.py -v

# Test manually
python -m src.main
# Then in Telegram: "generate a premium master code for VIP friends"
```

### Production
```bash
# Apply migration
psql -U prod_user -d health_agent_prod -f migrations/004_master_code_support.sql

# Deploy code
git pull origin main
systemctl restart health-agent-bot  # or your deployment method

# Verify
# In Telegram: "generate a premium master code for friends and family"
```

---

## Monitoring

### Logs to Watch
```bash
# Admin check logs
grep "Admin check:" logs/bot.log

# Master code creation
grep "MASTER CODE" logs/bot.log

# Master code validation
grep "Validating MASTER CODE" logs/bot.log

# Usage tracking
grep "Master code .* used" logs/bot.log
```

### Database Queries
```sql
-- Check master codes
SELECT code, description, tier, uses_count, created_at
FROM invite_codes
WHERE is_master_code = true
ORDER BY uses_count DESC;

-- Check recent code usage
SELECT ic.code, ic.is_master_code, ic.uses_count, ic.max_uses,
       COUNT(u.telegram_id) as users_activated
FROM invite_codes ic
LEFT JOIN users u ON u.invite_code_used = ic.code
GROUP BY ic.id
ORDER BY ic.created_at DESC
LIMIT 10;
```

---

## Next Steps

1. **Immediate**: Create PR to merge fix to main
2. **After PR merged**: Implement master code feature
3. **After testing**: Deploy to production
4. **After deployment**: Generate master code for user
5. **Monitor**: Track usage and ensure no issues

---

## Questions for User

Before implementing Phase 2, confirm:

1. ✅ **Tier**: Premium tier for master code? (assumed yes)
2. ✅ **Trial**: No trial period? (assumed 0 days trial)
3. ❓ **Code format**: Use random word format (e.g., `family-premium-access`) or custom code (e.g., `sam-vip-2024`)?
4. ❓ **Multiple master codes**: Create just one, or support multiple master codes for different purposes?
5. ❓ **Deactivation**: Need ability to deactivate master code if compromised?

**Recommendation**: Start with one master code using random word format. Can create more later if needed. Add deactivation support (set `active=false`) in case code is shared too widely.

---

## Risk Assessment

### Low Risk
- Fix deployment (already tested on issue-12 branch)
- Master code creation (additive feature, doesn't modify existing behavior)

### Medium Risk
- Master code validation (changes validation logic, but with fallback)
- Migration (adds columns, but non-breaking)

### Mitigation
- Comprehensive testing before deployment
- Database backup before migration
- Gradual rollout (test in dev first)
- Monitoring after deployment
- Easy rollback plan

---

## Summary

**Phase 1 (URGENT)**: Merge and deploy existing fix so admin can generate codes in production.

**Phase 2**: Add master code feature with:
- Unlimited uses
- Premium tier
- Reusable for friends/family
- Tracked usage
- Clear admin messaging

**Total effort**: ~1 hour (15 min fix deployment + 45 min feature implementation)

**User benefit**: Can immediately generate codes AND have special reusable code for inner circle.
