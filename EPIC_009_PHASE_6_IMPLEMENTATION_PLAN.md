# Epic 009 - Phase 6: Pattern Detection Engine
## Implementation Plan

**Status:** Ready for Implementation
**Estimated Time:** 20 hours
**Dependencies:** ✅ Phase 5 (Event Timeline Foundation - MERGED via PR #108)
**Created:** 2026-01-17

---

## Executive Summary

This plan details the implementation of an automated pattern detection engine that analyzes the unified health event timeline to discover meaningful correlations, sequences, and cycles in user health data. The engine will run nightly, detecting patterns like food-symptom correlations, multi-factor energy patterns, and behavioral sequences.

**Key Features:**
- Automated pattern mining from unified event timeline
- Statistical significance testing (p-value < 0.05 threshold)
- 5+ pattern detection algorithms (temporal correlations, multi-factor, sequences, cycles, semantic clustering)
- Nightly background job for continuous pattern discovery
- Pattern confidence tracking and evidence accumulation

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Pattern Detection Engine                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐         ┌─────────────────────┐      │
│  │  Pattern Mining  │────────▶│ Statistical Tests   │      │
│  │  Algorithms      │         │ (Chi-square, etc.)  │      │
│  └────────┬─────────┘         └──────────┬──────────┘      │
│           │                               │                 │
│           ▼                               ▼                 │
│  ┌──────────────────┐         ┌─────────────────────┐      │
│  │  Confidence      │────────▶│ Evidence Tracking   │      │
│  │  Scoring         │         │                     │      │
│  └──────────────────┘         └─────────────────────┘      │
│                                                              │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
            ┌─────────────────────────┐
            │  discovered_patterns    │
            │  (Database Table)       │
            └─────────────────────────┘
                        │
                        ▼
            ┌─────────────────────────┐
            │  Nightly Background Job │
            │  (3 AM user local time) │
            └─────────────────────────┘
```

---

## Phase Breakdown

### Phase 6.1: Database Schema (2 hours)

**Goal:** Create `discovered_patterns` table with proper indexing

**Tasks:**
1. Create migration file `migrations/025_discovered_patterns.sql`
2. Define table schema with JSONB pattern rules
3. Add performance indexes for user queries
4. Add GIN index for pattern_rule JSONB queries
5. Document metadata schema examples

**Database Schema:**
```sql
CREATE TABLE discovered_patterns (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    pattern_type VARCHAR(50) NOT NULL,
    pattern_rule JSONB NOT NULL,
    confidence DECIMAL(3,2) NOT NULL,
    occurrences INTEGER DEFAULT 0,
    impact_score DECIMAL(4,2),
    evidence JSONB,
    actionable_insight TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes
CREATE INDEX idx_patterns_user_confidence
    ON discovered_patterns(user_id, confidence DESC);

CREATE INDEX idx_patterns_user_impact
    ON discovered_patterns(user_id, impact_score DESC);

CREATE INDEX idx_patterns_rule
    ON discovered_patterns USING GIN (pattern_rule);

-- Compound index for pattern deduplication
CREATE UNIQUE INDEX idx_patterns_unique_rule
    ON discovered_patterns(user_id, pattern_type, md5(pattern_rule::text));
```

**Example Pattern Rules:**
```json
{
  "type": "temporal_correlation",
  "trigger": {"event_type": "meal", "metadata.meal_type": "lunch", "metadata.contains_pasta": true},
  "outcome": {"event_type": "symptom", "metadata.symptom": "tiredness"},
  "time_window": {"min_hours": 2, "max_hours": 4},
  "correlation_strength": 0.78
}
```

**Deliverable:**
- `migrations/025_discovered_patterns.sql` (tested and ready to apply)

**Success Criteria:**
- Migration runs without errors
- Indexes created successfully
- Can insert and query pattern records

---

### Phase 6.2: Statistical Analysis Utilities (3 hours)

**Goal:** Build core statistical functions for significance testing

**Tasks:**
1. Create `src/services/statistical_analysis.py`
2. Implement chi-square test for categorical correlations
3. Implement Pearson correlation for continuous variables
4. Add p-value calculation functions
5. Create confidence interval calculations
6. Add unit tests for statistical functions

**Key Functions:**
```python
def chi_square_test(observed: List[List[int]]) -> Tuple[float, float]:
    """Calculate chi-square statistic and p-value"""

def pearson_correlation(x: List[float], y: List[float]) -> Tuple[float, float]:
    """Calculate Pearson r and p-value"""

def calculate_confidence_interval(
    successes: int,
    total: int,
    confidence_level: float = 0.95
) -> Tuple[float, float]:
    """Calculate binomial confidence interval"""

def is_statistically_significant(p_value: float, alpha: float = 0.05) -> bool:
    """Check if p-value meets significance threshold"""
```

**Dependencies:**
- Add `scipy>=1.11.0` to requirements.txt for statistical functions
- Add `numpy>=1.24.0` for numerical operations

**Deliverable:**
- `src/services/statistical_analysis.py` with comprehensive docstrings
- `tests/unit/test_statistical_analysis.py` with 90%+ coverage

**Success Criteria:**
- All statistical tests return correct p-values (verified against known examples)
- Edge cases handled (empty data, single values, etc.)
- Unit tests pass

---

### Phase 6.3: Pattern Detection Algorithms (6 hours)

**Goal:** Implement 5+ pattern detection algorithms

**Tasks:**
1. Create `src/services/pattern_detection.py`
2. Implement temporal correlation detector (food → symptom)
3. Implement multi-factor pattern analyzer (2-4 variables)
4. Implement temporal sequence detector (behavioral chains)
5. Implement cycle-based pattern finder (weekly, monthly)
6. Implement semantic similarity clustering (pgvector)
7. Add pattern deduplication logic

**Pattern Detection Algorithms:**

#### Algorithm 1: Temporal Correlation Detection
```python
async def detect_temporal_correlations(
    user_id: str,
    start_date: datetime,
    end_date: datetime,
    trigger_event_type: str,
    outcome_event_type: str,
    time_window_hours: Tuple[int, int] = (1, 48)
) -> List[TemporalPattern]:
    """
    Detect correlations between trigger events and outcome events
    within a specific time window.

    Example: Pasta at lunch → Tiredness 2-4 hours later

    Returns patterns with p-value < 0.05
    """
```

#### Algorithm 2: Multi-Factor Pattern Analyzer
```python
async def detect_multifactor_patterns(
    user_id: str,
    start_date: datetime,
    end_date: datetime,
    factors: List[EventFilter],
    outcome: EventFilter
) -> List[MultifactorPattern]:
    """
    Analyze combinations of 2-4 variables for correlation with outcome.

    Example: Poor sleep + pasta + high stress → Energy crash

    Uses combinatorial analysis and statistical significance testing.
    """
```

#### Algorithm 3: Temporal Sequence Detection
```python
async def detect_behavioral_sequences(
    user_id: str,
    start_date: datetime,
    end_date: datetime,
    min_sequence_length: int = 2,
    max_sequence_length: int = 5
) -> List[SequencePattern]:
    """
    Find recurring sequences of events (behavioral chains).

    Example: Evening walk → Good sleep → High energy next day

    Uses sequence mining algorithms (e.g., PrefixSpan-like approach).
    """
```

#### Algorithm 4: Cycle-Based Pattern Finder
```python
async def detect_cyclical_patterns(
    user_id: str,
    start_date: datetime,
    end_date: datetime,
    cycle_types: List[str] = ["weekly", "monthly", "period"]
) -> List[CyclicalPattern]:
    """
    Find patterns that repeat on cycles (weekly, monthly, menstrual cycle).

    Examples:
    - Weekend vs weekday energy levels
    - Period week symptom patterns
    - Tuesday afternoon cravings

    Uses time-series analysis and autocorrelation.
    """
```

#### Algorithm 5: Semantic Similarity Clustering
```python
async def cluster_similar_patterns(
    user_id: str,
    patterns: List[Pattern]
) -> List[PatternCluster]:
    """
    Group semantically similar patterns using pgvector embeddings.

    Example:
    - "Pasta → tiredness" and "Rice → tiredness" → "Carbs → tiredness"

    Uses pgvector cosine similarity on pattern text embeddings.
    """
```

**Deliverable:**
- `src/services/pattern_detection.py` with all 5 algorithms
- Comprehensive docstrings and type hints
- Pattern deduplication logic

**Success Criteria:**
- Each algorithm can detect at least 1 pattern type
- Statistical significance enforced (p < 0.05)
- Algorithms complete in reasonable time (<5 min for 1000 events)

---

### Phase 6.4: Pattern Impact Scoring (2 hours)

**Goal:** Calculate impact scores for discovered patterns

**Tasks:**
1. Create impact scoring function in `pattern_detection.py`
2. Implement severity-based scoring (symptom impact)
3. Implement frequency-based scoring (pattern recurrence)
4. Add confidence weighting to impact scores
5. Generate actionable insights from patterns

**Impact Scoring Formula:**
```python
def calculate_impact_score(pattern: Pattern) -> float:
    """
    Calculate impact score (0-100) based on:
    - Severity: How significant is the outcome? (0-10)
    - Frequency: How often does pattern occur? (occurrences/days)
    - Confidence: Statistical confidence (p-value → confidence score)
    - Actionability: Can user change behavior? (0-10)

    Formula:
    impact_score = (severity * 20) + (frequency * 15) + (confidence * 30) + (actionability * 35)
    """
```

**Example Impact Scores:**
- High: 85/100 - "Pasta at lunch → Severe tiredness 2-4h later (occurs 80% of time)"
- Medium: 62/100 - "Poor sleep → Lower energy next day (occurs 65% of time)"
- Low: 38/100 - "Weekend mornings → Slightly later breakfast (occurs 50% of time)"

**Deliverable:**
- `calculate_impact_score()` function
- `generate_actionable_insight()` function

**Success Criteria:**
- Impact scores correlate with actual pattern importance
- Actionable insights are clear and specific

---

### Phase 6.5: Pattern Confidence Updates (2 hours)

**Goal:** Update existing pattern confidence based on new evidence

**Tasks:**
1. Create `update_pattern_confidence()` function
2. Implement Bayesian confidence updates
3. Add evidence accumulation tracking
4. Handle pattern invalidation (confidence drops below threshold)
5. Archive invalidated patterns (soft delete)

**Confidence Update Logic:**
```python
async def update_pattern_confidence(
    pattern_id: int,
    new_evidence: Evidence
) -> UpdatedPattern:
    """
    Update pattern confidence using Bayesian update formula.

    - Positive evidence (pattern holds): Increases confidence
    - Negative evidence (pattern fails): Decreases confidence
    - Neutral evidence (ambiguous): No change

    If confidence drops below 0.50, archive pattern.
    """
```

**Evidence Tracking:**
```json
{
  "evidence": [
    {
      "timestamp": "2026-01-15T14:30:00Z",
      "type": "positive",
      "context": "Pasta lunch at 12:00 → Tiredness at 14:30 (matched pattern)"
    },
    {
      "timestamp": "2026-01-16T14:00:00Z",
      "type": "negative",
      "context": "Pasta lunch at 12:00 → No tiredness observed"
    }
  ],
  "positive_count": 12,
  "negative_count": 3,
  "neutral_count": 1
}
```

**Deliverable:**
- `update_pattern_confidence()` function
- Pattern archival logic

**Success Criteria:**
- Confidence scores adjust appropriately with new evidence
- Invalidated patterns are archived, not deleted

---

### Phase 6.6: Nightly Background Job (3 hours)

**Goal:** Schedule nightly pattern mining job

**Tasks:**
1. Create `src/scheduler/pattern_mining.py`
2. Implement nightly job scheduler (3 AM user local time)
3. Add job that processes last 90 days of events
4. Implement pattern discovery workflow
5. Implement pattern confidence update workflow
6. Add job status logging and error handling
7. Integrate with existing ReminderManager scheduler

**Nightly Job Workflow:**
```python
async def run_nightly_pattern_mining(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Nightly pattern mining job (runs at 3 AM user local time).

    Workflow:
    1. Get all active users
    2. For each user:
       a. Fetch health_events from last 90 days
       b. Run all 5 pattern detection algorithms
       c. Save new patterns to discovered_patterns table
       d. Update confidence of existing patterns
       e. Archive patterns that no longer hold
    3. Log summary statistics (patterns discovered, updated, archived)
    """
```

**Scheduler Integration:**
```python
# In src/scheduler/pattern_mining.py
class PatternMiningScheduler:
    def __init__(self, application: Application):
        self.application = application
        self.job_queue = application.job_queue

    async def schedule_pattern_mining(self) -> None:
        """Schedule daily pattern mining at 3 AM"""
        for user in await get_all_active_users():
            user_timezone = user.get("timezone", "UTC")
            tz = ZoneInfo(user_timezone)
            scheduled_time = time(hour=3, minute=0, tzinfo=tz)

            self.job_queue.run_daily(
                callback=run_nightly_pattern_mining,
                time=scheduled_time,
                data={"user_id": user["telegram_id"]},
                name=f"pattern_mining_{user['telegram_id']}"
            )
```

**Deliverable:**
- `src/scheduler/pattern_mining.py`
- Integration with main application startup

**Success Criteria:**
- Job runs at 3 AM user local time
- All users processed nightly
- Job completes in <5 minutes per user (for 1000 events)
- Errors logged and don't crash job

---

### Phase 6.7: Unit Tests (2 hours)

**Goal:** Achieve 90%+ test coverage on pattern detection service

**Tasks:**
1. Create `tests/unit/test_pattern_detection.py`
2. Test each pattern detection algorithm independently
3. Test statistical significance enforcement
4. Test pattern deduplication
5. Test impact scoring
6. Test confidence updates
7. Add edge case tests (empty data, single event, etc.)

**Test Coverage Targets:**
- `statistical_analysis.py`: 95%+ coverage
- `pattern_detection.py`: 90%+ coverage
- `pattern_mining.py`: 85%+ coverage

**Key Test Cases:**
```python
class TestTemporalCorrelation:
    async def test_detects_food_symptom_correlation(self):
        """Test that pasta → tiredness is detected"""

    async def test_enforces_statistical_significance(self):
        """Test that p >= 0.05 patterns are rejected"""

    async def test_handles_empty_events(self):
        """Test graceful handling of users with no events"""

class TestMultifactorPatterns:
    async def test_detects_three_factor_pattern(self):
        """Test sleep + food + stress → outcome detection"""

    async def test_deduplicates_similar_patterns(self):
        """Test that duplicate patterns are merged"""
```

**Deliverable:**
- `tests/unit/test_pattern_detection.py` with comprehensive tests
- `tests/unit/test_statistical_analysis.py` with 95%+ coverage

**Success Criteria:**
- All tests pass
- Code coverage meets targets
- Edge cases handled gracefully

---

### Phase 6.8: Integration Tests (2 hours)

**Goal:** Test end-to-end pattern mining workflow

**Tasks:**
1. Create `tests/integration/test_pattern_mining.py`
2. Test full nightly job workflow
3. Test pattern discovery from real event data
4. Test pattern confidence updates over time
5. Test pattern archival workflow
6. Performance test: 1000 events in <5 minutes

**Integration Test Scenarios:**

**Scenario 1: Discover New Pattern**
```python
async def test_discover_temporal_correlation():
    """
    Given: User has 30 days of health events
    When: Nightly job runs pattern mining
    Then: Food-symptom correlation is discovered
    And: Pattern has p-value < 0.05
    And: Pattern has actionable insight
    """
```

**Scenario 2: Update Existing Pattern**
```python
async def test_update_pattern_confidence():
    """
    Given: Pattern exists with 0.75 confidence
    When: New evidence supports pattern (5 more occurrences)
    Then: Confidence increases to ~0.82
    And: Evidence is tracked in JSONB
    """
```

**Scenario 3: Archive Invalid Pattern**
```python
async def test_archive_invalidated_pattern():
    """
    Given: Pattern exists with 0.65 confidence
    When: New evidence contradicts pattern (10 failures)
    Then: Confidence drops below 0.50
    And: Pattern is archived (not deleted)
    """
```

**Scenario 4: Performance Test**
```python
async def test_pattern_mining_performance():
    """
    Given: User has 1000 health events (90 days)
    When: Pattern mining runs
    Then: Completes in <5 minutes
    And: Discovers at least 3 patterns
    """
```

**Deliverable:**
- `tests/integration/test_pattern_mining.py` with 4+ scenarios
- Performance benchmark results

**Success Criteria:**
- All integration tests pass
- Performance target met (<5 min for 1000 events)
- End-to-end workflow validated

---

## Implementation Sequence

**Week 1 (12 hours):**
1. Day 1-2: Phase 6.1 + 6.2 (Database + Statistics) - 5 hours
2. Day 3-4: Phase 6.3 Part 1 (First 3 algorithms) - 4 hours
3. Day 5: Phase 6.3 Part 2 (Remaining algorithms) - 3 hours

**Week 2 (8 hours):**
4. Day 1: Phase 6.4 + 6.5 (Impact Scoring + Confidence) - 4 hours
5. Day 2: Phase 6.6 (Background Job) - 3 hours
6. Day 3: Phase 6.7 + 6.8 (Testing) - 4 hours

**Total: 20 hours**

---

## Dependencies

### External Libraries
```txt
# Add to requirements.txt
scipy>=1.11.0           # Statistical tests (chi-square, Pearson)
numpy>=1.24.0           # Numerical operations
```

### Internal Dependencies
- ✅ `health_events` table (Phase 5 - MERGED)
- ✅ `src/services/health_events.py` (Phase 5 - MERGED)
- ✅ `src/scheduler/reminder_manager.py` (existing scheduler framework)
- ✅ pgvector extension (for semantic clustering)

---

## Success Criteria (Epic-Level)

1. ✅ `discovered_patterns` table created with proper indexes
2. ✅ Pattern detection service detects at least 5 pattern types
3. ✅ Statistical significance testing implemented (p < 0.05 threshold)
4. ✅ Nightly background job scheduled and functional
5. ✅ Pattern confidence updates based on new evidence
6. ✅ Unit tests: 90%+ coverage on pattern_detection.py
7. ✅ Integration tests: End-to-end pattern mining workflow
8. ✅ Performance: Pattern mining completes in <5 minutes for 1000 events

---

## Risk Mitigation

**Risk 1: Statistical Tests Too Slow**
- *Mitigation:* Use scipy optimized implementations, cache intermediate results

**Risk 2: Too Many False Positive Patterns**
- *Mitigation:* Strict p-value threshold (0.05), require minimum occurrences (n≥10)

**Risk 3: Nightly Job Overloads Database**
- *Mitigation:* Process users in batches, use connection pooling, add query timeouts

**Risk 4: Patterns Not Actionable**
- *Mitigation:* Human-review top patterns, refine insight generation algorithm

**Risk 5: pgvector Semantic Clustering Fails**
- *Mitigation:* Make semantic clustering optional (nice-to-have), core algorithms don't depend on it

---

## Post-Implementation

**After Phase 6 completes:**
1. Monitor pattern discovery rates (how many patterns per user?)
2. Evaluate pattern quality (false positive rate)
3. Gather user feedback on actionable insights
4. Tune statistical thresholds if needed
5. Prepare for Phase 7: Integration with chat interface

**Metrics to Track:**
- Patterns discovered per user (target: 5-10)
- Pattern confidence distribution (target: 70% above 0.70 confidence)
- Nightly job runtime (target: <5 min per user)
- Statistical significance (target: 100% of patterns have p < 0.05)

---

## Files to Create/Modify

### New Files
1. `migrations/025_discovered_patterns.sql` - Database schema
2. `src/services/statistical_analysis.py` - Statistical utilities
3. `src/services/pattern_detection.py` - Pattern detection algorithms
4. `src/scheduler/pattern_mining.py` - Nightly job scheduler
5. `tests/unit/test_statistical_analysis.py` - Statistical tests
6. `tests/unit/test_pattern_detection.py` - Algorithm tests
7. `tests/integration/test_pattern_mining.py` - E2E tests

### Modified Files
1. `requirements.txt` - Add scipy, numpy
2. `src/main.py` - Initialize pattern mining scheduler on startup

**Total Files:** 7 new, 2 modified

---

## Example Pattern Output

**Discovered Pattern Example:**
```json
{
  "id": 123,
  "user_id": "123456789",
  "pattern_type": "temporal_correlation",
  "pattern_rule": {
    "trigger": {
      "event_type": "meal",
      "metadata.meal_type": "lunch",
      "metadata.foods_contain": "pasta"
    },
    "outcome": {
      "event_type": "symptom",
      "metadata.symptom": "tiredness",
      "metadata.severity": ">=6"
    },
    "time_window": {"min_hours": 2, "max_hours": 4},
    "correlation_strength": 0.78,
    "p_value": 0.003
  },
  "confidence": 0.85,
  "occurrences": 18,
  "impact_score": 78.5,
  "evidence": {
    "positive_count": 18,
    "negative_count": 3,
    "first_observed": "2025-12-20T12:30:00Z",
    "last_observed": "2026-01-15T12:45:00Z"
  },
  "actionable_insight": "You tend to feel tired 2-4 hours after eating pasta for lunch. Consider choosing a lower-carb lunch option on days when you need sustained afternoon energy.",
  "created_at": "2026-01-10T03:00:00Z",
  "updated_at": "2026-01-17T03:00:00Z"
}
```

---

## Next Steps After Plan Approval

1. Create feature branch: `feature/epic-009-phase-6-pattern-detection`
2. Start with Phase 6.1 (database schema)
3. Proceed sequentially through phases
4. Run tests after each phase
5. Create PR when all phases complete

---

**Ready to begin implementation upon approval! 🚀**
