# Epic 009 - Phase 4: Portion Comparison - Implementation Plan

**Epic:** Ultimate Memory System - Visual Food Memory & Pattern Detection
**Phase:** 4 of 7
**Status:** 🔄 **IN PROGRESS**
**Estimated Time:** 12 hours
**Priority:** High
**Dependencies:** Phase 1 (Image Embeddings) ✅ + Phase 2 (Plate Recognition) ✅

---

## 🎯 Objective

Implement a portion comparison system that compares current photo portions to reference images using visual analysis and plate calibration data. Enable the system to provide context like "More rice, less chicken than last time" to Vision AI for improved accuracy.

---

## 📋 Requirements Analysis

### Must Have (MVP)
1. **Bounding Box Detection** - Detect individual food items within photos
2. **Area Comparison Algorithm** - Calculate pixel area differences between reference and current photos
3. **Portion Estimation** - Convert visual differences to rough weight estimates (±20% accuracy)
4. **Vision AI Integration** - Enhance prompts with comparison context
5. **User Feedback Mechanism** - Allow users to confirm/adjust AI estimates
6. **Accuracy Tracking** - Log estimates vs confirmed portions

### Should Have
- Plate-calibrated measurements using Phase 2 data
- Confidence scoring for estimates
- Multi-item detection per plate

### Could Have (Future)
- ML-based portion prediction
- Multi-angle photo support
- 3D portion reconstruction

### Won't Have
- Exact gram precision (unrealistic from photos alone)
- Complex 3D reconstruction

---

## 🏗️ Technical Architecture

### Data Flow
```
1. User sends food photo
   ↓
2. Detect plate using Phase 2 (PlateRecognitionService)
   ↓
3. Find similar reference images using Phase 1 (VisualFoodSearchService)
   ↓
4. Detect food item bounding boxes in both images
   ↓
5. Calculate area differences per food item
   ↓
6. Convert to portion estimates using plate calibration
   ↓
7. Generate comparison context for Vision AI
   ↓
8. Vision AI analyzes with enhanced prompts
   ↓
9. User confirms/adjusts estimates
   ↓
10. Store accuracy metrics for learning
```

### Component Architecture
```
┌─────────────────────────────────────────────────┐
│         PortionComparisonService                │
│  (src/services/portion_comparison.py)           │
│                                                  │
│  Methods:                                        │
│  - detect_food_items()                          │
│  - compare_portions()                           │
│  - calculate_portion_estimate()                 │
│  - generate_comparison_context()                │
│  - track_estimate_accuracy()                    │
└───────────┬─────────────────────────────────────┘
            │
            ├──► Uses: PlateRecognitionService (Phase 2)
            ├──► Uses: VisualFoodSearchService (Phase 1)
            ├──► Uses: ImageEmbeddingService (Phase 1)
            └──► Uses: Vision AI (existing)
```

---

## 📁 Deliverables

### 1. Database Schema
**File:** `migrations/024_portion_comparison.sql`

