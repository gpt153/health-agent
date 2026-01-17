# Epic 009 - Phase 2: Plate Recognition & Calibration - Implementation Plan

**Epic:** Ultimate Memory System - Visual Food Memory & Pattern Detection
**Phase:** 2 of 7
**Priority:** High
**Estimated Time:** 12 hours
**Status:** Planning Complete - Ready for Implementation

---

## 🎯 Objective

Build a plate/container recognition and calibration system that:
1. **Detects plates** from food images using image segmentation
2. **Generates CLIP embeddings** for plates to enable matching
3. **Matches plates** across user's food history using vector similarity
4. **Calibrates portion sizes** based on known plate dimensions
5. **Improves portion estimation accuracy** for future food logs

This enables the system to learn users' common plates/bowls and use them as reference objects for more accurate portion estimation.

---

## 📋 Context from Phase 1

### ✅ Phase 1 Achievements (Foundation)
- **CLIP embeddings** infrastructure exists (512-dimensional vectors)
- **pgvector** with HNSW indexing operational
- **ImageEmbeddingService** can generate embeddings for any image
- **VisualFoodSearchService** provides similarity search capabilities
- **food_image_references** table stores full food photo embeddings
- **Performance targets** met: <100ms search, <2s embedding generation

### 🔗 What We're Building On
- Leverage existing `ImageEmbeddingService` for plate embeddings
- Reuse pgvector infrastructure for plate matching
- Follow Phase 1 architecture patterns (services, async, caching)
- Maintain <500ms total processing time requirement

---

## 🏗️ Architecture Design

### Database Schema

#### `recognized_plates` Table
```sql
CREATE TABLE recognized_plates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,

    -- Plate identification
    plate_name VARCHAR(200),  -- Auto-generated or user-provided (e.g., "Large white dinner plate")
    embedding vector(512) NOT NULL,  -- CLIP embedding of plate

    -- Physical characteristics
    estimated_diameter_cm FLOAT,  -- Estimated diameter in centimeters
    estimated_capacity_ml FLOAT,   -- Estimated capacity for bowls/cups
    plate_type VARCHAR(50),         -- "plate", "bowl", "cup", "container"
    color VARCHAR(100),              -- Dominant color
    shape VARCHAR(50),               -- "round", "square", "oval", "rectangular"

    -- Usage tracking
    times_recognized INTEGER DEFAULT 1,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Calibration status
    is_calibrated BOOLEAN DEFAULT FALSE,
    calibration_confidence FLOAT,  -- 0.0 to 1.0
    calibration_method VARCHAR(50), -- "reference_portion", "user_input", "auto_inferred"

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- HNSW index for fast plate matching
CREATE INDEX idx_recognized_plates_embedding_hnsw
ON recognized_plates
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Standard indexes
CREATE INDEX idx_recognized_plates_user ON recognized_plates(user_id);
CREATE INDEX idx_recognized_plates_type ON recognized_plates(plate_type);
CREATE INDEX idx_recognized_plates_calibrated ON recognized_plates(is_calibrated);
CREATE INDEX idx_recognized_plates_user_times ON recognized_plates(user_id, times_recognized DESC);
```

#### Link Table: `food_entry_plates`
```sql
CREATE TABLE food_entry_plates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    food_entry_id UUID NOT NULL REFERENCES food_entries(id) ON DELETE CASCADE,
    recognized_plate_id UUID NOT NULL REFERENCES recognized_plates(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,

    -- Detection metadata
    confidence_score FLOAT NOT NULL,  -- Similarity score (0.0 to 1.0)
    detection_method VARCHAR(50),      -- "auto_detected", "user_confirmed"

    -- Spatial information
    plate_region JSONB,  -- Bounding box or segmentation mask

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_food_entry_plate UNIQUE(food_entry_id, recognized_plate_id)
);

CREATE INDEX idx_food_entry_plates_entry ON food_entry_plates(food_entry_id);
CREATE INDEX idx_food_entry_plates_plate ON food_entry_plates(recognized_plate_id);
CREATE INDEX idx_food_entry_plates_user ON food_entry_plates(user_id);
```

