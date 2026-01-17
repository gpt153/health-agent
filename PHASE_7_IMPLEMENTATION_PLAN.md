# Epic 009 - Phase 7: Integration & Agent Tools - Implementation Plan

**Status**: Ready for Implementation
**Epic**: Ultimate Memory System - Visual Food Memory & Pattern Detection
**Phase**: 7 of 7 (FINAL PHASE)
**Estimated Time**: 8 hours
**Created**: 2026-01-17

---

## 📋 Executive Summary

This is the **final integration phase** of Epic 009, bringing together all components built in Phases 1-6 into user-facing agent tools. This phase transforms 14,000+ lines of infrastructure code into natural, conversational features that enable:

- **Instant meal recognition** from photos (no manual entry)
- **Zero-repetition formula logging** (agent auto-suggests)
- **AI-discovered health insights** (pattern surfacing)
- **Truly personalized coaching** (context-aware responses)

**All dependencies complete:**
- ✅ Phase 1: Visual Reference Foundation (image embeddings)
- ✅ Phase 2: Plate Recognition (calibration data)
- ✅ Phase 3: Food Formulas (formula database)
- ✅ Phase 4: Portion Comparison (comparison logic)
- ✅ Phase 5: Event Timeline (unified events)
- ✅ Phase 6: Pattern Detection (pattern engine)

---

## 🎯 Goals & Success Criteria

### Primary Goals
1. **Create 3 core agent tools** for memory access
2. **Implement hybrid search** (RRF fusion) for <100ms performance
3. **Build pattern surfacing logic** for natural insights
4. **Enhance photo pipeline** with full memory context
5. **Enable user feedback loop** for pattern quality

### Success Criteria
- [ ] Agent can search food images by visual similarity
- [ ] Agent can retrieve and suggest formulas automatically
- [ ] Agent can surface health patterns naturally in conversation
- [ ] RRF hybrid search achieves <100ms latency
- [ ] Pattern notifications sent to users for new discoveries
- [ ] User feedback mechanism functional (helpful/not helpful)
- [ ] Photo analysis uses all memory context (Phases 1-6)
- [ ] All integration tests passing
- [ ] Documentation complete

---

## 📊 Architecture Overview

### Integration Points

```
┌─────────────────────────────────────────────────────────────┐
│                        Agent Layer                           │
│  (PydanticAI Tools - Natural Language Interface)            │
├─────────────────────────────────────────────────────────────┤
│  NEW: memory_tools.py                                        │
│  ├─ search_food_images() → Phase 1                          │
│  ├─ get_food_formula() → Phase 3                            │
│  └─ get_health_patterns() → Phase 6                         │
├─────────────────────────────────────────────────────────────┤
│  NEW: hybrid_search.py (RRF Fusion)                          │
│  ├─ Semantic Search (text embeddings)                       │
│  ├─ Visual Search (CLIP embeddings - Phase 1)               │
│  └─ Structured Search (formula keywords - Phase 3)          │
├─────────────────────────────────────────────────────────────┤
│  ENHANCED: Photo Analysis Pipeline                           │
│  ├─ Visual memory context (Phase 1)                         │
│  ├─ Plate recognition (Phase 2)                             │
│  ├─ Formula matching (Phase 3)                              │
│  └─ Portion comparison (Phase 4)                            │
├─────────────────────────────────────────────────────────────┤
│  NEW: Pattern Surfacing Logic                                │
│  ├─ Relevance scoring                                       │
│  ├─ Context-aware triggers                                  │
│  └─ User notifications                                      │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Message → Agent → memory_tools.py
                           ↓
            ┌──────────────┴──────────────┐
            │                             │
      Visual Search              Hybrid Search (RRF)
      (Phase 1 CLIP)             ┌────┬────┬────┐
            │                    │    │    │    │
            ↓                    ↓    ↓    ↓    ↓
    similar_foods         Semantic Visual Struct
            │                    │    │    │    │
            └────────────────────┴────┴────┴────┘
                           ↓
                    Fused Results
                           ↓
            Agent Response + Pattern Insights
```

---

## 🛠️ Implementation Tasks

### Task 1: Create Agent Tool - `search_food_images()`
**File**: `src/agent/tools/memory_tools.py` (new)
**Dependencies**: Phase 1 (`visual_food_search.py`, `image_embedding.py`)
**Estimated Time**: 1 hour

**Signature**:
```python
async def search_food_images(
    ctx: RunContext[AgentDeps],
    image_path: Optional[str] = None,
    text_description: Optional[str] = None,
    limit: int = 3
) -> MemoryResult
```

**Integration Points**:
- Uses `VisualFoodSearchService.find_similar_foods()`
- Returns `SimilarFoodMatch` objects

**Response Format**:
```
Found 3 similar meals:
1. Banana Protein Shake (95% match) - 2 days ago
   450 kcal | 30g protein
```

---