**Tables:**
```sql
-- Store bounding boxes for food items in images
CREATE TABLE food_item_detections (
    id UUID PRIMARY KEY,
    food_entry_id UUID REFERENCES food_entries(id),
    user_id VARCHAR(255) REFERENCES users(telegram_id),
    photo_path VARCHAR(500),

    -- Bounding box for detected item
    item_name VARCHAR(200),  -- "rice", "chicken", etc.
    bbox_x FLOAT,  -- Normalized 0-1
    bbox_y FLOAT,
    bbox_width FLOAT,
    bbox_height FLOAT,
    pixel_area FLOAT,  -- Calculated pixel area

    -- Metadata
    detection_confidence FLOAT,
    detection_method VARCHAR(50),  -- "vision_ai", "manual", etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Store portion comparisons
CREATE TABLE portion_comparisons (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES users(telegram_id),
    current_food_entry_id UUID REFERENCES food_entries(id),
    reference_food_entry_id UUID REFERENCES food_entries(id),

    -- Comparison data per food item
    item_name VARCHAR(200),
    current_area FLOAT,
    reference_area FLOAT,
    area_difference_ratio FLOAT,  -- (current - ref) / ref

    -- Portion estimates
    estimated_grams_difference FLOAT,
    confidence FLOAT,

    -- Context used for Vision AI
    comparison_context TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Track accuracy of portion estimates
CREATE TABLE portion_estimate_accuracy (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES users(telegram_id),
    portion_comparison_id UUID REFERENCES portion_comparisons(id),

    -- Estimate vs reality
    estimated_grams FLOAT,
    user_confirmed_grams FLOAT,
    variance_percentage FLOAT,  -- abs(estimated - confirmed) / confirmed

    -- Learning data
    plate_id UUID REFERENCES recognized_plates(id),
    food_item_type VARCHAR(200),
    visual_fill_percentage FLOAT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**
```sql
CREATE INDEX idx_food_detections_entry ON food_item_detections(food_entry_id);
CREATE INDEX idx_food_detections_user ON food_item_detections(user_id);
CREATE INDEX idx_portion_comparisons_current ON portion_comparisons(current_food_entry_id);
CREATE INDEX idx_portion_comparisons_reference ON portion_comparisons(reference_food_entry_id);
CREATE INDEX idx_portion_comparisons_user ON portion_comparisons(user_id);
CREATE INDEX idx_estimate_accuracy_user ON portion_estimate_accuracy(user_id);
CREATE INDEX idx_estimate_accuracy_variance ON portion_estimate_accuracy(variance_percentage);
```

**Functions:**
```sql
-- Get average accuracy for a user
CREATE FUNCTION get_user_portion_accuracy(p_user_id TEXT)
RETURNS TABLE (
    total_estimates INTEGER,
    avg_variance_percentage FLOAT,
    within_20_percent INTEGER
);

-- Get portion comparison history for a food item
CREATE FUNCTION get_food_item_portion_history(
    p_user_id TEXT,
    p_food_item VARCHAR(200),
    p_limit INTEGER
) RETURNS TABLE (
    comparison_date TIMESTAMP,
    area_difference_ratio FLOAT,
    estimated_grams_difference FLOAT,
    confirmed_grams_difference FLOAT
);
```

---

### 2. Data Models
**File:** `src/models/portion.py`

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class BoundingBox(BaseModel):
    """Bounding box for a detected food item"""
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    width: float = Field(ge=0.0, le=1.0)
    height: float = Field(ge=0.0, le=1.0)

    @property
    def area(self) -> float:
        """Calculate normalized area"""
        return self.width * self.height

class FoodItemDetection(BaseModel):
    """Detected food item in an image"""
    id: str
    food_entry_id: str
    user_id: str
    photo_path: str
    item_name: str
    bbox: BoundingBox
    pixel_area: float
    detection_confidence: float
    detection_method: str
    created_at: datetime

class PortionComparison(BaseModel):
    """Comparison between current and reference portions"""
    id: str
    user_id: str
    current_food_entry_id: str
    reference_food_entry_id: str
    item_name: str
    current_area: float
    reference_area: float
    area_difference_ratio: float  # (current - ref) / ref
    estimated_grams_difference: float
    confidence: float
    comparison_context: str
    created_at: datetime

    @property
    def percentage_difference(self) -> float:
        """Convert ratio to percentage"""
        return self.area_difference_ratio * 100

    @property
    def is_larger(self) -> bool:
        """Is current portion larger than reference?"""
        return self.area_difference_ratio > 0

class PortionEstimateAccuracy(BaseModel):
    """Accuracy tracking for portion estimates"""
    id: str
    user_id: str
    portion_comparison_id: str
    estimated_grams: float
    user_confirmed_grams: float
    variance_percentage: float
    plate_id: Optional[str]
    food_item_type: str
    visual_fill_percentage: Optional[float]
    created_at: datetime

    @property
    def is_within_target(self) -> bool:
        """Is estimate within ±20% target?"""
        return self.variance_percentage <= 20.0

class ComparisonContext(BaseModel):
    """Context to enhance Vision AI prompts"""
    reference_image_path: Optional[str]
    portion_differences: list[str]  # ["More rice (+30g)", "Less chicken (-50g)"]
    plate_info: Optional[str]  # "Using your blue plate #1 (calibrated)"
    confidence_notes: str  # "Medium confidence estimate"
```

