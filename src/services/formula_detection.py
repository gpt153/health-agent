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
import re

from src.db.connection import db
from src.exceptions import ServiceError
from src.services.visual_food_search import get_visual_search_service

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

    Epic 009 - Phase 3: Food Formulas & Auto-Suggestion
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

        Raises:
            FormulaDetectionError: If detection fails
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
                f"Detected {len(candidates)} formula candidates from {len(entries)} entries "
                f"(min_occurrences={min_occurrences})"
            )

            return candidates

        except Exception as e:
            logger.error(f"Formula detection failed: {e}", exc_info=True)
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
        if not quantity:
            return ""

        # Extract number from quantity string
        match = re.search(r'(\d+(?:\.\d+)?)', str(quantity))
        if not match:
            return str(quantity).lower()

        value = float(match.group(1))

        # Round to nearest 10 for grouping (allows small variations)
        rounded = round(value / 10) * 10

        # Preserve unit
        unit = str(quantity).replace(match.group(1), "").strip()

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

        Raises:
            FormulaDetectionError: If search fails
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
                        # Handle JSONB columns
                        foods = row["foods"]
                        if isinstance(foods, str):
                            foods = json.loads(foods)

                        total_macros = row["total_macros"]
                        if isinstance(total_macros, str):
                            total_macros = json.loads(total_macros)

                        formulas.append({
                            "id": str(row["formula_id"]),
                            "name": row["name"],
                            "keywords": row["keywords"],
                            "foods": foods,
                            "total_calories": row["total_calories"],
                            "total_macros": total_macros,
                            "times_used": row["times_used"],
                            "match_score": row["match_score"]
                        })

                    logger.info(
                        f"Found {len(formulas)} formulas for keyword '{keyword}'"
                    )

                    return formulas

        except Exception as e:
            logger.error(f"Keyword search failed: {e}", exc_info=True)
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

        Raises:
            FormulaDetectionError: If matching fails
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

                # Handle JSONB columns
                foods = best_match["foods"]
                if isinstance(foods, str):
                    foods = json.loads(foods)

                total_macros = best_match["total_macros"]
                if isinstance(total_macros, str):
                    total_macros = json.loads(total_macros)

                return {
                    "id": str(best_match["id"]),
                    "name": best_match["name"],
                    "foods": foods,
                    "total_calories": best_match["total_calories"],
                    "total_macros": total_macros,
                    "match_score": best_score
                }

            return None

        except Exception as e:
            logger.error(f"Fuzzy matching failed: {e}", exc_info=True)
            raise FormulaDetectionError(f"Fuzzy matching failed: {e}")

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

        Raises:
            FormulaDetectionError: If visual search fails
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

                # Handle JSONB columns
                foods = formula["foods"]
                if isinstance(foods, str):
                    foods = json.loads(foods)

                total_macros = formula["total_macros"]
                if isinstance(total_macros, str):
                    total_macros = json.loads(total_macros)

                formulas.append({
                    "id": str(formula["id"]),
                    "name": formula["name"],
                    "foods": foods,
                    "total_calories": formula["total_calories"],
                    "total_macros": total_macros,
                    "times_used": formula["times_used"],
                    "visual_similarity": visual_match.similarity_score if visual_match else 0.0,
                    "confidence_level": visual_match.confidence_level if visual_match else "low"
                })

            logger.info(
                f"Found {len(formulas)} formulas from visual search"
            )

            return formulas

        except Exception as e:
            logger.error(f"Visual formula search failed: {e}", exc_info=True)
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

        Raises:
            FormulaDetectionError: If search fails
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
            combined_matches: Dict[str, Dict[str, Any]] = {}

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
            logger.error(f"Combined formula search failed: {e}", exc_info=True)
            raise FormulaDetectionError(f"Combined search failed: {e}")


# Global service instance
_detection_service: Optional[FormulaDetectionService] = None


def get_formula_detection_service() -> FormulaDetectionService:
    """Get or create the global formula detection service instance"""
    global _detection_service

    if _detection_service is None:
        _detection_service = FormulaDetectionService()

    return _detection_service
