"""
Pattern Feedback API Endpoints
Epic 009 - Phase 7: Integration & Agent Tools

REST API endpoints for user feedback on discovered patterns.

Endpoints:
- POST /patterns/{pattern_id}/feedback - Submit feedback (helpful/not helpful)
- GET /patterns/{pattern_id}/feedback - Get feedback summary
- GET /patterns/needing-feedback - Get patterns that need user feedback

This enables the learning loop where user feedback improves pattern quality.
"""
from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from src.db.connection import db
from src.services.pattern_detection import get_user_patterns

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/patterns", tags=["patterns"])


# Request/Response Models

class FeedbackSubmission(BaseModel):
    """Request body for submitting pattern feedback"""
    is_helpful: bool = Field(..., description="True if pattern was helpful, False otherwise")
    comment: Optional[str] = Field(None, description="Optional user comment about the pattern")


class FeedbackResponse(BaseModel):
    """Response after submitting feedback"""
    success: bool
    message: str
    pattern_id: int
    new_confidence: Optional[float] = None  # If confidence was adjusted


class FeedbackSummary(BaseModel):
    """Summary of feedback for a pattern"""
    pattern_id: int
    helpful_count: int
    not_helpful_count: int
    total_feedback: int
    helpful_ratio: Optional[float]  # 0-1, None if no feedback yet
    confidence: float
    confidence_adjusted: bool  # True if confidence was auto-adjusted from feedback


class PatternNeedingFeedback(BaseModel):
    """Pattern that needs user feedback"""
    pattern_id: int
    pattern_type: str
    actionable_insight: str
    confidence: float
    impact_score: float
    occurrences: int
    feedback_count: int


# Endpoints