---

### 3. Portion Comparison Service
**File:** `src/services/portion_comparison.py`

**Core Methods:**

```python
class PortionComparisonService:
    """
    Service for comparing food portions between images

    Features:
    - Detect food items using Vision AI bounding boxes
    - Compare areas between current and reference images
    - Calculate portion estimates using plate calibration
    - Generate comparison context for Vision AI
    - Track accuracy over time
    """

    # Configuration
    SIMILAR_IMAGE_THRESHOLD = 0.80  # 80% similarity to be considered "same meal"
    MIN_AREA_DIFFERENCE = 0.05  # Ignore <5% differences (noise)
    DEFAULT_DENSITY_G_PER_ML = 1.0  # Water-like density

    # Confidence thresholds
    HIGH_CONFIDENCE = 0.80
    MEDIUM_CONFIDENCE = 0.60

    async def detect_food_items(
        self,
        photo_path: str,
        user_id: str,
        food_entry_id: str
    ) -> list[FoodItemDetection]:
        """
        Detect individual food items and their bounding boxes

        Uses Vision AI to identify food items and extract bounding boxes.
        Falls back to simple heuristics if Vision AI doesn't support it.

        Args:
            photo_path: Path to food photo
            user_id: Telegram user ID
            food_entry_id: UUID of food entry

        Returns:
            List of detected food items with bounding boxes
        """

    async def compare_portions(
        self,
        current_photo_path: str,
        reference_photo_path: str,
        user_id: str,
        current_food_entry_id: str,
        reference_food_entry_id: str,
        plate_id: Optional[str] = None
    ) -> list[PortionComparison]:
        """
        Compare portions between current and reference images

        Steps:
        1. Detect food items in both images
        2. Match items by name/type
        3. Calculate area differences
        4. Convert to weight estimates using plate calibration
        5. Generate comparison context

        Args:
            current_photo_path: Current food photo
            reference_photo_path: Reference food photo
            user_id: Telegram user ID
            current_food_entry_id: UUID of current entry
            reference_food_entry_id: UUID of reference entry
            plate_id: Optional plate ID for calibration

        Returns:
            List of portion comparisons per food item
        """

    async def calculate_portion_estimate(
        self,
        area_difference_ratio: float,
        reference_grams: float,
        plate_capacity_ml: Optional[float] = None,
        food_density: float = DEFAULT_DENSITY_G_PER_ML
    ) -> tuple[float, float]:
        """
        Calculate portion estimate from area difference

        Args:
            area_difference_ratio: (current - ref) / ref
            reference_grams: Known weight of reference portion
            plate_capacity_ml: Optional plate capacity for calibration
            food_density: Density of food in g/ml

        Returns:
            (estimated_grams_difference, confidence)
        """

    async def generate_comparison_context(
        self,
        comparisons: list[PortionComparison],
        plate_name: Optional[str] = None
    ) -> ComparisonContext:
        """
        Generate context for Vision AI enhancement

        Creates natural language descriptions like:
        "This looks like your meal from yesterday, but with:
        - More rice (estimated +30g)
        - Less chicken (estimated -50g)
        Using your blue plate #1 (calibrated)"

        Args:
            comparisons: List of portion comparisons
            plate_name: Optional plate name for context

        Returns:
            ComparisonContext for Vision AI
        """

    async def track_estimate_accuracy(
        self,
        portion_comparison_id: str,
        user_id: str,
        estimated_grams: float,
        user_confirmed_grams: float,
        plate_id: Optional[str] = None,
        food_item_type: str = "unknown"
    ) -> PortionEstimateAccuracy:
        """
        Track accuracy of portion estimate

        Stores estimate vs actual for learning and improvement.

        Args:
            portion_comparison_id: UUID of comparison
            user_id: Telegram user ID
            estimated_grams: What we estimated
            user_confirmed_grams: What user confirmed
            plate_id: Optional plate used
            food_item_type: Type of food

        Returns:
            Accuracy record
        """

    async def find_reference_image(
        self,
        current_photo_path: str,
        user_id: str,
        food_item_name: Optional[str] = None
    ) -> Optional[tuple[str, str]]:
        """
        Find best reference image for comparison

        Uses Phase 1 visual similarity to find matching meals.

        Args:
            current_photo_path: Current food photo
            user_id: Telegram user ID
            food_item_name: Optional food item name for filtering

        Returns:
            (reference_photo_path, reference_food_entry_id) or None
        """

    async def get_user_accuracy_stats(
        self,
        user_id: str
    ) -> dict:
        """
        Get accuracy statistics for a user

        Returns:
            {
                "total_estimates": int,
                "avg_variance_percentage": float,
                "within_20_percent": int,
                "accuracy_rate": float
            }
        """
```

