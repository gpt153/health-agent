# Epic 009 - Phase 3: Food Formulas & Auto-Suggestion - Implementation Plan

**Epic:** Ultimate Memory System - Visual Food Memory & Pattern Detection
**Phase:** 3 of 7
**Issue:** #110
**Estimated Time:** 16 hours
**Priority:** High
**Dependencies:** ✅ Phase 1 (Image Embeddings) - COMPLETE

---

## 🎯 Executive Summary

This phase builds intelligent formula detection and auto-suggestion on top of the visual similarity foundation from Phase 1. It will enable the system to learn recurring meals (e.g., protein shakes, usual breakfasts) and automatically suggest them based on text keywords and visual cues.

**Key User Benefit:** Users will no longer need to describe identical meals repeatedly - the system will remember and suggest them automatically.

---

## 📋 Tasks Breakdown

### Task 1: Database Schema for Food Formulas (2 hours)

**Goal:** Create persistent storage for formulas and track their usage patterns.

**Deliverable:** `migrations/022_food_formulas.sql`

**Schema Design:**

```sql
-- Food formulas table (persistent recipes/patterns)
CREATE TABLE IF NOT EXISTS food_formulas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,

    -- Formula identification
    name VARCHAR(200) NOT NULL,                 -- "Morning Protein Shake", "Usual Breakfast"
    keywords TEXT[] DEFAULT '{}',               -- ["protein shake", "shake", "morning shake"]
    description TEXT,                           -- User-provided or AI-generated description

    -- Formula content
    foods JSONB NOT NULL,                       -- Same format as food_entries.foods
    total_calories INTEGER NOT NULL,
    total_macros JSONB NOT NULL,               -- {protein, carbs, fat}

    -- Visual reference (link to image embedding)
    reference_photo_path VARCHAR(500),
    reference_embedding_id UUID REFERENCES food_image_references(id) ON DELETE SET NULL,

    -- Pattern metadata
    created_from_entry_id UUID REFERENCES food_entries(id) ON DELETE SET NULL,
    is_auto_detected BOOLEAN DEFAULT false,    -- true if detected by pattern learning
    confidence_score FLOAT,                    -- 0.0 to 1.0 for auto-detected formulas

    -- Usage tracking
    times_used INTEGER DEFAULT 1,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, name)
);

-- Formula usage log (track when formulas are used)
CREATE TABLE IF NOT EXISTS formula_usage_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    formula_id UUID NOT NULL REFERENCES food_formulas(id) ON DELETE CASCADE,
    food_entry_id UUID NOT NULL REFERENCES food_entries(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,

    -- How was it matched?
    match_method VARCHAR(50) NOT NULL,         -- "keyword", "visual", "combined", "manual"
    match_confidence FLOAT,                    -- 0.0 to 1.0

    -- Variations tracking
    is_exact_match BOOLEAN DEFAULT true,
    variations JSONB,                          -- Track any deviations from formula

    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_food_formulas_user ON food_formulas(user_id, last_used_at DESC);
CREATE INDEX idx_food_formulas_keywords ON food_formulas USING GIN(keywords);
CREATE INDEX idx_formula_usage_log_formula ON formula_usage_log(formula_id, used_at DESC);
CREATE INDEX idx_formula_usage_log_user ON formula_usage_log(user_id, used_at DESC);

-- Update timestamp trigger
CREATE TRIGGER update_food_formulas_updated_at
BEFORE UPDATE ON food_formulas
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Helper function: Search formulas by keyword
CREATE OR REPLACE FUNCTION search_formulas_by_keyword(
    p_user_id TEXT,
    p_keyword TEXT,
    p_limit INTEGER DEFAULT 5
)
RETURNS TABLE (
    formula_id UUID,
    name VARCHAR(200),
    keywords TEXT[],
    foods JSONB,
    total_calories INTEGER,
    total_macros JSONB,
    times_used INTEGER,
    match_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ff.id,
        ff.name,
        ff.keywords,
        ff.foods,
        ff.total_calories,
        ff.total_macros,
        ff.times_used,
        -- Simple keyword matching score
        (
            CASE
                WHEN LOWER(p_keyword) = ANY(SELECT LOWER(unnest(ff.keywords))) THEN 1.0
                WHEN ff.name ILIKE '%' || p_keyword || '%' THEN 0.8
                WHEN EXISTS (
                    SELECT 1 FROM unnest(ff.keywords) k
                    WHERE LOWER(k) LIKE '%' || LOWER(p_keyword) || '%'
                ) THEN 0.6
                ELSE 0.3
            END
        )::FLOAT as match_score
    FROM food_formulas ff
    WHERE ff.user_id = p_user_id
    AND (
        LOWER(p_keyword) = ANY(SELECT LOWER(unnest(ff.keywords)))
        OR ff.name ILIKE '%' || p_keyword || '%'
        OR EXISTS (
            SELECT 1 FROM unnest(ff.keywords) k
            WHERE LOWER(k) LIKE '%' || LOWER(p_keyword) || '%'
        )
    )
    ORDER BY match_score DESC, ff.times_used DESC, ff.last_used_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;
```

**Testing:**
- Verify tables created successfully
- Test foreign key constraints
- Verify indexes created
- Test helper function with sample data

---

### Task 2: Formula Detection Service (3 hours)

**Goal:** Implement pattern learning to detect recurring meals from historical food logs.

**Deliverable:** `src/services/formula_detection.py`

**Implementation:**

