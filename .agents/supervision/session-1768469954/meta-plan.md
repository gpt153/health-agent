# Project Supervision Meta-Plan
**Session**: session-1768469954
**Started**: 2026-01-15 09:39 UTC (10:39 Stockholm time)
**Goal**: Complete memory personalization enhancement (4 phases)

---

## Project Overview

**Context**: Audit revealed response cache bypasses agent, eliminating personalization for ~10% of messages.

**Solution**: 4-phase approach to ensure 100% personalized responses across all interactions.

---

## Phase Structure

### Phase 1: Critical Cache Removal ⚡ (Issue #46)
**Priority**: CRITICAL  
**Status**: Ready to start
**Dependencies**: None
**Estimated**: 30 minutes

**Goal**: Remove response cache to guarantee all messages go through agent with full memory.

**Deliverables**:
- Delete `src/utils/response_cache.py`
- Remove cache logic from `src/bot.py` (lines 718-724)
- Verify all messages trigger agent

**Success Criteria**:
- ✅ Cache file deleted
- ✅ All messages personalized (tested: "Hi", "Thanks", "OK")
- ✅ No [CACHE_HIT] in logs

**Blocks**: Phase 2

---

### Phase 2: Memory Optimization 🚀 (Issue #47)
**Priority**: HIGH
**Status**: Blocked by Phase 1  
**Dependencies**: #46 must complete
**Estimated**: 1-2 hours

**Goal**: Parallelize memory retrieval for 3-5s personalized responses.

**Deliverables**:
- New file: `src/memory/retrieval.py` (parallel loader)
- Refactor `generate_system_prompt()` to accept pre-loaded context
- Update `get_agent_response()` to use parallel retrieval
- Benchmark: <250ms memory operations (P95)

**Success Criteria**:
- ✅ Memory retrieval parallelized
- ✅ <250ms overhead (down from ~400ms)
- ✅ ~150ms faster responses
- ✅ All tests pass

**Can run parallel with**: Phase 3

---

### Phase 3: Habit Extraction System 🎯 (Issue #48)
**Priority**: MEDIUM
**Status**: Blocked by Phase 1
**Dependencies**: #46 must complete  
**Estimated**: 3-4 hours

**Goal**: Automatic pattern learning and habit application.

**User requirement**: "3dl whey100 should auto-calculate to 1.5 portions + 3dl milk"

**Deliverables**:
- Migration: `migrations/016_user_habits.sql`
- New module: `src/memory/habit_extractor.py`
- Integrate habits into system prompt
- Trigger habit detection on food logging

**Success Criteria**:
- ✅ Habits extracted after 3+ repetitions
- ✅ Confidence scoring works
- ✅ Agent auto-applies "3dl whey100" pattern
- ✅ Database schema created

**Can run parallel with**: Phase 2

---

### Phase 4: Enhanced Photo Memory 📸 (Issue #49)
**Priority**: MEDIUM
**Status**: Blocked by Phases 1, 2, 3
**Dependencies**: #46, #47, #48 must complete
**Estimated**: 12-17 hours

**Goal**: Full memory integration for food photos (Mem0 search, photo similarity, habits, history).

**User requirement**: "Agent should recognize similar food photos from past"

**Sub-tasks**:
- **4.1**: Add Mem0 search to photo analysis (1-2h)
- **4.2**: Include recent food history context (2-3h)
- **4.3**: Apply habits to vision AI (3-4h)
- **4.4**: Photo similarity detection with CLIP embeddings (6-8h)

**Deliverables**:
- Migration: `migrations/017_food_photo_embeddings.sql`
- New module: `src/utils/photo_embedding.py`
- Enhanced `analyze_food_photo()` function
- Photo similarity search in `src/db/queries.py`

**Success Criteria**:
- ✅ Vision AI gets Mem0 context
- ✅ Vision AI gets food history
- ✅ Vision AI applies habits
- ✅ Similar photos detected (>85% similarity)
- ✅ User test: "Your usual post-workout shake" recognition

---

## Dependency Graph

```
Issue #46 (Phase 1) - CRITICAL - 30 min
  ↓ BLOCKS
  ├─→ Issue #47 (Phase 2) - HIGH - 1-2h
  │     ↓
  │     └─→ Issue #49 (Phase 4) - MEDIUM - 12-17h
  │
  └─→ Issue #48 (Phase 3) - MEDIUM - 3-4h
        ↓
        └─→ Issue #49 (Phase 4) - MEDIUM - 12-17h

Issue #44: Parent tracking issue (no execution, just status)
```

**Execution Order**:
1. **Start immediately**: #46 (Phase 1)
2. **After #46**: Start #47 AND #48 in parallel
3. **After #47 AND #48**: Start #49 (Phase 4)

**Critical Path**: #46 → #47 → #49 (Total: 14-19.5 hours)

---

## Concurrency Plan

**Max concurrent**: 5 issues (VM limit)

**Wave 1** (Now):
- Issue #46 (Phase 1) - CRITICAL

**Wave 2** (After Wave 1 completes):
- Issue #47 (Phase 2) - parallel execution
- Issue #48 (Phase 3) - parallel execution  

**Wave 3** (After Wave 2 completes):
- Issue #49 (Phase 4) - all 4 sub-tasks

---

## Success Metrics

**Completion Criteria**:
- ✅ All 4 phases complete and merged
- ✅ 100% personalization achieved
- ✅ Response times: 3-5s (competitive)
- ✅ Habit learning functional
- ✅ Photo recognition enhanced

**Quality Gates**:
- All tests pass
- No regressions
- Performance targets met
- User requirements satisfied

---

## Risk Assessment

**Low Risk**:
- Phase 1: Simple deletion (30 min)
- Phase 2: Refactoring existing code (well-understood)

**Medium Risk**:
- Phase 3: New database schema (habits table)
- Phase 4.1-4.3: Integration work (moderate complexity)

**High Risk**:
- Phase 4.4: Photo embeddings (new tech: CLIP, vector DB)

**Mitigation**:
- Phases 1-3 first (lower risk, high value)
- Phase 4.4 last (allows testing earlier wins)
- Can defer 4.4 if time-constrained

---

## Time Estimates

**Best case**: 15 hours (all smooth)
**Expected**: 18-20 hours (some debugging)
**Worst case**: 25 hours (unexpected issues)

**With SCAR parallel execution**: ~12-15 hours wall-clock time

---

**Next**: Spawn SCAR monitors for Phase 1