#### Functions
```sql
-- Find similar plates for matching
CREATE OR REPLACE FUNCTION find_similar_plates(
    p_user_id TEXT,
    p_embedding vector(512),
    p_limit INTEGER DEFAULT 5,
    p_distance_threshold FLOAT DEFAULT 0.2
) RETURNS TABLE (
    plate_id UUID,
    plate_name VARCHAR(200),
    similarity_score FLOAT,
    times_recognized INTEGER,
    is_calibrated BOOLEAN
);

-- Update plate usage statistics
CREATE OR REPLACE FUNCTION update_plate_usage(
    p_plate_id UUID
) RETURNS VOID;

-- Get plate calibration data
CREATE OR REPLACE FUNCTION get_plate_calibration_data(
    p_user_id TEXT,
    p_plate_id UUID
) RETURNS TABLE (
    food_entry_id UUID,
    portion_size_grams FLOAT,
    portion_confidence FLOAT
);
```

---

## 🛠️ Implementation Components

### 1. Migration: `022_recognized_plates.sql`

**File:** `migrations/022_recognized_plates.sql`

**Contents:**
- Create `recognized_plates` table with full schema
- Create `food_entry_plates` link table
- Create HNSW index for plate embeddings
- Create helper functions (find_similar_plates, update_plate_usage)
- Add comments and documentation

**Dependencies:**
- Requires pgvector extension (already installed from Phase 1)
- Builds on existing `food_entries` and `users` tables

---

### 2. Core Service: `src/services/plate_recognition.py`

**Class:** `PlateRecognitionService`

#### Key Methods

##### Plate Detection
```python
async def detect_plate_from_image(
    self,
    image_path: str | Path,
    user_id: str
) -> Optional[DetectedPlate]:
    """
    Detect and extract plate from food image

    Steps:
    1. Analyze image for plate/container regions
    2. Crop plate region (if detectable)
    3. Generate CLIP embedding for plate
    4. Check for existing matches in user's plate database
    5. Return detected plate with metadata

    Returns:
        DetectedPlate or None if no plate detected
    """
```

##### Plate Matching
```python
async def match_plate(
    self,
    plate_embedding: list[float],
    user_id: str,
    threshold: float = 0.85
) -> Optional[RecognizedPlate]:
    """
    Match plate embedding against user's recognized plates

    Uses pgvector similarity search with high threshold (0.85)
    to find exact plate matches.

    Returns:
        RecognizedPlate if match found, None otherwise
    """
```

##### Plate Registration
```python
async def register_new_plate(
    self,
    user_id: str,
    embedding: list[float],
    metadata: PlateMetadata
) -> RecognizedPlate:
    """
    Register a new plate in the user's database

    Creates a new entry in recognized_plates table
    with auto-generated name and initial metadata.
    """
```

##### Size Calibration
```python
async def calibrate_plate_size(
    self,
    plate_id: str,
    reference_portion_grams: float,
    visual_fill_percentage: float,
    confidence: float = 0.8
) -> CalibrationResult:
    """
    Calibrate plate size from a reference portion

    Method:
    1. User provides accurate portion weight (e.g., 170g)
    2. Estimate visual fill percentage (20%, 50%, 100%)
    3. Calculate total capacity: total = portion / fill_percentage
    4. Update plate dimensions in database
    5. Mark as calibrated with confidence score

    Example:
        170g fills 50% of bowl → total capacity = 340g
    """
```

##### Plate-Based Portion Estimation
```python
async def estimate_portion_from_plate(
    self,
    plate_id: str,
    visual_fill_percentage: float
) -> PortionEstimate:
    """
    Estimate portion size based on calibrated plate

    If plate is calibrated, use its dimensions to estimate
    portion size more accurately than vision AI alone.

    Returns:
        PortionEstimate with size in grams and confidence
    """
```

---

### 3. Data Models

**File:** `src/models/plate.py`

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class PlateMetadata(BaseModel):
    """Metadata extracted from plate detection"""
    plate_type: str = Field(..., description="plate, bowl, cup, container")
    color: Optional[str] = None
    shape: Optional[str] = None  # round, square, oval, rectangular
    estimated_diameter_cm: Optional[float] = None
    estimated_capacity_ml: Optional[float] = None

class DetectedPlate(BaseModel):
    """Plate detected from an image"""
    embedding: list[float]
    metadata: PlateMetadata
    confidence: float = Field(..., ge=0.0, le=1.0)
    region: Optional[dict] = None  # Bounding box coordinates