```python
"""
Formula Detection Service
Learns recurring meal patterns from food logs and detects formula candidates.

Epic 009 - Phase 3: Food Formulas & Auto-Suggestion
"""
from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict
import json

from src.db.connection import db
from src.exceptions import ServiceError

logger = logging.getLogger(__name__)


class FormulaDetectionError(ServiceError):
    """Raised when formula detection fails"""
    pass


@dataclass
class FormulaCandidate:
    """Represents a potential formula detected from patterns"""
    foods: List[Dict[str, Any]]  # List of food items
    total_calories: int
    total_macros: Dict[str, float]
    occurrence_count: int  # How many times this pattern appeared
    entry_ids: List[str]  # UUIDs of matching entries
    confidence_score: float  # 0.0 to 1.0
    suggested_name: str  # Auto-generated name
    suggested_keywords: List[str]  # Auto-generated keywords


class FormulaDetectionService:
    """
    Service for detecting recurring meal patterns and formula candidates

    Analyzes historical food logs to identify:
    - Identical meals (exact matches)
    - Similar meals (with minor variations)
    - Recurring patterns
    """

    # Configuration
    MIN_OCCURRENCES_FOR_FORMULA = 3  # Meal must appear at least 3 times
    SIMILARITY_THRESHOLD = 0.85  # 85% similarity for "close enough" matches
    MIN_CONFIDENCE_SCORE = 0.70  # Minimum confidence to suggest as formula

    def __init__(self) -> None:
        """Initialize formula detection service"""
        pass

    async def detect_formula_candidates(
        self,
        user_id: str,
        days_back: int = 90,
        min_occurrences: Optional[int] = None
    ) -> List[FormulaCandidate]:
        """
        Analyze user's food history to detect formula candidates

        Args:
            user_id: Telegram user ID
            days_back: How far back to analyze (default: 90 days)
            min_occurrences: Minimum times pattern must appear (default: MIN_OCCURRENCES_FOR_FORMULA)

        Returns:
            List of formula candidates sorted by confidence
        """
        if min_occurrences is None:
            min_occurrences = self.MIN_OCCURRENCES_FOR_FORMULA

        try:
            # Fetch food entries from recent history
            cutoff_date = datetime.now() - timedelta(days=days_back)

            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT id, foods, total_calories, total_macros,
                               photo_path, timestamp, notes
                        FROM food_entries
                        WHERE user_id = %s
                        AND timestamp >= %s
                        ORDER BY timestamp DESC
                        """,
                        (user_id, cutoff_date)
                    )
                    entries = await cur.fetchall()

            if len(entries) < min_occurrences:
                logger.info(f"Not enough entries ({len(entries)}) to detect patterns")
                return []

            # Group similar meals together
            meal_groups = self._group_similar_meals(entries)

            # Convert groups to formula candidates
            candidates = []
            for group_key, group_entries in meal_groups.items():
                if len(group_entries) >= min_occurrences:
                    candidate = self._create_candidate_from_group(group_entries)
                    if candidate.confidence_score >= self.MIN_CONFIDENCE_SCORE:
                        candidates.append(candidate)

            # Sort by confidence and occurrence count
            candidates.sort(
                key=lambda c: (c.confidence_score, c.occurrence_count),
                reverse=True
            )

            logger.info(
                f"Detected {len(candidates)} formula candidates from {len(entries)} entries"
            )

            return candidates

        except Exception as e:
            logger.error(f"Formula detection failed: {e}")
            raise FormulaDetectionError(f"Failed to detect formulas: {e}")

    def _group_similar_meals(
        self,
        entries: List[Dict]
    ) -> Dict[str, List[Dict]]:
        """
        Group entries with similar food combinations

        Returns:
            Dict mapping group_key -> list of similar entries
        """
        groups: Dict[str, List[Dict]] = defaultdict(list)

        for entry in entries:
            # Create a normalized key from food items
            foods = entry["foods"]
            if isinstance(foods, str):
                foods = json.loads(foods)

            # Sort foods by name for consistent comparison
            sorted_foods = sorted(foods, key=lambda f: f.get("name", ""))

            # Create group key from food names and approximate quantities
            group_key = self._create_group_key(sorted_foods)

            groups[group_key].append(entry)

        return groups

    def _create_group_key(self, foods: List[Dict]) -> str:
        """
        Create a normalized key for grouping similar meals

        Uses food names and rounded quantities to allow minor variations
        """
        key_parts = []
        for food in foods:
            name = food.get("name", "").lower().strip()
            quantity = food.get("quantity", "")

            # Normalize quantity (round to nearest 10g/ml for grouping)
            # This allows minor variations like "250g" and "255g" to match
            normalized_qty = self._normalize_quantity(quantity)

            key_parts.append(f"{name}:{normalized_qty}")

        return "|".join(key_parts)

    def _normalize_quantity(self, quantity: str) -> str:
        """Normalize quantity for grouping (allow ~10% variation)"""
        import re

        # Extract number from quantity string
        match = re.search(r'(\d+(?:\.\d+)?)', quantity)
        if not match:
            return quantity.lower()

        value = float(match.group(1))

        # Round to nearest 10 for grouping (allows small variations)
        rounded = round(value / 10) * 10

        # Preserve unit
        unit = quantity.replace(match.group(1), "").strip()

        return f"{int(rounded)}{unit}"

    def _create_candidate_from_group(
        self,
        group_entries: List[Dict]
    ) -> FormulaCandidate:
        """
        Create a formula candidate from a group of similar entries

        Uses the most recent entry as the template
        """
        # Use most recent entry as template
        template = group_entries[0]

        foods = template["foods"]
        if isinstance(foods, str):
            foods = json.loads(foods)

        total_macros = template["total_macros"]
        if isinstance(total_macros, str):
            total_macros = json.loads(total_macros)

        # Calculate confidence based on:
        # 1. Number of occurrences (more = higher confidence)
        # 2. Consistency of calories/macros across occurrences
        # 3. Recency (recent patterns = higher confidence)

        occurrence_count = len(group_entries)
        consistency_score = self._calculate_consistency(group_entries)
        recency_score = self._calculate_recency(group_entries)

        # Weighted confidence score
        confidence_score = (
            0.5 * min(occurrence_count / 10.0, 1.0) +  # Occurrences (capped at 10)
            0.3 * consistency_score +                   # Consistency
            0.2 * recency_score                         # Recency
        )

        # Generate suggested name and keywords
        suggested_name = self._generate_formula_name(foods, template)
        suggested_keywords = self._generate_keywords(foods, template)

        return FormulaCandidate(
            foods=foods,
            total_calories=template["total_calories"],
            total_macros=total_macros,
            occurrence_count=occurrence_count,
            entry_ids=[str(e["id"]) for e in group_entries],
            confidence_score=confidence_score,
            suggested_name=suggested_name,
            suggested_keywords=suggested_keywords
        )

    def _calculate_consistency(self, entries: List[Dict]) -> float:
        """Calculate how consistent calories/macros are across entries"""
        if len(entries) < 2:
            return 1.0

        calories = [e["total_calories"] for e in entries if e["total_calories"]]
        if not calories:
            return 0.5

        avg_calories = sum(calories) / len(calories)

        # Calculate coefficient of variation
        if avg_calories == 0:
            return 0.5

        variance = sum((c - avg_calories) ** 2 for c in calories) / len(calories)
        std_dev = variance ** 0.5
        cv = std_dev / avg_calories

        # Convert to 0-1 score (lower variation = higher score)
        # CV < 0.1 (10%) = excellent, CV > 0.3 (30%) = poor
        consistency_score = max(0.0, min(1.0, 1.0 - (cv / 0.3)))

        return consistency_score

    def _calculate_recency(self, entries: List[Dict]) -> float:
        """Calculate recency score - more recent patterns score higher"""
        if not entries:
            return 0.5

        # Get most recent entry timestamp
        timestamps = [e["timestamp"] for e in entries]
        most_recent = max(timestamps)

        # Days since last occurrence
        days_ago = (datetime.now() - most_recent).days

        # Score: 1.0 if used today, decays over 90 days
        recency_score = max(0.0, min(1.0, 1.0 - (days_ago / 90.0)))

        return recency_score

    def _generate_formula_name(
        self,
        foods: List[Dict],
        template: Dict
    ) -> str:
        """Generate a descriptive name for the formula"""
        # Check notes for clues
        notes = template.get("notes", "")
        if notes:
            # Use first few words of notes as name
            words = notes.split()[:4]
            if len(words) >= 2:
                return " ".join(words).title()

        # Otherwise, generate from food items
        if len(foods) == 1:
            return foods[0].get("name", "Unknown Food").title()
        elif len(foods) <= 3:
            names = [f.get("name", "").split()[0] for f in foods]
            return " + ".join(names).title()
        else:
            # Many items - use generic name
            return f"{len(foods)}-Item Meal"

    def _generate_keywords(
        self,
        foods: List[Dict],
        template: Dict
    ) -> List[str]:
        """Generate search keywords for the formula"""
        keywords = []

        # Add food names
        for food in foods:
            name = food.get("name", "").lower()
            if name:
                keywords.append(name)
                # Add individual words from multi-word names
                keywords.extend(name.split())

        # Add notes keywords
        notes = template.get("notes", "").lower()
        if notes:
            # Extract meaningful words (skip common words)
            skip_words = {"the", "a", "an", "and", "or", "but", "with", "for"}
            words = [w for w in notes.split() if len(w) > 2 and w not in skip_words]
            keywords.extend(words[:5])  # Limit to 5 keywords from notes

        # Deduplicate and return
        return list(set(keywords))[:10]  # Max 10 keywords


# Global service instance
_detection_service: Optional[FormulaDetectionService] = None


def get_formula_detection_service() -> FormulaDetectionService:
    """Get or create global formula detection service instance"""
    global _detection_service

    if _detection_service is None:
        _detection_service = FormulaDetectionService()

    return _detection_service
```