---

### 4. Vision AI Integration
**File:** `src/utils/vision.py` (modifications)

**Enhanced Prompts:**

```python
# Add to existing vision.py

async def analyze_food_photo_with_comparison(
    photo_path: str,
    caption: Optional[str] = None,
    user_id: Optional[str] = None,
    comparison_context: Optional[ComparisonContext] = None,
    **kwargs
) -> VisionAnalysisResult:
    """
    Analyze food photo with portion comparison context

    Enhanced version that includes comparison data in the prompt.
    """

    # Build enhanced prompt
    prompt_parts = []

    if comparison_context:
        prompt_parts.append(
            f"PORTION COMPARISON CONTEXT:\n"
            f"{', '.join(comparison_context.portion_differences)}\n"
            f"{comparison_context.confidence_notes}\n"
        )

        if comparison_context.plate_info:
            prompt_parts.append(f"PLATE INFO: {comparison_context.plate_info}\n")

    # Add to existing prompt
    if caption:
        prompt_parts.append(f"User description: {caption}")

    prompt_parts.append("""
    Analyze this food photo considering the portion comparison context above.
    Adjust your calorie and macro estimates based on the portion differences.
    """)

    # Call existing vision AI with enhanced prompt
    # ... (rest of implementation)
```

---

### 5. Food Photo Handler Integration
**File:** `src/handlers/food_photo.py` (modifications)

**Integration Points:**

```python
# Add to existing food photo handler

async def process_food_photo_with_portion_analysis(
    photo_path: str,
    user_id: str,
    caption: Optional[str] = None
):
    """
    Process food photo with portion comparison

    Workflow:
    1. Find similar reference images (Phase 1)
    2. Detect plate (Phase 2)
    3. Compare portions (Phase 4)
    4. Generate comparison context
    5. Analyze with Vision AI (enhanced)
    6. Store results
    """

    # 1. Find reference image
    portion_service = get_portion_comparison_service()
    reference = await portion_service.find_reference_image(
        photo_path, user_id
    )

    # 2. Detect plate
    plate_service = get_plate_recognition_service()
    detected_plate = await plate_service.detect_plate_from_image(
        photo_path, user_id
    )

    comparison_context = None
    if reference:
        # 3. Compare portions
        ref_photo, ref_entry_id = reference
        comparisons = await portion_service.compare_portions(
            current_photo_path=photo_path,
            reference_photo_path=ref_photo,
            user_id=user_id,
            current_food_entry_id=current_entry_id,  # Will be created
            reference_food_entry_id=ref_entry_id,
            plate_id=detected_plate.id if detected_plate else None
        )

        # 4. Generate context
        comparison_context = await portion_service.generate_comparison_context(
            comparisons,
            plate_name=detected_plate.plate_name if detected_plate else None
        )

    # 5. Analyze with Vision AI (enhanced)
    result = await analyze_food_photo_with_comparison(
        photo_path=photo_path,
        caption=caption,
        user_id=user_id,
        comparison_context=comparison_context
    )

    # 6. Store results
    # ... (save food entry, comparisons, etc.)
```