class RecognizedPlate(BaseModel):
    """Plate from database with full history"""
    id: str
    user_id: str
    plate_name: str
    embedding: list[float]
    metadata: PlateMetadata
    times_recognized: int
    is_calibrated: bool
    calibration_confidence: Optional[float] = None
    estimated_diameter_cm: Optional[float] = None
    estimated_capacity_ml: Optional[float] = None
    first_seen_at: datetime
    last_seen_at: datetime

class CalibrationResult(BaseModel):
    """Result of plate calibration"""
    plate_id: str
    calibration_method: str
    estimated_capacity_ml: Optional[float] = None
    estimated_diameter_cm: Optional[float] = None
    confidence: float
    success: bool
    message: str

class PortionEstimate(BaseModel):
    """Portion size estimate based on plate"""
    estimated_grams: float
    confidence: float
    method: str  # "calibrated_plate", "visual_estimation"
    plate_id: Optional[str] = None
```

---

### 4. Calibration Utilities

**File:** `src/utils/plate_calibration.py`

#### Calibration Strategies

##### Strategy 1: Reference Portion Calibration
```python
def calibrate_from_portion(
    portion_grams: float,
    fill_percentage: float
) -> float:
    """
    Calculate total capacity from known portion

    Example:
        170g fills 50% → capacity = 340g
    """
    return portion_grams / fill_percentage
```

##### Strategy 2: Visual Geometry Estimation
```python
def estimate_diameter_from_image(
    plate_region: dict,
    reference_objects: list
) -> Optional[float]:
    """
    Estimate plate diameter using visual cues

    Uses common reference objects (utensils, food items)
    to estimate real-world size.
    """
```

##### Strategy 3: User Input Calibration
```python
async def calibrate_from_user_input(
    plate_id: str,
    user_provided_size: float,
    size_type: str  # "diameter_cm" or "capacity_ml"
) -> CalibrationResult:
    """
    Calibrate plate from explicit user input

    User tells us: "This bowl is 20cm diameter"
    """
```

---

### 5. Integration with Food Logging Pipeline

**File:** `src/bot.py` (modifications)

#### Enhanced Food Photo Handler

```python
async def handle_food_photo_with_plate_detection(
    user_id: str,
    photo_path: str,
    caption: Optional[str] = None
):
    """
    Enhanced food photo handler with plate detection

    Workflow:
    1. Vision AI analyzes food (existing Phase 1)
    2. Generate embedding for full image (existing Phase 1)
    3. **NEW:** Detect plate from image
    4. **NEW:** Match plate against user's recognized plates
    5. **NEW:** If new plate, register it
    6. **NEW:** Link food entry to detected plate
    7. **NEW:** Use plate dimensions for portion refinement (if calibrated)
    8. Save food entry with enhanced metadata
    """

    # Existing Phase 1 flow
    vision_result = await analyze_food_photo(photo_path, caption)
    food_entry = create_food_entry(vision_result)

    # NEW Phase 2 integration
    plate_service = get_plate_recognition_service()

    # Detect plate in background (non-blocking)
    detected_plate = await plate_service.detect_plate_from_image(
        photo_path, user_id
    )

    if detected_plate:
        # Match or register plate
        matched_plate = await plate_service.match_plate(
            detected_plate.embedding,
            user_id
        )

        if not matched_plate:
            matched_plate = await plate_service.register_new_plate(
                user_id,
                detected_plate.embedding,
                detected_plate.metadata
            )

        # Link food entry to plate
        await link_food_entry_to_plate(
            food_entry.id,
            matched_plate.id,
            detected_plate.confidence
        )

        # Refine portion estimate if plate is calibrated
        if matched_plate.is_calibrated:
            refined_portions = await refine_portions_with_plate(
                food_entry,
                matched_plate
            )
            food_entry = update_portions(food_entry, refined_portions)

    # Save enhanced entry
    await save_food_entry(food_entry)