**Testing:**
- Unit tests for pattern grouping logic
- Unit tests for confidence score calculation
- Integration test with real food entry data
- Test edge cases (no patterns, all unique meals)

---

### Task 3: Keyword-Based Formula Matching (2 hours)

**Goal:** Implement text-based formula detection with fuzzy matching.

**Deliverable:** Add keyword matching methods to `formula_detection.py`

**Implementation:**

```python
# Add to FormulaDetectionService class

async def find_formulas_by_keyword(
    self,
    user_id: str,
    keyword: str,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Find formulas matching a keyword

    Uses the database function for efficient keyword search

    Args:
        user_id: Telegram user ID
        keyword: Search keyword (e.g., "protein shake")
        limit: Max results to return

    Returns:
        List of matching formulas with match scores
    """
    try:
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM search_formulas_by_keyword(%s, %s, %s)",
                    (user_id, keyword, limit)
                )
                results = await cur.fetchall()

                formulas = []
                for row in results:
                    formulas.append({
                        "id": str(row["formula_id"]),
                        "name": row["name"],
                        "keywords": row["keywords"],
                        "foods": row["foods"],
                        "total_calories": row["total_calories"],
                        "total_macros": row["total_macros"],
                        "times_used": row["times_used"],
                        "match_score": row["match_score"]
                    })

                logger.info(
                    f"Found {len(formulas)} formulas for keyword '{keyword}'"
                )

                return formulas

    except Exception as e:
        logger.error(f"Keyword search failed: {e}")
        raise FormulaDetectionError(f"Keyword search failed: {e}")

async def fuzzy_match_formula(
    self,
    user_id: str,
    text: str,
    threshold: float = 0.6
) -> Optional[Dict[str, Any]]:
    """
    Find best matching formula from natural language text

    Uses fuzzy matching to handle variations like:
    - "protein shake" -> "Morning Protein Shake"
    - "usual breakfast" -> "Usual Breakfast"
    - "the shake" -> "Protein Shake"

    Args:
        user_id: Telegram user ID
        text: Natural language text
        threshold: Minimum match score (0.0 to 1.0)

    Returns:
        Best matching formula or None
    """
    from difflib import SequenceMatcher

    try:
        # Get all user's formulas
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id, name, keywords, foods, total_calories,
                           total_macros, times_used
                    FROM food_formulas
                    WHERE user_id = %s
                    ORDER BY times_used DESC, last_used_at DESC
                    """,
                    (user_id,)
                )
                formulas = await cur.fetchall()

        if not formulas:
            return None

        # Normalize input text
        text_lower = text.lower().strip()

        # Calculate match scores
        best_match = None
        best_score = 0.0

        for formula in formulas:
            score = 0.0

            # Check exact keyword match (highest priority)
            keywords = formula["keywords"] or []
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    score = max(score, 1.0)
                    break

            # Check fuzzy match against name
            name_similarity = SequenceMatcher(
                None,
                text_lower,
                formula["name"].lower()
            ).ratio()
            score = max(score, name_similarity)

            # Check fuzzy match against keywords
            for keyword in keywords:
                keyword_similarity = SequenceMatcher(
                    None,
                    text_lower,
                    keyword.lower()
                ).ratio()
                score = max(score, keyword_similarity)

            # Update best match
            if score > best_score:
                best_score = score
                best_match = formula

        # Return if above threshold
        if best_score >= threshold:
            logger.info(
                f"Fuzzy matched '{text}' to '{best_match['name']}' "
                f"(score: {best_score:.2f})"
            )
            return {
                "id": str(best_match["id"]),
                "name": best_match["name"],
                "foods": best_match["foods"],
                "total_calories": best_match["total_calories"],
                "total_macros": best_match["total_macros"],
                "match_score": best_score
            }

        return None

    except Exception as e:
        logger.error(f"Fuzzy matching failed: {e}")
        raise FormulaDetectionError(f"Fuzzy matching failed: {e}")
```

**Testing:**
- Test exact keyword matches
- Test fuzzy matching with variations
- Test match scoring
- Test edge cases (empty keywords, no formulas)