---

### 6. User Feedback Mechanism
**File:** `src/handlers/portion_feedback.py` (new)

**Telegram Interface:**

```python
class PortionFeedbackHandler:
    """
    Handle user feedback on portion estimates

    Provides inline keyboard for confirming/adjusting estimates.
    """

    async def show_portion_estimate_confirmation(
        self,
        message,
        portion_comparisons: list[PortionComparison]
    ):
        """
        Show estimate confirmation UI

        Example:
        "Your meal looks like:
        🍚 Rice: ~30g more than last time
        🍗 Chicken: ~50g less than last time

        [✅ Looks Right] [📏 Adjust]"
        """

    async def handle_portion_adjustment(
        self,
        callback_query,
        portion_comparison_id: str
    ):
        """
        Handle user adjusting estimate

        Shows slider or input for user to provide actual amount.
        Stores in portion_estimate_accuracy table.
        """
```

---

### 7. Tests

#### Unit Tests
**File:** `tests/unit/test_portion_comparison.py`

```python
# Test cases:
- test_bounding_box_area_calculation
- test_area_difference_calculation
- test_portion_estimate_from_area_ratio
- test_portion_estimate_with_plate_calibration
- test_comparison_context_generation
- test_confidence_calculation
- test_accuracy_variance_calculation
- test_find_reference_image
- test_match_food_items_by_name
- test_handle_no_reference_image
- test_handle_multiple_food_items
- test_handle_calibrated_vs_uncalibrated_plate
```

#### Integration Tests
**File:** `tests/integration/test_portion_comparison_integration.py`

```python
# Test cases:
- test_end_to_end_portion_comparison
- test_vision_ai_with_comparison_context
- test_portion_comparison_with_plate_calibration
- test_accuracy_tracking_workflow
- test_user_feedback_loop
- test_comparison_with_multiple_items
- test_comparison_without_reference_image
- test_database_storage_and_retrieval
- test_get_user_accuracy_stats
- test_portion_history_for_food_item
```

#### Performance Tests
**File:** `tests/performance/test_portion_comparison_performance.py`

```python
# Benchmarks:
- test_bounding_box_detection_speed (target: <500ms)
- test_area_comparison_calculation (target: <100ms)
- test_end_to_end_comparison_workflow (target: <2s)
- test_accuracy_stats_query (target: <200ms)
```

---

## 🔄 Implementation Strategy

### Phase 4A: Core Comparison (4 hours)
1. ✅ Database migration (024_portion_comparison.sql)
2. ✅ Data models (src/models/portion.py)
3. ✅ Core comparison service skeleton
4. ✅ Bounding box detection (MVP: simple heuristics)
5. ✅ Area comparison algorithm

### Phase 4B: Integration (4 hours)
6. ✅ Vision AI prompt enhancement
7. ✅ Food photo handler integration
8. ✅ Reference image finding
9. ✅ Plate calibration integration

### Phase 4C: Feedback & Tracking (4 hours)
10. ✅ User feedback mechanism (Telegram UI)
11. ✅ Accuracy tracking implementation
12. ✅ Statistics and reporting
13. ✅ Tests (unit + integration)
14. ✅ Performance validation

---

## 📊 Success Criteria

