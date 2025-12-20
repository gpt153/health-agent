"""Integration tests for food entry correction workflow (GitHub issue #20)"""
import pytest
from datetime import datetime
from uuid import uuid4

from src.db.queries import save_food_entry, update_food_entry, get_food_entries_by_date
from src.models.food import FoodEntry, FoodItem, Macros


@pytest.mark.asyncio
async def test_food_entry_correction_workflow():
    """
    Test the complete food correction workflow:
    1. Log food entry
    2. Correct the entry
    3. Verify correction persists after simulated /clear

    This tests the fix for issue #20 where corrections were lost after /clear
    """
    user_id = f"test_user_{uuid4()}"

    # Step 1: Create initial food entry with incorrect calories (like the pizza example)
    initial_entry = FoodEntry(
        user_id=user_id,
        timestamp=datetime.now(),
        photo_path=None,
        foods=[
            FoodItem(
                name="3/8 Vesuvio pizza with kebab",
                quantity="3/8 pizza",
                calories=350,  # WRONG - user will correct this
                macros=Macros(protein=20, carbs=40, fat=10)
            )
        ],
        total_calories=350,
        total_macros=Macros(protein=20, carbs=40, fat=10),
        meal_type="lunch",
        notes="Initial entry - incorrect estimation"
    )

    await save_food_entry(initial_entry)

    # Step 2: Get the entry to verify it was saved
    entries = await get_food_entries_by_date(user_id)
    assert len(entries) == 1
    assert entries[0]["total_calories"] == 350
    entry_id = str(entries[0]["id"])

    # Step 3: User corrects the entry (simulates user saying "3/8 pizza should be ~1000 kcal")
    correction_result = await update_food_entry(
        entry_id=entry_id,
        user_id=user_id,
        total_calories=1000,  # CORRECTED value
        total_macros={"protein": 60, "carbs": 100, "fat": 40},
        correction_note="User corrected: 3/8 pizza is ~1000 kcal, not 350 kcal",
        corrected_by="user"
    )

    assert correction_result["success"] is True
    assert correction_result["old_values"]["total_calories"] == 350
    assert correction_result["new_values"]["total_calories"] == 1000

    # Step 4: Simulate /clear by just querying database again (no conversation history)
    # This simulates what happens after /clear - only database data is available
    entries_after_clear = await get_food_entries_by_date(user_id)

    # Step 5: Verify the corrected value persists
    assert len(entries_after_clear) == 1
    assert entries_after_clear[0]["total_calories"] == 1000  # Should be corrected value
    assert entries_after_clear[0]["correction_note"] == "User corrected: 3/8 pizza is ~1000 kcal, not 350 kcal"
    assert entries_after_clear[0]["corrected_by"] == "user"

    # Step 6: Verify macros also updated
    import json
    macros = entries_after_clear[0]["total_macros"]
    if isinstance(macros, str):
        macros = json.loads(macros)
    assert macros["protein"] == 60
    assert macros["carbs"] == 100
    assert macros["fat"] == 40


@pytest.mark.asyncio
async def test_update_food_entry_nonexistent():
    """Test that updating a non-existent entry returns error"""
    result = await update_food_entry(
        entry_id=str(uuid4()),
        user_id="nonexistent_user",
        total_calories=500,
        correction_note="Should fail"
    )

    assert result["success"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_update_food_entry_wrong_user():
    """Test that users can't update other users' entries"""
    # Create entry for user A
    user_a = f"test_user_a_{uuid4()}"
    user_b = f"test_user_b_{uuid4()}"

    entry = FoodEntry(
        user_id=user_a,
        timestamp=datetime.now(),
        photo_path=None,
        foods=[
            FoodItem(
                name="Test food",
                quantity="1 portion",
                calories=200,
                macros=Macros(protein=10, carbs=20, fat=5)
            )
        ],
        total_calories=200,
        total_macros=Macros(protein=10, carbs=20, fat=5),
        meal_type="snack"
    )

    await save_food_entry(entry)
    entries = await get_food_entries_by_date(user_a)
    entry_id = str(entries[0]["id"])

    # Try to update as user B
    result = await update_food_entry(
        entry_id=entry_id,
        user_id=user_b,  # Wrong user!
        total_calories=500,
        correction_note="Should fail - wrong user"
    )

    assert result["success"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_partial_update():
    """Test updating only calories without changing macros"""
    user_id = f"test_user_{uuid4()}"

    # Create entry
    entry = FoodEntry(
        user_id=user_id,
        timestamp=datetime.now(),
        photo_path=None,
        foods=[
            FoodItem(
                name="Food item",
                quantity="1 serving",
                calories=300,
                macros=Macros(protein=15, carbs=30, fat=10)
            )
        ],
        total_calories=300,
        total_macros=Macros(protein=15, carbs=30, fat=10),
        meal_type="breakfast"
    )

    await save_food_entry(entry)
    entries = await get_food_entries_by_date(user_id)
    entry_id = str(entries[0]["id"])

    # Update only calories
    result = await update_food_entry(
        entry_id=entry_id,
        user_id=user_id,
        total_calories=400,  # Change only this
        # macros not provided - should stay the same
        correction_note="Adjusted calories only"
    )

    assert result["success"] is True
    assert result["new_values"]["total_calories"] == 400

    # Verify macros stayed the same
    entries_after = await get_food_entries_by_date(user_id)
    import json
    macros = entries_after[0]["total_macros"]
    if isinstance(macros, str):
        macros = json.loads(macros)
    assert macros["protein"] == 15
    assert macros["carbs"] == 30
    assert macros["fat"] == 10


@pytest.mark.asyncio
async def test_audit_trail():
    """Test that food_entry_audit table logs all updates"""
    from src.db.connection import db

    user_id = f"test_user_{uuid4()}"

    # Create entry
    entry = FoodEntry(
        user_id=user_id,
        timestamp=datetime.now(),
        photo_path=None,
        foods=[
            FoodItem(
                name="Test",
                quantity="1",
                calories=100,
                macros=Macros(protein=5, carbs=10, fat=3)
            )
        ],
        total_calories=100,
        total_macros=Macros(protein=5, carbs=10, fat=3),
        meal_type="snack"
    )

    await save_food_entry(entry)
    entries = await get_food_entries_by_date(user_id)
    entry_id = str(entries[0]["id"])

    # Update entry
    await update_food_entry(
        entry_id=entry_id,
        user_id=user_id,
        total_calories=200,
        correction_note="Test correction"
    )

    # Check audit log
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT * FROM food_entry_audit
                WHERE food_entry_id = %s AND user_id = %s
                """,
                (entry_id, user_id)
            )
            audit_entries = await cur.fetchall()

    assert len(audit_entries) > 0
    audit = audit_entries[0]
    assert audit["action"] == "updated"
    assert audit["correction_note"] == "Test correction"

    # Verify old and new values are logged
    import json
    old_values = json.loads(audit["old_values"]) if isinstance(audit["old_values"], str) else audit["old_values"]
    new_values = json.loads(audit["new_values"]) if isinstance(audit["new_values"], str) else audit["new_values"]

    assert old_values["total_calories"] == 100
    assert new_values["total_calories"] == 200