```

---

## 🧪 Testing Strategy

### Unit Tests

**File:** `tests/unit/test_plate_recognition.py`

**Coverage:**
- ✅ Plate detection from images
- ✅ CLIP embedding generation for plates
- ✅ Plate matching logic (threshold testing)
- ✅ New plate registration
- ✅ Calibration calculations
- ✅ Portion estimation from calibrated plates
- ✅ Error handling (no plate detected, invalid inputs)
- ✅ Edge cases (multiple plates, partial views)

**Test Count Target:** ~20 unit tests

---

### Integration Tests

**File:** `tests/integration/test_plate_recognition_integration.py`

**Coverage:**
- ✅ Full workflow: detect → match → register → calibrate
- ✅ Database operations (insert, update, query)
- ✅ pgvector similarity search for plates
- ✅ Link table operations (food_entry_plates)
- ✅ Plate usage tracking (times_recognized)
- ✅ User isolation (plates scoped to users)
- ✅ Calibration persistence
- ✅ Integration with food logging pipeline

**Test Count Target:** ~15 integration tests

---

### Performance Benchmarks

**File:** `tests/performance/test_plate_recognition_performance.py`

**Benchmarks:**
- ✅ **Plate detection speed:** Target <500ms
- ✅ **Embedding generation:** Target <2s (reuses Phase 1 service)
- ✅ **Plate matching speed:** Target <100ms (pgvector search)
- ✅ **Full pipeline latency:** Target <3s total
- ✅ **Concurrent detection:** 10 simultaneous requests
- ✅ **Database scalability:** Performance with 100+ plates per user

**Performance Target:** <500ms for plate detection + matching (excludes embedding generation)

---

### Accuracy Validation

**File:** `tests/validation/test_plate_recognition_accuracy.py`

**Validation Criteria:**
- ✅ **Plate matching accuracy:** >80% on test set
- ✅ **False positive rate:** <10% (wrong plate matches)
- ✅ **Calibration accuracy:** Within 15% of true dimensions
- ✅ **Portion estimation improvement:** 20% better than vision-only

**Test Dataset:**
- 50 test images with known plates
- 10 unique plate types
- Multiple angles and lighting conditions
- Ground truth calibration data

---

## 📊 Success Criteria (from Issue)

### Must Have (Phase 2 Completion)

- [x] **Migration:** `022_recognized_plates.sql` created with proper schema
  - recognized_plates table
  - food_entry_plates link table
  - HNSW index for embeddings
  - Helper functions

- [x] **Service:** `src/services/plate_recognition.py` implemented
  - Plate detection from images
  - CLIP embedding generation (reuses Phase 1)
  - Plate matching using pgvector
  - New plate registration
  - Calibration system

- [x] **Calibration:** Size estimation from reference portions
  - Calculate capacity from known portions
  - Store calibration data
  - Use for future portion estimates

- [x] **Linking:** Food entries linked to recognized plates
  - food_entry_plates table populated
  - Confidence scores tracked
  - Usage statistics updated

- [x] **Metadata:** Plate characteristics stored
  - Type (plate/bowl/cup)
  - Color, shape
  - Estimated dimensions
  - Calibration status

- [x] **Testing:** Recognition accuracy >80%
  - Unit tests (20+)
  - Integration tests (15+)
  - Performance benchmarks
  - Accuracy validation

---

## 🚀 Implementation Phases

### Phase 2A: Database Foundation (2 hours)
1. ✅ Create migration `022_recognized_plates.sql`
2. ✅ Define database schema and indexes
3. ✅ Create PostgreSQL functions
4. ✅ Test migration locally

### Phase 2B: Core Service (4 hours)
1. ✅ Create data models (`src/models/plate.py`)
2. ✅ Implement `PlateRecognitionService`
   - Plate detection
   - Embedding generation (reuse Phase 1)
   - Plate matching
   - New plate registration
3. ✅ Create calibration utilities
4. ✅ Unit tests for core service

### Phase 2C: Integration (3 hours)
1. ✅ Integrate with food logging pipeline
2. ✅ Link food entries to plates
3. ✅ Update plate usage statistics
4. ✅ Integration tests

### Phase 2D: Testing & Validation (3 hours)
1. ✅ Performance benchmarks
2. ✅ Accuracy validation
3. ✅ Edge case testing
4. ✅ Documentation and cleanup

**Total Estimated Time:** 12 hours

---

## 🔗 Dependencies & Prerequisites

### From Phase 1 (Already Complete)
- ✅ pgvector extension installed
- ✅ ImageEmbeddingService operational
- ✅ CLIP embedding infrastructure (512-dim)
- ✅ HNSW indexing patterns established
- ✅ OpenAI API integration

### New Dependencies
- **None** - All required libraries already in `requirements.txt`
- Pillow (image processing) - already installed
- OpenAI SDK - already configured

### Database Requirements
- PostgreSQL 14+ with pgvector extension
- Existing tables: `users`, `food_entries`
- Migration 021 must be applied

---

## 🎯 Key Design Decisions

### 1. Plate Detection Strategy
**Decision:** Use Vision AI + CLIP embeddings (not computer vision segmentation)

**Rationale:**
- Simpler implementation (reuses Phase 1 infrastructure)
- Good enough accuracy for MVP
- Can enhance with CV later if needed
- Avoids introducing new ML dependencies

**Implementation:**
- Ask Vision AI to describe the plate in the image
- Generate CLIP embedding for plate region
- Use embedding similarity for matching

### 2. Calibration Approach
**Decision:** Reference portion method (user provides accurate weights)

**Rationale:**
- Most accurate calibration method
- Leverages existing user behavior (weighing food)
- Progressive improvement (calibrates over time)
- No complex geometric calculations needed

**Example:**
```
User logs: "170g cottage cheese in my blue bowl"
System: Detects blue bowl is 50% full
System: Calculates total capacity = 340g
System: Stores calibration for future use
```

### 3. Matching Threshold
**Decision:** 0.85 similarity threshold for plate matching

**Rationale:**
- Higher than food matching (0.70) due to simpler visual features
- Plates are more consistent than food appearance
- Reduces false positives (matching wrong plates)
- User can manually merge plates if needed

### 4. Embedding Scope
**Decision:** Generate embeddings for plate region, not full image

**Rationale:**
- More precise matching (focuses on plate, not food)
- Better discrimination between similar plates
- Avoids food content affecting plate matching

**Alternative Considered:** Full image embeddings
- **Rejected:** Food content would interfere with plate recognition

---

## 📝 Implementation Notes

### Image Processing Approach

For MVP (Phase 2), we'll use a **simplified detection** approach:

```python
async def detect_plate_region(image_path: str) -> Optional[PlateRegion]:
    """
    Simplified plate detection using Vision AI

    Ask Vision AI: "Describe the plate/bowl/container in this image"
    Then crop the approximate region for embedding generation.

    Note: This is a pragmatic MVP approach. Can be enhanced
    with CV segmentation (e.g., SAM, Mask R-CNN) in later phases.
    """