### Functional Requirements
- [ ] Portion comparison works: "More rice than last time"
- [ ] Estimate accuracy within ±20% variance for calibrated plates
- [ ] Vision AI uses comparison context correctly in prompts
- [ ] User can confirm/adjust estimates via Telegram
- [ ] Accuracy tracking stores and reports statistics
- [ ] All tests passing (unit + integration)

### Performance Requirements
- [ ] Bounding box detection: <500ms
- [ ] Area comparison: <100ms
- [ ] End-to-end workflow: <2s
- [ ] Accuracy stats query: <200ms

### Quality Requirements
- [ ] No placeholders or TODOs in production code
- [ ] Comprehensive error handling
- [ ] Full type hints throughout
- [ ] Documentation for all public methods
- [ ] Logging at appropriate levels

---

## 🔗 Integration Points

### Phase 1 (Image Embeddings) - ✅ COMPLETE
- **Uses:** `VisualFoodSearchService.find_similar_foods()` to find reference images
- **Uses:** `ImageEmbeddingService` for embedding generation (if needed)
- **Integration:** Find visually similar past meals for comparison

### Phase 2 (Plate Recognition) - ✅ COMPLETE
- **Uses:** `PlateRecognitionService.detect_plate_from_image()` to identify plate
- **Uses:** `RecognizedPlate.estimated_capacity_ml` for portion calibration
- **Uses:** `RecognizedPlate.is_calibrated` to adjust confidence
- **Integration:** Use plate dimensions to convert area to weight

### Existing Vision AI
- **Enhances:** Vision prompt with comparison context
- **Uses:** Existing `analyze_food_photo()` function
- **Integration:** Pass `ComparisonContext` to enhance accuracy

### Existing Food Logging
- **Enhances:** Food photo handler with portion analysis
- **Uses:** Existing food entry storage
- **Integration:** Store comparisons alongside food entries

---

## 🚧 Implementation Challenges & Solutions

### Challenge 1: Bounding Box Detection
**Problem:** OpenAI/Anthropic vision APIs may not support bounding box detection directly.

**Solutions:**
- **MVP:** Use simple heuristics (assume single centered item)
- **Iteration 1:** Use Vision AI to identify item regions descriptively
- **Iteration 2:** Integrate specialized object detection API (e.g., Roboflow)
- **Future:** Train custom YOLOv8 model for food items

**Chosen Approach (MVP):** Simple heuristics with manual adjustment option

### Challenge 2: Area to Weight Conversion
**Problem:** 2D area doesn't directly translate to 3D volume/weight.

**Solutions:**
- Use plate calibration as reference scale
- Assume consistent camera angles (user habit)
- Apply density estimates per food type
- Track accuracy and learn correction factors
- Provide ±20% confidence ranges

**Chosen Approach:** Calibrated plate + density + learning from feedback

### Challenge 3: Multi-Item Detection
**Problem:** Detecting and matching multiple food items per image.

**Solutions:**
- **MVP:** Single item assumption
- **Iteration 1:** Vision AI provides item names, estimate regions
- **Iteration 2:** Proper object detection with segmentation
- **Future:** Instance segmentation for overlapping items

**Chosen Approach (MVP):** Single item with Vision AI assistance for multiple

### Challenge 4: Reference Image Selection
**Problem:** Finding the "right" reference image to compare against.

**Solutions:**
- Use Phase 1 visual similarity (high threshold: 0.80+)
- Filter by food item name if available
- Prefer recent images (temporal relevance)
- Allow user to select reference manually

**Chosen Approach:** Automated visual similarity + manual override option

---

## 📈 Metrics & Monitoring

### Accuracy Metrics
- **Estimate Variance:** Track `abs(estimated - confirmed) / confirmed`
- **Target:** 80% of estimates within ±20% variance
- **Reporting:** Per-user accuracy dashboard