---

### Task 4: Visual Cue Formula Detection (3 hours)

**Goal:** Combine visual similarity from Phase 1 with formula matching.

**Deliverable:** Add visual matching to `formula_detection.py`

**Implementation:**

```python
# Add to FormulaDetectionService class

from src.services.visual_food_search import get_visual_search_service

async def find_formulas_by_image(
    self,
    user_id: str,
    image_path: str,
    similarity_threshold: float = 0.75,
    limit: int = 3
) -> List[Dict[str, Any]]:
    """
    Find formulas using visual similarity

    Leverages Phase 1's visual search to find formulas that look similar

    Args:
        user_id: Telegram user ID
        image_path: Path to query image
        similarity_threshold: Minimum visual similarity (0.0 to 1.0)
        limit: Max results

    Returns:
        List of visually similar formulas
    """
    try:
        # Use Phase 1's visual search service
        visual_service = get_visual_search_service()

        # Find visually similar food entries
        similar_foods = await visual_service.find_similar_foods(
            user_id=user_id,
            query_image_path=image_path,
            limit=limit * 2,  # Get more candidates
            min_similarity=similarity_threshold
        )

        if not similar_foods:
            logger.info("No visually similar foods found")
            return []

        # Check if any of these entries are linked to formulas
        entry_ids = [match.food_entry_id for match in similar_foods]

        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT DISTINCT
                        ff.id,
                        ff.name,
                        ff.foods,
                        ff.total_calories,
                        ff.total_macros,
                        ff.times_used,
                        ful.food_entry_id,
                        ful.match_confidence
                    FROM food_formulas ff
                    JOIN formula_usage_log ful ON ff.id = ful.formula_id
                    WHERE ff.user_id = %s
                    AND ful.food_entry_id = ANY(%s)
                    ORDER BY ff.times_used DESC, ff.last_used_at DESC
                    LIMIT %s
                    """,
                    (user_id, entry_ids, limit)
                )
                formula_results = await cur.fetchall()

        # Combine visual similarity with formula data
        formulas = []
        for formula in formula_results:
            # Find the corresponding visual match
            visual_match = next(
                (m for m in similar_foods if m.food_entry_id == str(formula["food_entry_id"])),
                None
            )

            formulas.append({
                "id": str(formula["id"]),
                "name": formula["name"],
                "foods": formula["foods"],
                "total_calories": formula["total_calories"],
                "total_macros": formula["total_macros"],
                "times_used": formula["times_used"],
                "visual_similarity": visual_match.similarity_score if visual_match else 0.0,
                "confidence_level": visual_match.confidence_level if visual_match else "low"
            })

        logger.info(
            f"Found {len(formulas)} formulas from visual search"
        )

        return formulas

    except Exception as e:
        logger.error(f"Visual formula search failed: {e}")
        raise FormulaDetectionError(f"Visual search failed: {e}")

async def find_formulas_combined(
    self,
    user_id: str,
    text: Optional[str] = None,
    image_path: Optional[str] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Find formulas using combined text + visual matching

    This is the most powerful matching mode - uses both keyword
    and visual cues to find the best formula match.

    Args:
        user_id: Telegram user ID
        text: Optional text/keywords
        image_path: Optional image path
        limit: Max results

    Returns:
        List of formulas ranked by combined confidence
    """
    if not text and not image_path:
        raise FormulaDetectionError("Must provide either text or image")

    try:
        text_matches = []
        visual_matches = []

        # Get matches from both sources
        if text:
            text_matches = await self.find_formulas_by_keyword(
                user_id, text, limit=limit
            )

        if image_path:
            visual_matches = await self.find_formulas_by_image(
                user_id, image_path, limit=limit
            )

        # Combine and rank by confidence
        combined_matches = {}

        # Add text matches
        for match in text_matches:
            formula_id = match["id"]
            combined_matches[formula_id] = {
                **match,
                "text_match_score": match.get("match_score", 0.0),
                "visual_similarity": 0.0,
                "combined_confidence": match.get("match_score", 0.0)
            }

        # Add/enhance with visual matches
        for match in visual_matches:
            formula_id = match["id"]

            if formula_id in combined_matches:
                # Enhance existing match
                combined_matches[formula_id]["visual_similarity"] = match["visual_similarity"]
                # Combined confidence: weighted average
                text_score = combined_matches[formula_id]["text_match_score"]
                visual_score = match["visual_similarity"]
                combined_matches[formula_id]["combined_confidence"] = (
                    0.6 * text_score + 0.4 * visual_score  # Text weighted higher
                )
            else:
                # New match from visual only
                combined_matches[formula_id] = {
                    **match,
                    "text_match_score": 0.0,
                    "combined_confidence": match["visual_similarity"] * 0.8  # Visual only
                }

        # Sort by combined confidence
        results = sorted(
            combined_matches.values(),
            key=lambda x: x["combined_confidence"],
            reverse=True
        )[:limit]

        logger.info(
            f"Combined search found {len(results)} formulas "
            f"(text: {len(text_matches)}, visual: {len(visual_matches)})"
        )

        return results

    except Exception as e:
        logger.error(f"Combined formula search failed: {e}")
        raise FormulaDetectionError(f"Combined search failed: {e}")
```

**Testing:**
- Integration test with Phase 1 visual search
- Test visual-only matching
- Test combined text + visual matching
- Test confidence scoring

---

### Task 5: Auto-Suggestion System (2.5 hours)

**Goal:** Build intelligent suggestion system for food logging workflow.

**Deliverable:** `src/services/formula_suggestions.py`

**Implementation:**