### Task 2: Create Agent Tool - `get_food_formula()`
**File**: `src/agent/tools/memory_tools.py`
**Dependencies**: Phase 3 (`formula_detection.py`, `formula_tools.py`)
**Estimated Time**: 1 hour

**Signature**:
```python
async def get_food_formula(
    ctx: RunContext[AgentDeps],
    keyword: Optional[str] = None,
    image_path: Optional[str] = None,
    auto_suggest: bool = True
) -> MemoryResult
```

**Auto-Suggestion Logic**:
- Time-based boosting (breakfast/lunch/dinner)
- Frequency-based boosting (times_used > 10)
- Combined confidence scoring

---

### Task 3: Create Agent Tool - `get_health_patterns()`
**File**: `src/agent/tools/memory_tools.py`
**Dependencies**: Phase 6 (`pattern_detection.py`)
**Estimated Time**: 1.5 hours

**Signature**:
```python
async def get_health_patterns(
    ctx: RunContext[AgentDeps],
    query: Optional[str] = None,
    pattern_types: Optional[List[str]] = None,
    min_confidence: float = 0.70,
    min_impact: float = 50.0
) -> MemoryResult
```

**Relevance Scoring**:
- Temporal match (30 points)
- Contextual match (40 points)
- Recency bonus (20 points)
- Impact bonus (10 points)

---

### Task 4: Implement RRF Hybrid Search
**File**: `src/services/hybrid_search.py` (new)
**Dependencies**: Phases 1, 3, 6
**Estimated Time**: 2 hours

**RRF Algorithm**:
```python
RRF_score(item) = Σ(1 / (k + rank_i))
where k=60 (standard), rank_i = rank in result list i
```

**Performance Target**: <100ms total latency
- Semantic search: ~30ms
- Visual search: ~25ms
- Structured search: ~15ms
- Fusion: ~10ms

---

### Task 5: Build Pattern Surfacing Logic
**File**: `src/services/pattern_surfacing.py` (new)
**Dependencies**: Phase 6 (`pattern_detection.py`)
**Estimated Time**: 1.5 hours

**Surfacing Triggers**:
- `user_asks_why` → immediate surfacing
- `symptom_mentioned` → immediate surfacing
- `all_factors_present` → deferred surfacing

**Max Frequency**:
- Temporal correlations: 1/day
- Multifactor patterns: 2/week
- Behavioral sequences: 3/week

---

### Task 6: User Notification System
**File**: `src/services/pattern_notifications.py` (new)
**Dependencies**: Phase 6, Telegram bot
**Estimated Time**: 1 hour

**Notification Criteria**:
- Confidence >= 0.70
- Impact >= 60
- User preferences allow
- Not recently notified about similar pattern

**Notification Format**:
```
🔍 New Health Pattern Discovered!
Pattern: [description]
Confidence: 85%
Impact: High (78/100)
Recommendation: [actionable insight]
[Helpful] [Not Helpful]
```

---

### Task 7: Pattern Feedback Endpoints
**File**: `src/api/pattern_feedback.py` (new)
**Dependencies**: Phase 6
**Estimated Time**: 1 hour

**Database Schema**:
```sql
ALTER TABLE discovered_patterns ADD COLUMN user_feedback JSONB DEFAULT '{
    "helpful_count": 0,
    "not_helpful_count": 0,
    "feedback_history": []
}'::jsonb;
```

**Learning Loop**:
- If helpful_ratio < 0.5 → reduce confidence by 10%
- If helpful_ratio > 0.8 → increase confidence by 5%

---

### Task 8: Enhanced Photo Analysis Pipeline
**File**: `src/services/photo_analysis.py` (update existing)
**Dependencies**: Phases 1, 2, 3, 4
**Estimated Time**: 1.5 hours

**Enhanced Flow**:
```
Photo Upload
    ↓
Visual Memory Search (Phase 1)
    ↓
Plate Recognition (Phase 2)
    ↓
Formula Matching (Phase 3)
    ↓
GPT-4 Vision (with context)
    ↓
Portion Comparison (Phase 4)
    ↓
Final Food Entry
```

**Context Building**:
```python
async def build_analysis_context(
    user_id: str,
    image_path: str
) -> Dict[str, Any]:
    return {
        "reference_foods": await visual_search(...),
        "plate_calibration": await plate_service.detect_plate(...),
        "formula_matches": await formula_service.find_formulas_by_image(...)
    }
```

---

### Task 9: Integration Tests
**File**: `tests/integration/test_phase7_integration.py` (new)
**Estimated Time**: 1.5 hours

**Test Scenarios**:
1. End-to-End Formula Recognition
2. Pattern Surfacing in Conversation
3. Hybrid Search Performance (<100ms)
4. Full Memory Integration

---

## 📦 Deliverables Checklist

