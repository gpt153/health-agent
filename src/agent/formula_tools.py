"""
PydanticAI tools for food formula retrieval and suggestion.
Epic 009 - Phase 3: Food Formulas & Auto-Suggestion
"""
from __future__ import annotations

from pydantic_ai import RunContext
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, TYPE_CHECKING
import json

if TYPE_CHECKING:
    from src.agent import AgentDeps

from src.services.formula_detection import get_formula_detection_service
from src.services.formula_suggestions import get_suggestion_service
from src.db.connection import db


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
                suggestion={
                    "formula_id": top_suggestion.formula_id,
                    "name": top_suggestion.name,
                    "foods": top_suggestion.foods,
                    "total_calories": top_suggestion.total_calories,
                    "total_macros": top_suggestion.total_macros,
                    "confidence": top_suggestion.confidence,
                    "reason": top_suggestion.reason
                }
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
            formulas=[{
                "formula_id": s.formula_id,
                "name": s.name,
                "foods": s.foods,
                "total_calories": s.total_calories,
                "total_macros": s.total_macros,
                "confidence": s.confidence,
                "reason": s.reason
            } for s in suggestions]
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

        # Handle JSONB columns
        foods = entry["foods"]
        if isinstance(foods, str):
            foods = json.loads(foods)

        total_macros = entry["total_macros"]
        if isinstance(total_macros, str):
            total_macros = json.loads(total_macros)

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
                        json.dumps(foods),
                        entry["total_calories"],
                        json.dumps(total_macros),
                        entry["photo_path"],
                        entry_id
                    )
                )
                result = await cur.fetchone()
                formula_id = result["id"] if result else None
                await conn.commit()

        if not formula_id:
            return FormulaResult(
                success=False,
                message="Failed to create formula"
            )

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


async def list_user_formulas(
    ctx: RunContext[AgentDeps],
    limit: int = 10
) -> FormulaResult:
    """
    List user's saved formulas

    Use this when user asks "what formulas do I have?" or wants to see their saved meals.

    Args:
        limit: Maximum number of formulas to return

    Returns:
        FormulaResult with list of formulas
    """
    try:
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id, name, total_calories, times_used, last_used_at,
                           keywords, is_auto_detected
                    FROM food_formulas
                    WHERE user_id = %s
                    ORDER BY times_used DESC, last_used_at DESC
                    LIMIT %s
                    """,
                    (ctx.deps.telegram_id, limit)
                )
                formulas = await cur.fetchall()

        if not formulas:
            return FormulaResult(
                success=False,
                message="You don't have any saved formulas yet."
            )

        message = f"📋 Your formulas ({len(formulas)} total):\n\n"
        for formula in formulas:
            auto_tag = " 🤖" if formula["is_auto_detected"] else ""
            message += f"• **{formula['name']}**{auto_tag}\n"
            message += f"  {formula['total_calories']} kcal • Used {formula['times_used']} times\n"
            if formula["keywords"]:
                keywords_str = ", ".join(formula["keywords"][:3])
                message += f"  Keywords: {keywords_str}\n"
            message += "\n"

        return FormulaResult(
            success=True,
            message=message,
            formulas=[{
                "id": str(f["id"]),
                "name": f["name"],
                "total_calories": f["total_calories"],
                "times_used": f["times_used"],
                "keywords": f["keywords"]
            } for f in formulas]
        )

    except Exception as e:
        return FormulaResult(
            success=False,
            message=f"Failed to list formulas: {str(e)}"
        )