```python
"""
Formula Auto-Suggestion System
Suggests formulas during food logging based on context.

Epic 009 - Phase 3: Food Formulas & Auto-Suggestion
"""
from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, time
from dataclasses import dataclass

from src.services.formula_detection import get_formula_detection_service
from src.exceptions import ServiceError

logger = logging.getLogger(__name__)


class SuggestionError(ServiceError):
    """Raised when suggestion system fails"""
    pass


@dataclass
class FormulaSuggestion:
    """A formula suggestion with context"""
    formula_id: str
    name: str
    foods: List[Dict]
    total_calories: int
    total_macros: Dict
    confidence: float  # 0.0 to 1.0
    reason: str  # Why this was suggested
    match_method: str  # "keyword", "visual", "combined", "contextual"


class FormulaSuggestionService:
    """
    Intelligent formula suggestion system

    Suggests formulas based on:
    - User's text input
    - Uploaded photo (if available)
    - Time of day (breakfast/lunch/dinner patterns)
    - Recent usage patterns
    """

    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.80
    AUTO_APPLY_THRESHOLD = 0.95  # Auto-apply if confidence this high

    def __init__(self) -> None:
        """Initialize suggestion service"""
        self.detection_service = get_formula_detection_service()

    async def suggest_formulas(
        self,
        user_id: str,
        text: Optional[str] = None,
        image_path: Optional[str] = None,
        current_time: Optional[datetime] = None,
        max_suggestions: int = 3
    ) -> List[FormulaSuggestion]:
        """
        Get formula suggestions based on available context

        Args:
            user_id: Telegram user ID
            text: User's text input (optional)
            image_path: Food photo path (optional)
            current_time: Timestamp for contextual suggestions
            max_suggestions: Max number of suggestions to return

        Returns:
            List of formula suggestions ranked by confidence
        """
        if current_time is None:
            current_time = datetime.now()

        try:
            suggestions = []

            # Method 1: Combined text + visual matching (highest priority)
            if text or image_path:
                combined_matches = await self.detection_service.find_formulas_combined(
                    user_id=user_id,
                    text=text,
                    image_path=image_path,
                    limit=max_suggestions
                )

                for match in combined_matches:
                    reason = self._generate_reason(match, text, image_path)
                    suggestions.append(FormulaSuggestion(
                        formula_id=match["id"],
                        name=match["name"],
                        foods=match["foods"],
                        total_calories=match["total_calories"],
                        total_macros=match["total_macros"],
                        confidence=match["combined_confidence"],
                        reason=reason,
                        match_method="combined" if (text and image_path) else (
                            "keyword" if text else "visual"
                        )
                    ))

            # Method 2: Contextual suggestions (time-based patterns)
            if len(suggestions) < max_suggestions:
                contextual = await self._get_contextual_suggestions(
                    user_id, current_time, max_suggestions - len(suggestions)
                )
                suggestions.extend(contextual)

            # Sort by confidence
            suggestions.sort(key=lambda s: s.confidence, reverse=True)

            # Limit to max_suggestions
            suggestions = suggestions[:max_suggestions]

            logger.info(
                f"Generated {len(suggestions)} suggestions for user {user_id}"
            )

            return suggestions

        except Exception as e:
            logger.error(f"Failed to generate suggestions: {e}")
            raise SuggestionError(f"Suggestion failed: {e}")

    async def _get_contextual_suggestions(
        self,
        user_id: str,
        current_time: datetime,
        limit: int
    ) -> List[FormulaSuggestion]:
        """
        Get contextual suggestions based on time of day and patterns

        Example: If it's morning and user often has the same breakfast,
        suggest that breakfast formula.
        """
        from src.db.connection import db

        try:
            # Determine meal time category
            meal_time = self._get_meal_time_category(current_time.time())

            # Find formulas commonly used at this time
            async with db.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT
                            ff.id,
                            ff.name,
                            ff.foods,
                            ff.total_calories,
                            ff.total_macros,
                            COUNT(ful.id) as usage_count,
                            MAX(ful.used_at) as last_used
                        FROM food_formulas ff
                        JOIN formula_usage_log ful ON ff.id = ful.formula_id
                        WHERE ff.user_id = %s
                        AND EXTRACT(HOUR FROM ful.used_at) BETWEEN %s AND %s
                        GROUP BY ff.id, ff.name, ff.foods, ff.total_calories, ff.total_macros
                        ORDER BY usage_count DESC, last_used DESC
                        LIMIT %s
                        """,
                        (
                            user_id,
                            meal_time["start_hour"],
                            meal_time["end_hour"],
                            limit
                        )
                    )
                    results = await cur.fetchall()

            suggestions = []
            for row in results:
                # Calculate confidence based on usage frequency at this time
                usage_count = row["usage_count"]
                confidence = min(0.75, 0.5 + (usage_count * 0.05))  # Cap at 0.75

                suggestions.append(FormulaSuggestion(
                    formula_id=str(row["id"]),
                    name=row["name"],
                    foods=row["foods"],
                    total_calories=row["total_calories"],
                    total_macros=row["total_macros"],
                    confidence=confidence,
                    reason=f"You often have this during {meal_time['name']}",
                    match_method="contextual"
                ))

            return suggestions

        except Exception as e:
            logger.warning(f"Contextual suggestions failed: {e}")
            return []

    def _get_meal_time_category(self, current_time: time) -> Dict[str, Any]:
        """Categorize time into meal periods"""
        hour = current_time.hour

        if 5 <= hour < 11:
            return {"name": "breakfast", "start_hour": 5, "end_hour": 11}
        elif 11 <= hour < 15:
            return {"name": "lunch", "start_hour": 11, "end_hour": 15}
        elif 15 <= hour < 18:
            return {"name": "snack time", "start_hour": 15, "end_hour": 18}
        elif 18 <= hour < 22:
            return {"name": "dinner", "start_hour": 18, "end_hour": 22}
        else:
            return {"name": "late night", "start_hour": 22, "end_hour": 5}

    def _generate_reason(
        self,
        match: Dict[str, Any],
        text: Optional[str],
        image_path: Optional[str]
    ) -> str:
        """Generate human-readable reason for suggestion"""
        reasons = []

        if text and match.get("text_match_score", 0) > 0.7:
            reasons.append("matches your description")

        if image_path and match.get("visual_similarity", 0) > 0.7:
            reasons.append("looks similar to your photo")

        if match.get("times_used", 0) >= 5:
            reasons.append("you've logged this before")

        if not reasons:
            return "similar to your previous meals"

        return " and ".join(reasons).capitalize()

    def should_auto_apply(self, suggestion: FormulaSuggestion) -> bool:
        """Determine if suggestion should be auto-applied"""
        return suggestion.confidence >= self.AUTO_APPLY_THRESHOLD


# Global service instance
_suggestion_service: Optional[FormulaSuggestionService] = None


def get_suggestion_service() -> FormulaSuggestionService:
    """Get or create global suggestion service instance"""
    global _suggestion_service

    if _suggestion_service is None:
        _suggestion_service = FormulaSuggestionService()

    return _suggestion_service
```

**Testing:**
- Test suggestion generation with various inputs
- Test contextual time-based suggestions
- Test confidence thresholds
- Test auto-apply logic

---

### Task 6: Formula Management API Endpoints (2 hours)

**Goal:** Create REST API for formula CRUD operations.