### Code Files
- [ ] `src/agent/tools/memory_tools.py` (new)
- [ ] `src/services/hybrid_search.py` (new)
- [ ] `src/services/pattern_surfacing.py` (new)
- [ ] `src/services/pattern_notifications.py` (new)
- [ ] `src/api/pattern_feedback.py` (new)
- [ ] `src/services/photo_analysis.py` (update)

### Database Migrations
- [ ] `migrations/026_pattern_feedback.sql`
- [ ] `migrations/027_notification_preferences.sql`

### Tests
- [ ] `tests/integration/test_phase7_integration.py`

### Documentation
- [ ] `docs/agent_tools_user_guide.md`
- [ ] `docs/api_reference_phase7.md`

---

## 🎬 User Experience Examples

### Example 1: Visual Memory in Action

**User**: [sends photo of protein shake]

**Agent**:
> That looks like your **Banana Protein Shake**! 🥤
>
> I found 3 similar photos from your history:
> - 2 days ago: Same shake (95% match)
>
> **Usual formula:**
> - 30g protein powder, 1 banana, 300ml almond milk
>
> **Nutrition:** 450 kcal | 30g protein
>
> Is this the same? I can log it for you!

**User**: "Yes"

**Agent**: ✅ Logged automatically!

---

### Example 2: Pattern Surfacing

**User**: "I'm feeling really tired this afternoon 😴"

**Agent**:
> I've noticed a pattern in your data:
>
> 🔍 **Pattern:** You tend to feel tired 2-4 hours after eating pasta for lunch, especially on days when you sleep <7 hours.
>
> **Your situation:**
> - Pasta lunch today ✓
> - Sleep: 6.5 hours ✓
>
> **Confidence:** 85% (12 occurrences)
>
> 💡 **Recommendation:** Try lower-carb lunch on low-sleep days.
>
> [Helpful] [Not Helpful]

---

### Example 3: Hybrid Search

**User**: "Do I have a shake recipe saved?"

**Agent**:
> Found 2 matching formulas:
>
> 1. **Banana Protein Shake** (92% match)
>    - Used 15 times | 450 kcal
>
> 2. **Post-Workout Shake** (78% match)
>    - Used 8 times | 380 kcal
>
> Would you like to log one?

---

## ⚡ Performance Requirements

### Latency Targets
- Visual search: <100ms
- Formula retrieval: <50ms
- Pattern retrieval: <50ms
- RRF hybrid search: <100ms
- Photo analysis (full): <3s

### Optimization Strategies
1. Concurrent execution (`asyncio.gather()`)
2. Connection pooling (5-20 connections)
3. Query result caching (90s TTL)
4. HNSW indexing for vectors
5. Prepared statements

---

## 🧪 Testing Strategy

### Unit Tests
- RRF fusion correctness
- Pattern relevance scoring
- Notification filtering

### Integration Tests
- End-to-end workflows
- Multi-phase integration
- Agent conversation flows

### Performance Tests
- Hybrid search latency (<100ms)
- Concurrent tool usage
- Memory consumption

---

## 📝 Implementation Order

**Day 1 (3 hours)**
1. Create `memory_tools.py` with 3 core tools (Tasks 1-3)
2. Write unit tests

**Day 2 (3 hours)**
3. Implement RRF hybrid search (Task 4)
4. Pattern surfacing logic (Task 5)
5. Performance testing

**Day 3 (2 hours)**
6. User notifications (Task 6)
7. Feedback endpoints (Task 7)
8. Integration tests (Task 9)

**Total: 8 hours**

---

## 🚀 Deployment Plan

### Pre-Deployment Checklist
- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] Performance tests meeting targets
- [ ] Database migrations tested
- [ ] Documentation complete

### Deployment Steps
1. Database Migration (026-027)
2. Deploy Code (blue-green)
3. Enable Feature Flags
4. Monitor Performance
5. User Feedback Collection

---

## 📊 Success Metrics

### Technical Metrics
- Search latency: <100ms (p95)
- Pattern surfacing accuracy: >80%
- Formula match accuracy: >85%
- API error rate: <0.1%

### User Metrics
- Formula usage rate: >30% of meals
- Pattern feedback ratio: >60% "helpful"
- Photo recognition success: >75%
- User satisfaction: NPS >50

### Business Metrics
- Time saved per user: ~5 min/day
- User engagement: +20% daily active
- Retention: +15% 30-day

---

## 🎯 Final Notes

This is the **culmination of Epic 009** - all 14,000+ lines of infrastructure from Phases 1-6 come together in this final integration phase.

**Key Success Factors:**
1. **Performance** - Sub-100ms hybrid search is critical
2. **Accuracy** - Formula/pattern matching must be >80% accurate
3. **User Experience** - Insights must feel natural, not intrusive
4. **Feedback Loop** - User feedback improves system over time

**After Phase 7:**
- Users can log meals with **zero manual entry** (just photos)
- Agent proactively surfaces **personalized health insights**
- System **learns and improves** from user feedback

**This transforms the health agent from a logging tool into a true AI health coach.** 🚀

---

**End of Implementation Plan**