### Performance Metrics
- **Detection Time:** Time to detect food items
- **Comparison Time:** Time to compare portions
- **End-to-End Time:** Total workflow duration
- **Cache Hit Rate:** Reference image cache effectiveness

### Usage Metrics
- **Comparison Usage:** % of photos with comparisons
- **Feedback Rate:** % of comparisons with user feedback
- **Adjustment Rate:** % of estimates user adjusts
- **Calibrated Plate Usage:** % using calibrated plates

---

## 🔒 Privacy & Security

### User Data Isolation
- All queries filtered by `user_id`
- Foreign key constraints enforce data integrity
- Cascade deletion removes comparisons when entries deleted

### Data Retention
- Portion comparisons stored indefinitely for learning
- Accuracy data anonymized for system-wide improvements
- User can delete all data via standard deletion flow

### Sensitive Data
- Food photos: Same privacy as existing food logging
- Portion estimates: Private to user, not shared
- Accuracy stats: Aggregated without user identification

---

## 📝 Documentation

### User Documentation
- **Feature Guide:** "How portion comparison works"
- **Accuracy Expectations:** "Understand estimate confidence"
- **Feedback Guide:** "How to adjust estimates"
- **Best Practices:** "Tips for accurate comparisons"

### Developer Documentation
- **API Documentation:** All service methods
- **Database Schema:** Table relationships and indexes
- **Integration Guide:** How to use PortionComparisonService
- **Algorithm Explanation:** Area-to-weight conversion logic

---

## 🎯 Next Steps

1. **Review Plan** - Get stakeholder approval
2. **Create Branch** - `git checkout -b epic-009-phase-4-portion-comparison`
3. **Implement Phase 4A** - Core comparison logic
4. **Implement Phase 4B** - Integration with existing systems
5. **Implement Phase 4C** - Feedback and tracking
6. **Test & Validate** - Comprehensive testing
7. **Deploy** - Migration + code deployment
8. **Monitor** - Track accuracy and performance
9. **Iterate** - Improve based on real-world usage

---

## ✅ Definition of Done

- [ ] All database migrations applied successfully
- [ ] All data models created with full validation
- [ ] PortionComparisonService fully implemented
- [ ] Vision AI integration enhanced with comparison context
- [ ] Food photo handler integrated with portion analysis
- [ ] User feedback mechanism working in Telegram
- [ ] Accuracy tracking storing and reporting data
- [ ] All unit tests passing (>90% coverage)
- [ ] All integration tests passing
- [ ] Performance benchmarks meeting targets
- [ ] Documentation complete (code + user guides)
- [ ] No placeholders or TODOs in production code
- [ ] Code reviewed and approved
- [ ] Deployed to production
- [ ] Monitoring and alerting configured

---

**Plan Created:** January 17, 2025
**Ready for Implementation:** ✅ YES
**Estimated Effort:** 12 hours (4h + 4h + 4h)
**Quality Standard:** Production-ready, fully tested, no placeholders

---

## 🔄 Dependencies Checklist

### Phase 1 Dependencies - ✅ ALL COMPLETE
- [x] `food_image_references` table exists
- [x] `VisualFoodSearchService.find_similar_foods()` available
- [x] `ImageEmbeddingService` functional
- [x] CLIP embeddings generating correctly

### Phase 2 Dependencies - ✅ ALL COMPLETE
- [x] `recognized_plates` table exists
- [x] `PlateRecognitionService.detect_plate_from_image()` available
- [x] `PlateRecognitionService.get_plate_by_id()` available
- [x] Plate calibration data (capacity_ml, diameter_cm) stored

### Existing System Dependencies - ✅ ALL PRESENT
- [x] Vision AI integration (`src/utils/vision.py`)
- [x] Food entry storage (`food_entries` table)
- [x] Food photo handler (`src/handlers/food_photo.py`)
- [x] Telegram bot framework

---

**READY TO PROCEED WITH IMPLEMENTATION** 🚀