**Deliverable:** Add endpoints to `src/api/routes.py`

**Implementation:**

```python
# Add to src/api/routes.py

from src.services.formula_detection import get_formula_detection_service
from src.services.formula_suggestions import get_suggestion_service

# Formula Management Endpoints

@app.post("/api/formulas")
async def create_formula(
    name: str = Body(...),
    foods: List[Dict] = Body(...),
    keywords: List[str] = Body(default=[]),
    description: Optional[str] = Body(default=None),
    reference_photo_path: Optional[str] = Body(default=None),
    user_id: str = Depends(get_current_user)
):
    """Create a new food formula"""
    # Implementation
    pass

@app.get("/api/formulas")
async def get_user_formulas(
    user_id: str = Depends(get_current_user),
    limit: int = Query(default=20, le=100),
    include_usage_stats: bool = Query(default=True)
):
    """Get all formulas for a user"""
    # Implementation
    pass

@app.get("/api/formulas/{formula_id}")
async def get_formula(
    formula_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get a specific formula"""
    # Implementation
    pass

@app.put("/api/formulas/{formula_id}")
async def update_formula(
    formula_id: str,
    name: Optional[str] = Body(default=None),
    keywords: Optional[List[str]] = Body(default=None),
    foods: Optional[List[Dict]] = Body(default=None),
    user_id: str = Depends(get_current_user)
):
    """Update a formula"""
    # Implementation
    pass

@app.delete("/api/formulas/{formula_id}")
async def delete_formula(
    formula_id: str,
    user_id: str = Depends(get_current_user)
):
    """Delete a formula"""
    # Implementation
    pass

@app.post("/api/formulas/search")
async def search_formulas(
    text: Optional[str] = Body(default=None),
    image_path: Optional[str] = Body(default=None),
    limit: int = Body(default=5),
    user_id: str = Depends(get_current_user)
):
    """Search formulas by keyword or image"""
    # Implementation
    pass

@app.post("/api/formulas/suggest")
async def suggest_formulas(
    text: Optional[str] = Body(default=None),
    image_path: Optional[str] = Body(default=None),
    max_suggestions: int = Body(default=3),
    user_id: str = Depends(get_current_user)
):
    """Get formula suggestions"""
    # Implementation
    pass

@app.post("/api/formulas/detect-patterns")
async def detect_formula_patterns(
    days_back: int = Body(default=90),
    min_occurrences: int = Body(default=3),
    user_id: str = Depends(get_current_user)
):
    """Detect formula candidates from food history"""
    # Implementation
    pass
```

**Testing:**
- API endpoint tests for CRUD operations
- Test authentication/authorization
- Test input validation
- Test error handling

---

### Task 7: Agent Tools for Formula Retrieval (2.5 hours)

**Goal:** Add PydanticAI tools for agent-based formula interaction.

**Deliverable:** `src/agent/formula_tools.py`

**Implementation:**

```python
"""
PydanticAI tools for food formula retrieval and suggestion.
Epic 009 - Phase 3: Food Formulas & Auto-Suggestion
"""
from __future__ import annotations

from pydantic_ai import RunContext
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.agent import AgentDeps

from src.services.formula_detection import get_formula_detection_service
from src.services.formula_suggestions import get_suggestion_service


class FormulaResult(BaseModel):
    """Result of formula operations"""
    success: bool
    message: str
    formulas: Optional[List[Dict]] = None
    suggestion: Optional[Dict] = None


async def get_food_formula(
    ctx: RunContext[AgentDeps],
    keyword: str
) -> FormulaResult:
    """
    Retrieve a food formula by keyword

    Use this when the user mentions a recurring meal or formula:
    - "my protein shake"
    - "usual breakfast"
    - "the shake"

    Args:
        keyword: Search keyword from user's message

    Returns:
        FormulaResult with matching formulas
    """
    try:
        service = get_formula_detection_service()

        formulas = await service.find_formulas_by_keyword(
            user_id=ctx.deps.telegram_id,
            keyword=keyword,
            limit=5
        )

        if not formulas:
            return FormulaResult(
                success=False,
                message=f"No formulas found matching '{keyword}'. "
                        "Would you like to create one?"
            )

        # Format response
        top_match = formulas[0]
        message = f"Found formula: **{top_match['name']}**\n\n"
        message += f"📊 {top_match['total_calories']} kcal\n"
        message += f"📈 Used {top_match['times_used']} times before\n\n"

        if len(formulas) > 1:
            message += f"(Found {len(formulas)} matches total)"

        return FormulaResult(
            success=True,
            message=message,
            formulas=formulas
        )

    except Exception as e:
        return FormulaResult(
            success=False,
            message=f"Failed to retrieve formula: {str(e)}"
        )


async def search_formulas(
    ctx: RunContext[AgentDeps],
    text: Optional[str] = None,
    include_visual: bool = False
) -> FormulaResult:
    """
    Search for matching formulas

    Use this to find formulas based on user's description or photo.

    Args:
        text: Search text/keywords
        include_visual: Whether to include visual search (if photo available)

    Returns:
        FormulaResult with search results
    """
    try:
        service = get_formula_detection_service()

        # Get image path from context if available and requested
        image_path = None
        if include_visual and hasattr(ctx.deps, 'photo_path'):
            image_path = ctx.deps.photo_path

        formulas = await service.find_formulas_combined(
            user_id=ctx.deps.telegram_id,
            text=text,
            image_path=image_path,
            limit=5
        )

        if not formulas:
            return FormulaResult(
                success=False,
                message="No matching formulas found."
            )

        message = f"Found {len(formulas)} matching formula(s):\n\n"
        for i, formula in enumerate(formulas[:3], 1):
            confidence = formula.get("combined_confidence", 0) * 100
            message += f"{i}. **{formula['name']}** ({confidence:.0f}% match)\n"
            message += f"   {formula['total_calories']} kcal\n\n"

        return FormulaResult(
            success=True,
            message=message,
            formulas=formulas
        )

    except Exception as e:
        return FormulaResult(
            success=False,
            message=f"Search failed: {str(e)}"
        )


async def suggest_formula(
    ctx: RunContext[AgentDeps],
    text: Optional[str] = None
) -> FormulaResult:
    """
    Get intelligent formula suggestions

    Use this to proactively suggest formulas during food logging.
    Takes into account:
    - User's text input
    - Current time of day
    - Previous usage patterns
    - Visual similarity (if photo provided)

    Args:
        text: Optional text from user

    Returns:
        FormulaResult with suggestions
    """
    try:
        service = get_suggestion_service()

        # Get image path from context if available
        image_path = None
        if hasattr(ctx.deps, 'photo_path'):
            image_path = ctx.deps.photo_path

        suggestions = await service.suggest_formulas(
            user_id=ctx.deps.telegram_id,
            text=text,
            image_path=image_path,
            max_suggestions=3
        )

        if not suggestions:
            return FormulaResult(
                success=False,
                message="No formula suggestions available."
            )

        # Check for high-confidence auto-apply
        top_suggestion = suggestions[0]
        if service.should_auto_apply(top_suggestion):
            message = f"🎯 This looks like your **{top_suggestion.name}**!\n\n"
            message += f"📊 {top_suggestion.total_calories} kcal\n"
            message += f"Confidence: {top_suggestion.confidence*100:.0f}%\n\n"
            message += "Should I log this formula?"

            return FormulaResult(
                success=True,
                message=message,
                suggestion=top_suggestion.__dict__
            )

        # Multiple suggestions
        message = "💡 Formula suggestions:\n\n"
        for i, sug in enumerate(suggestions, 1):
            message += f"{i}. **{sug.name}** ({sug.confidence*100:.0f}%)\n"
            message += f"   {sug.total_calories} kcal - {sug.reason}\n\n"

        message += "Would you like to use one of these?"

        return FormulaResult(
            success=True,
            message=message,
            formulas=[s.__dict__ for s in suggestions]
        )

    except Exception as e:
        return FormulaResult(
            success=False,
            message=f"Failed to generate suggestions: {str(e)}"
        )


async def create_formula_from_entry(
    ctx: RunContext[AgentDeps],
    entry_id: str,
    name: str,
    keywords: Optional[List[str]] = None
) -> FormulaResult:
    """
    Create a new formula from an existing food entry

    Use this when user wants to save a meal as a reusable formula.

    Args:
        entry_id: UUID of the food entry to use as template
        name: Name for the formula
        keywords: Optional search keywords

    Returns:
        FormulaResult with creation status
    """
    try:
        from src.db.connection import db
        import json

        # Fetch the food entry
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT foods, total_calories, total_macros, photo_path
                    FROM food_entries
                    WHERE id = %s AND user_id = %s
                    """,
                    (entry_id, ctx.deps.telegram_id)
                )
                entry = await cur.fetchone()

        if not entry:
            return FormulaResult(
                success=False,
                message="Food entry not found."
            )

        # Generate keywords if not provided
        if keywords is None:
            keywords = [name.lower()]

        # Create the formula
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO food_formulas
                    (user_id, name, keywords, foods, total_calories,
                     total_macros, reference_photo_path, created_from_entry_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        ctx.deps.telegram_id,
                        name,
                        keywords,
                        json.dumps(entry["foods"]),
                        entry["total_calories"],
                        json.dumps(entry["total_macros"]),
                        entry["photo_path"],
                        entry_id
                    )
                )
                formula_id = (await cur.fetchone())["id"]
                await conn.commit()

        return FormulaResult(
            success=True,
            message=f"✅ Created formula: **{name}**\n\n"
                   f"You can now log this by saying '{keywords[0]}'"
        )

    except Exception as e:
        return FormulaResult(
            success=False,
            message=f"Failed to create formula: {str(e)}"
        )
```