```

**Enhancement Path (Future):**
- Phase 3+: Integrate Segment Anything Model (SAM)
- Phase 3+: Use bounding box detection
- Phase 3+: Handle multiple plates per image

---

### Calibration Workflow (User Experience)

**Automatic Calibration (Preferred):**
1. User logs food with accurate weight: "170g cottage cheese"
2. System detects plate, asks: "Is this in your white bowl?" (shows image)
3. User confirms
4. System calibrates: "Great! I'll use this bowl as a reference for portions."

**Manual Calibration (Fallback):**
1. User command: `/calibrate_plate`
2. User sends photo of empty plate
3. System asks: "What's the diameter or capacity?"
4. User provides: "20cm diameter" or "500ml bowl"
5. System stores calibration

---

### Edge Cases to Handle

1. **No plate visible**
   - Detection returns None
   - Food entry proceeds normally (Phase 1 behavior)
   - No plate linking

2. **Multiple plates in image**
   - MVP: Detect largest/most prominent plate
   - Future: Detect all plates, ask user which one

3. **Plate partially visible**
   - Lower confidence score
   - Still attempt matching if >60% visible

4. **New plate not matching**
   - Create new entry in recognized_plates
   - Auto-name: "Plate #1", "Bowl #2", etc.
   - User can rename later

5. **Conflicting calibrations**
   - Use weighted average based on confidence
   - Prefer recent calibrations (time decay)

---

## 🔍 Quality Assurance

### Code Quality Standards
- ✅ Type hints for all functions
- ✅ Docstrings for all public methods
- ✅ Error handling for all external calls
- ✅ Logging at INFO/DEBUG/WARNING levels
- ✅ No placeholders or TODOs in production code

### Performance Standards
- ✅ <500ms for plate detection + matching
- ✅ <100ms for database similarity search
- ✅ <3s total latency for full pipeline
- ✅ Async/non-blocking operations

### Accuracy Standards
- ✅ >80% plate matching accuracy
- ✅ <10% false positive rate
- ✅ >20% improvement in portion estimation (calibrated vs uncalibrated)

---

## 📦 Deliverables Checklist

### Code Deliverables
- [ ] `migrations/022_recognized_plates.sql` - Database migration
- [ ] `src/models/plate.py` - Data models
- [ ] `src/services/plate_recognition.py` - Core service
- [ ] `src/utils/plate_calibration.py` - Calibration utilities
- [ ] `src/bot.py` (updated) - Integration with food logging

### Test Deliverables
- [ ] `tests/unit/test_plate_recognition.py` - Unit tests (~20 tests)
- [ ] `tests/integration/test_plate_recognition_integration.py` - Integration tests (~15 tests)
- [ ] `tests/performance/test_plate_recognition_performance.py` - Performance benchmarks
- [ ] `tests/validation/test_plate_recognition_accuracy.py` - Accuracy validation

### Documentation Deliverables
- [ ] This implementation plan (EPIC_009_PHASE_2_IMPLEMENTATION_PLAN.md)
- [ ] Recognition accuracy report
- [ ] Phase 2 completion summary (after implementation)

---

## 🎉 Definition of Done

Phase 2 is complete when:

1. ✅ All code deliverables implemented and committed
2. ✅ All tests passing (unit + integration + performance)
3. ✅ Migration 022 applied to database
4. ✅ Accuracy validation >80% on test dataset
5. ✅ Performance benchmarks meet targets (<500ms)
6. ✅ Integration with food logging pipeline functional
7. ✅ No placeholders or TODOs in production code
8. ✅ Code review completed
9. ✅ Documentation complete
10. ✅ Recognition accuracy report generated

---

## 🔜 Next Steps (After Phase 2)

**Phase 3:** Pattern Detection (scheduled next)
- Detect recurring food combinations
- Identify eating patterns
- Build contextual memory

**Dependencies from Phase 2:**
- Plate recognition enables better portion pattern detection
- Calibrated plates improve accuracy of pattern analysis
- Historical plate data informs habit learning

---

## 📞 Questions & Clarifications

### Open Questions
1. **Q:** Should we support multi-plate detection (e.g., plate + coffee cup)?
   **A:** MVP: Single plate per image. Multi-plate in Phase 3+.

2. **Q:** How to handle plate rotations/angles?
   **A:** CLIP embeddings are somewhat rotation-invariant. Acceptable for MVP.

3. **Q:** Should users be able to manually label plates?
   **A:** Yes, add simple rename functionality: `/rename_plate <id> <new_name>`

4. **Q:** What about non-plate containers (Tupperware, bags)?
   **A:** Support as "container" type. Same workflow.

---

## 🎯 Success Metrics

### Technical Metrics
- **Plate detection rate:** >70% of food photos have detectable plates
- **Matching accuracy:** >80% correct plate matches
- **Calibration coverage:** >50% of users have ≥1 calibrated plate after 2 weeks
- **Performance:** <500ms average detection + matching time

### User Impact Metrics
- **Portion accuracy improvement:** 20% better estimates with calibrated plates
- **User engagement:** Users calibrate plates voluntarily (no prompting needed)
- **Retention:** Plate recognition doesn't add friction to food logging

---

## 📚 References

- **Epic 009 Full Specification:** `/home/samuel/supervisor/health-agent/.bmad/epic-009-ultimate-memory-system.md` (Note: File doesn't exist yet, using issue description)
- **Phase 1 Summary:** `EPIC_009_PHASE_1_IMPLEMENTATION_SUMMARY.md`
- **Database Migration 021:** `migrations/021_food_image_references.sql`
- **Image Embedding Service:** `src/services/image_embedding.py`
- **Visual Search Service:** `src/services/visual_food_search.py`

---

**Plan Status:** ✅ READY FOR IMPLEMENTATION
**Next Step:** Begin Phase 2A - Database Foundation
**Estimated Completion:** 12 hours from start

---

*This plan follows the architecture and patterns established in Phase 1, ensuring consistency and maintainability across the Epic 009 implementation.*