@router.post("/{pattern_id}/feedback", response_model=FeedbackResponse)
async def submit_pattern_feedback(
    pattern_id: int,
    feedback: FeedbackSubmission,
    user_id: str  # In production, get from auth/session
):
    """
    Submit feedback on a discovered pattern

    Args:
        pattern_id: ID of the pattern
        feedback: Feedback submission (helpful/not helpful + optional comment)
        user_id: User submitting feedback (from auth)

    Returns:
        FeedbackResponse with success status

    Example:
        POST /patterns/123/feedback
        {
            "is_helpful": true,
            "comment": "This really helped me understand my energy levels!"
        }
    """
    try:
        # Verify pattern exists and belongs to user
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id, confidence, user_feedback
                    FROM discovered_patterns
                    WHERE id = %s AND user_id = %s
                    """,
                    (pattern_id, user_id)
                )
                pattern = await cur.fetchone()

                if not pattern:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Pattern {pattern_id} not found for user {user_id}"
                    )

                old_confidence = pattern['confidence']

                # Record feedback using DB function
                await cur.execute(
                    "SELECT record_pattern_feedback(%s, %s, %s)",
                    (pattern_id, feedback.is_helpful, feedback.comment)
                )
                await conn.commit()

                # Check if confidence was adjusted
                await cur.execute(
                    "SELECT confidence FROM discovered_patterns WHERE id = %s",
                    (pattern_id,)
                )
                result = await cur.fetchone()
                new_confidence = result['confidence'] if result else old_confidence

                logger.info(
                    f"Recorded feedback for pattern {pattern_id}: "
                    f"helpful={feedback.is_helpful}, user={user_id}"
                )

                return FeedbackResponse(
                    success=True,
                    message="Thank you for your feedback!",
                    pattern_id=pattern_id,
                    new_confidence=new_confidence if new_confidence != old_confidence else None
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to record feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record feedback: {str(e)}"
        )


@router.get("/{pattern_id}/feedback", response_model=FeedbackSummary)
async def get_pattern_feedback(
    pattern_id: int,
    user_id: str  # From auth
):
    """
    Get feedback summary for a pattern

    Args:
        pattern_id: ID of the pattern
        user_id: User requesting feedback (from auth)

    Returns:
        FeedbackSummary with feedback statistics

    Example:
        GET /patterns/123/feedback
        →
        {
            "pattern_id": 123,
            "helpful_count": 8,
            "not_helpful_count": 2,
            "total_feedback": 10,
            "helpful_ratio": 0.8,
            "confidence": 0.87,
            "confidence_adjusted": true
        }
    """
    try:
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                # Get pattern with feedback
                await cur.execute(
                    """
                    SELECT
                        id,
                        confidence,
                        user_feedback
                    FROM discovered_patterns
                    WHERE id = %s AND user_id = %s
                    """,
                    (pattern_id, user_id)
                )
                pattern = await cur.fetchone()

                if not pattern:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Pattern {pattern_id} not found"
                    )

                feedback_data = pattern['user_feedback'] or {}

                helpful_count = feedback_data.get('helpful_count', 0)
                not_helpful_count = feedback_data.get('not_helpful_count', 0)
                total_feedback = helpful_count + not_helpful_count

                # Calculate helpful ratio
                helpful_ratio = None
                if total_feedback > 0:
                    helpful_ratio = helpful_count / total_feedback

                # Check if confidence was adjusted
                # (would be indicated by feedback history)
                confidence_adjusted = len(feedback_data.get('feedback_history', [])) >= 5

                return FeedbackSummary(
                    pattern_id=pattern_id,
                    helpful_count=helpful_count,
                    not_helpful_count=not_helpful_count,
                    total_feedback=total_feedback,
                    helpful_ratio=helpful_ratio,
                    confidence=pattern['confidence'],
                    confidence_adjusted=confidence_adjusted
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get feedback summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get feedback: {str(e)}"
        )


@router.get("/needing-feedback", response_model=list[PatternNeedingFeedback])
async def get_patterns_needing_feedback(
    user_id: str,  # From auth
    limit: int = 5
):
    """
    Get high-quality patterns that need user feedback

    Returns patterns that:
    - Have high confidence (>= 0.70)
    - Have high impact (>= 50)
    - Have little or no feedback yet (< 3 feedbacks)

    Args:
        user_id: User ID (from auth)
        limit: Maximum patterns to return (default: 5)

    Returns:
        List of patterns needing feedback

    Example:
        GET /patterns/needing-feedback?limit=3
        →
        [
            {
                "pattern_id": 45,
                "pattern_type": "temporal_correlation",
                "actionable_insight": "You tend to feel tired...",
                "confidence": 0.85,
                "impact_score": 78.0,
                "occurrences": 12,
                "feedback_count": 0
            },
            ...
        ]
    """
    try:
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                # Use DB function to get patterns needing feedback
                await cur.execute(
                    "SELECT * FROM get_patterns_needing_feedback(%s, %s)",
                    (user_id, limit)
                )
                patterns = await cur.fetchall()

                return [
                    PatternNeedingFeedback(
                        pattern_id=p['pattern_id'],
                        pattern_type=p['pattern_type'],
                        actionable_insight=p['actionable_insight'],
                        confidence=p['confidence'],
                        impact_score=p['impact_score'],
                        occurrences=p['occurrences'],
                        feedback_count=p['feedback_count']
                    )
                    for p in patterns
                ]

    except Exception as e:
        logger.error(f"Failed to get patterns needing feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get patterns: {str(e)}"
        )


# Optional: Bulk feedback endpoint
@router.post("/feedback/bulk", response_model=dict)
async def submit_bulk_feedback(
    feedbacks: list[tuple[int, bool]],  # [(pattern_id, is_helpful), ...]
    user_id: str  # From auth
):
    """
    Submit feedback for multiple patterns at once

    Useful for batch operations or UI that shows multiple patterns

    Args:
        feedbacks: List of (pattern_id, is_helpful) tuples
        user_id: User submitting feedback

    Returns:
        Summary of bulk operation

    Example:
        POST /patterns/feedback/bulk
        {
            "feedbacks": [
                [123, true],
                [124, false],
                [125, true]
            ]
        }
    """
    try:
        success_count = 0
        error_count = 0

        async with db.connection() as conn:
            async with conn.cursor() as cur:
                for pattern_id, is_helpful in feedbacks:
                    try:
                        # Verify pattern belongs to user
                        await cur.execute(
                            "SELECT id FROM discovered_patterns WHERE id = %s AND user_id = %s",
                            (pattern_id, user_id)
                        )
                        if not await cur.fetchone():
                            error_count += 1
                            continue

                        # Record feedback
                        await cur.execute(
                            "SELECT record_pattern_feedback(%s, %s, NULL)",
                            (pattern_id, is_helpful)
                        )
                        success_count += 1

                    except Exception as e:
                        logger.error(f"Failed to record feedback for pattern {pattern_id}: {e}")
                        error_count += 1

                await conn.commit()

        return {
            "success": True,
            "total": len(feedbacks),
            "successful": success_count,
            "failed": error_count
        }

    except Exception as e:
        logger.error(f"Bulk feedback failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Bulk feedback failed: {str(e)}"
        )