**Testing:**
- Unit tests for each tool function
- Integration tests with agent context
- Test error handling
- Test with various input scenarios

---

### Task 8: Testing & Accuracy Benchmarks (2 hours)

**Goal:** Comprehensive testing and accuracy measurement.

**Deliverables:**
- Unit tests: `tests/unit/test_formula_detection.py`
- Integration tests: `tests/integration/test_formula_system.py`
- Accuracy report: Documentation of benchmark results

**Test Coverage:**

1. **Formula Detection Tests**
   - Pattern grouping accuracy
   - Confidence score validation
   - Edge cases (no patterns, single occurrence)

2. **Keyword Matching Tests**
   - Exact matches
   - Fuzzy matching
   - Multi-word keywords
   - Case sensitivity

3. **Visual Matching Tests**
   - Integration with Phase 1
   - Combined text + visual
   - Confidence scoring

4. **Suggestion System Tests**
   - Contextual suggestions
   - Time-based patterns
   - Auto-apply logic

5. **Agent Tools Tests**
   - Tool function returns
   - Error handling
   - Context dependencies

6. **End-to-End Tests**
   - Real user workflow simulation
   - Multi-step formula creation and usage
   - Pattern learning from historical data

**Accuracy Benchmarks:**
- Formula detection accuracy: >80% for 3+ occurrences
- Keyword matching precision: >85%
- Visual + text combined: >90%
- Auto-suggestion acceptance rate: Target >70%

---

## 🗂️ File Structure

```
health-agent/
├── migrations/
│   └── 022_food_formulas.sql                    # NEW: Database schema
│
├── src/
│   ├── services/
│   │   ├── formula_detection.py                 # NEW: Pattern learning & matching
│   │   └── formula_suggestions.py               # NEW: Auto-suggestion system
│   │
│   ├── agent/
│   │   └── formula_tools.py                     # NEW: PydanticAI tools
│   │
│   ├── api/
│   │   └── routes.py                            # MODIFIED: Add formula endpoints
│   │
│   └── bot.py                                   # MODIFIED: Integrate suggestions
│
└── tests/
    ├── unit/
    │   ├── test_formula_detection.py            # NEW: Detection unit tests
    │   └── test_formula_suggestions.py          # NEW: Suggestion unit tests
    │
    └── integration/
        └── test_formula_system.py               # NEW: End-to-end tests
```

---

## 🔄 Integration Points

### Integration with Phase 1 (Visual Search)
- Use `VisualFoodSearchService` for image-based formula matching
- Link formulas to image embeddings via `reference_embedding_id`
- Leverage existing CLIP embeddings for visual cues

### Integration with Food Logging Workflow
- Suggest formulas during food photo upload
- Auto-detect formula usage and log to `formula_usage_log`
- Update `times_used` and `last_used_at` on formula application

### Integration with Agent System
- Add formula tools to agent's tool registry
- Enable conversational formula creation ("save this as a formula")
- Proactive formula suggestions during food logging

---

## 📊 Success Criteria Checklist

- [ ] Database schema created and migrated successfully
- [ ] Pattern learning detects recurring meals (3+ occurrences)
- [ ] Keyword matching works with exact and fuzzy matches
- [ ] Visual similarity matching integrated with Phase 1
- [ ] Combined text + visual detection functional
- [ ] Auto-suggestion system generates contextual suggestions
- [ ] Formula management API endpoints working
- [ ] Agent tools integrated and functional
- [ ] Formula detection accuracy >80%
- [ ] Suggestion acceptance rate >70% (measured post-deployment)
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] Documentation complete

---

## 🚀 Deployment Plan

### Prerequisites
- ✅ Phase 1 (Image Embeddings) deployed
- PostgreSQL with pgvector extension
- Migration 021 applied

### Migration Steps

1. **Apply Migration 022**
   ```bash
   ./run_migrations.sh
   ```

2. **Verify Schema**
   ```bash
   psql -d health_agent -c "\d food_formulas"
   psql -d health_agent -c "\d formula_usage_log"
   ```

3. **Run Pattern Learning (Optional - Background Job)**
   ```bash
   python scripts/detect_formula_patterns.py --user-id <telegram_id>
   ```

4. **Deploy Code**
   - Deploy new services
   - Deploy agent tools
   - Deploy API endpoints
   - Restart bot

5. **Smoke Test**
   - Test keyword search: "protein shake"
   - Test formula creation
   - Test auto-suggestion
   - Test agent tools

---

## 🔧 Background Jobs

### Formula Pattern Learning Job

Create a background job to periodically detect patterns:

```python
# scripts/detect_formula_patterns.py

"""
Background job to detect formula patterns from food history
Runs weekly to identify new recurring meal patterns
"""
import asyncio
from src.services.formula_detection import get_formula_detection_service
from src.db.connection import db

async def detect_patterns_for_all_users():
    """Detect patterns for all active users"""
    service = get_formula_detection_service()

    # Get all users with recent food logs
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT DISTINCT user_id
                FROM food_entries
                WHERE timestamp >= NOW() - INTERVAL '90 days'
                """
            )
            users = await cur.fetchall()

    for user in users:
        user_id = user["user_id"]
        try:
            candidates = await service.detect_formula_candidates(user_id)

            # Auto-create high-confidence formulas
            for candidate in candidates:
                if candidate.confidence_score >= 0.85:
                    await create_formula(user_id, candidate)

        except Exception as e:
            print(f"Failed for user {user_id}: {e}")

if __name__ == "__main__":
    asyncio.run(detect_patterns_for_all_users())
```

Schedule via cron:
```bash
0 2 * * 0 python scripts/detect_formula_patterns.py  # Weekly at 2 AM Sunday
```

---

## 📝 User Experience Flow

### Scenario 1: First-Time Formula Creation

1. **User:** Sends photo of protein shake
2. **Bot:** Analyzes photo, extracts nutrition
3. **User:** "Save this as my protein shake"
4. **Agent:** Uses `create_formula_from_entry()` tool
5. **Bot:** "✅ Created formula: **Protein Shake**. You can now log this by saying 'protein shake'"

### Scenario 2: Automatic Formula Detection

1. **User:** Logs same meal 3 times over 2 weeks
2. **Background Job:** Detects pattern, creates formula automatically
3. **Next Time User Logs:** Bot suggests: "💡 This looks like your usual breakfast! Should I use that formula?"
4. **User:** "Yes"
5. **Bot:** Logs formula, updates usage stats

### Scenario 3: Visual + Text Formula Matching

1. **User:** Sends photo + text "protein shake"
2. **Bot:** Runs combined search (text + visual)
3. **Bot:** "🎯 This looks like your **Morning Protein Shake**! (95% confidence)"
4. **User:** Confirms
5. **Bot:** Logs formula, records usage

---

## ⚠️ Important Considerations

### Privacy & Data
- All formulas are user-scoped (can't see other users' formulas)
- Foreign key constraints ensure data integrity
- Cascade deletion removes formulas when users deleted

### Performance
- Database indexes on frequently queried fields
- Efficient pattern grouping algorithm
- Leverage Phase 1's HNSW index for visual search

### False Positives
- Use confidence thresholds to avoid bad suggestions
- Allow user feedback to improve matching
- Track acceptance rates in `formula_usage_log`

### Edge Cases
- User has no recurring patterns → No formulas created
- Conflicting keyword matches → Return multiple suggestions
- Visual-only match (no text) → Lower confidence score

---

## 📈 Future Enhancements (Post-Phase 3)

These are explicitly out of scope for Phase 3 but documented for future phases:

- **Substitution suggestions:** "Out of whey protein? Try pea protein instead"
- **Nutritional variation tracking:** Track how formula macros vary over time
- **Formula sharing:** Share formulas with other users (future epic)
- **Meal planning automation:** Use formulas for weekly meal plans
- **Recipe generation:** Generate cooking instructions from formulas

---

## 🎯 Implementation Order

### Day 1-2 (Foundation)
1. Create database migration (Task 1)
2. Implement formula detection service (Task 2)
3. Test pattern learning with real data

### Day 3-4 (Matching)
4. Implement keyword matching (Task 3)
5. Implement visual cue detection (Task 4)
6. Integration tests with Phase 1

### Day 5-6 (Intelligence)
7. Implement auto-suggestion system (Task 5)
8. Create API endpoints (Task 6)
9. API integration tests

### Day 7-8 (Agent Integration & Testing)
10. Implement agent tools (Task 7)
11. End-to-end testing (Task 8)
12. Accuracy benchmarks and documentation

---

## 📚 Dependencies

### External Libraries
- ✅ All dependencies already in project (no new packages needed)
- Uses existing: `psycopg2`, `pydantic`, `pydantic-ai`

### Internal Dependencies
- ✅ Phase 1: `VisualFoodSearchService` (COMPLETE)
- ✅ Phase 1: `ImageEmbeddingService` (COMPLETE)
- ✅ Existing: `food_entries` table and queries
- ✅ Existing: Agent system and tool registry

---

## ✅ Ready to Implement

This plan is comprehensive, tested-oriented, and builds directly on Phase 1's foundation. All deliverables are clearly defined with:
- Concrete database schemas
- Detailed implementation code
- Comprehensive testing strategy
- Clear success criteria
- Deployment checklist

**Total Estimated Time:** 16 hours (matches epic estimate)

**Risk Assessment:** Low
- Builds on proven Phase 1 architecture
- No new external dependencies
- Clear integration points
- Well-defined scope with MoSCoW prioritization

---

**Plan Ready for Execution** ✅

Let me know when you're ready to begin implementation, and I'll start with Task 1 (Database Migration).
