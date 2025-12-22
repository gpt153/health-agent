"""
Migrate user data from markdown files to PostgreSQL user_profiles table
"""
import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional

from src.config import DATA_PATH
from src.db.connection import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_markdown_field(content: str, field_name: str) -> Optional[str]:
    """Extract field value from markdown using pattern: - **Field**: Value"""
    pattern = rf"- \*\*{re.escape(field_name)}\*\*:\s*(.+)"
    match = re.search(pattern, content)
    return match.group(1).strip() if match else None


def parse_markdown_list(content: str, section_name: str) -> list[str]:
    """Extract list items from a markdown section"""
    items = []
    in_section = False

    for line in content.split('\n'):
        if f"## {section_name}" in line:
            in_section = True
            continue
        if in_section:
            if line.startswith('##'):  # New section
                break
            if line.strip().startswith('-'):
                item = line.strip().lstrip('-').strip()
                if item and not item.startswith('**'):
                    items.append(item)
            elif line.strip().startswith('*'):
                item = line.strip().lstrip('*').strip()
                if item:
                    items.append(item)

    return items


async def migrate_user_profile(user_dir: Path) -> Dict[str, Any]:
    """
    Migrate a single user's markdown files to PostgreSQL

    Returns:
        Dict with migration results
    """
    telegram_id = user_dir.name
    logger.info(f"Migrating user {telegram_id}...")

    # Initialize profile data
    profile_data = {}

    # Read profile.md
    profile_file = user_dir / "profile.md"
    if profile_file.exists():
        profile_content = profile_file.read_text()

        # Extract basic profile fields
        if name := parse_markdown_field(profile_content, "Name"):
            profile_data["name"] = name

        if age_str := parse_markdown_field(profile_content, "Age"):
            try:
                profile_data["age"] = int(age_str)
            except ValueError:
                logger.warning(f"Invalid age for {telegram_id}: {age_str}")

        if height_str := parse_markdown_field(profile_content, "Height"):
            try:
                # Extract number from string like "175 cm"
                height_match = re.search(r'(\d+\.?\d*)', height_str)
                if height_match:
                    profile_data["height_cm"] = float(height_match.group(1))
            except ValueError:
                logger.warning(f"Invalid height for {telegram_id}: {height_str}")

        if weight_str := parse_markdown_field(profile_content, "Current Weight"):
            try:
                weight_match = re.search(r'(\d+\.?\d*)', weight_str)
                if weight_match:
                    profile_data["current_weight_kg"] = float(weight_match.group(1))
            except ValueError:
                logger.warning(f"Invalid weight for {telegram_id}: {weight_str}")

        if target_weight_str := parse_markdown_field(profile_content, "Target Weight"):
            try:
                weight_match = re.search(r'(\d+\.?\d*)', target_weight_str)
                if weight_match:
                    profile_data["target_weight_kg"] = float(weight_match.group(1))
            except ValueError:
                logger.warning(f"Invalid target weight for {telegram_id}: {target_weight_str}")

        if goal := parse_markdown_field(profile_content, "Goal"):
            profile_data["goal_type"] = goal.lower().replace(" ", "_")

        # Extract allergies
        allergies = parse_markdown_list(profile_content, "Allergies")
        if allergies and allergies != ["None"]:
            profile_data["allergies"] = allergies

        # Extract health conditions
        conditions = parse_markdown_list(profile_content, "Health Conditions")
        if conditions and conditions != ["None"]:
            profile_data["health_conditions"] = conditions

        # Extract medications
        medications = parse_markdown_list(profile_content, "Medications")
        if medications and medications != ["None"]:
            profile_data["medications"] = medications

    # Read preferences.md
    preferences_file = user_dir / "preferences.md"
    if preferences_file.exists():
        pref_content = preferences_file.read_text()

        comm_prefs = {}

        if language := parse_markdown_field(pref_content, "Language"):
            profile_data["preferred_language"] = language.lower()[:2]  # e.g., "english" -> "en"

        if brevity := parse_markdown_field(pref_content, "Brevity"):
            comm_prefs["brevity"] = brevity.lower()

        if tone := parse_markdown_field(pref_content, "Tone"):
            comm_prefs["tone"] = tone.lower()

        if humor := parse_markdown_field(pref_content, "Humor"):
            comm_prefs["use_humor"] = humor.lower() in ("yes", "true", "enabled")

        if coaching := parse_markdown_field(pref_content, "Coaching Style"):
            profile_data["coaching_style"] = coaching.lower().replace(" ", "_")

        if daily := parse_markdown_field(pref_content, "Daily Summary"):
            comm_prefs["daily_summary"] = daily.lower() in ("yes", "true", "enabled")

        if checkins := parse_markdown_field(pref_content, "Proactive Check-ins"):
            comm_prefs["proactive_checkins"] = checkins.lower() in ("yes", "true", "enabled")

        # Extract dietary preferences
        dietary = parse_markdown_list(pref_content, "Dietary Preferences")
        if dietary and dietary != ["None"]:
            profile_data["dietary_preferences"] = dietary

        # Extract timezone
        if timezone := parse_markdown_field(pref_content, "Timezone"):
            # Normalize timezone string
            tz = timezone.strip()
            if '/' in tz or tz == 'UTC':
                profile_data["_timezone"] = tz  # Store separately, will go in timezone column

        if comm_prefs:
            profile_data["communication_preferences"] = comm_prefs

    # Read patterns.md
    patterns_file = user_dir / "patterns.md"
    if patterns_file.exists():
        patterns_content = patterns_file.read_text()

        # Extract exercise preferences
        exercise_patterns = parse_markdown_list(patterns_content, "Exercise Preferences")
        if exercise_patterns:
            profile_data["exercise_preferences"] = exercise_patterns

        # Extract sleep patterns
        sleep_patterns = parse_markdown_list(patterns_content, "Sleep Patterns")
        if sleep_patterns:
            profile_data["sleep_patterns"] = sleep_patterns

    # Save to PostgreSQL
    timezone = profile_data.pop("_timezone", "UTC")

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO user_profiles (telegram_id, profile_data, timezone)
                VALUES (%s, %s, %s)
                ON CONFLICT (telegram_id)
                DO UPDATE SET
                    profile_data = EXCLUDED.profile_data,
                    timezone = EXCLUDED.timezone,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (telegram_id, json.dumps(profile_data), timezone)
            )
            await conn.commit()

    logger.info(f"✅ Migrated {telegram_id}: {len(profile_data)} fields, timezone={timezone}")

    return {
        "telegram_id": telegram_id,
        "fields_migrated": len(profile_data),
        "timezone": timezone,
        "has_allergies": "allergies" in profile_data,
        "has_dietary_prefs": "dietary_preferences" in profile_data
    }


async def migrate_all_users(dry_run: bool = False):
    """
    Migrate all users from markdown to PostgreSQL

    Args:
        dry_run: If True, don't actually write to database
    """
    data_path = Path(DATA_PATH)

    if not data_path.exists():
        logger.warning(f"Data path does not exist: {data_path}")
        return

    # Initialize database
    await db.init_pool()

    user_dirs = [d for d in data_path.iterdir() if d.is_dir() and d.name.isdigit()]

    if not user_dirs:
        logger.info("No user directories found to migrate")
        return

    logger.info(f"Found {len(user_dirs)} user directories to migrate")

    results = []
    errors = []

    for user_dir in user_dirs:
        try:
            if dry_run:
                logger.info(f"[DRY RUN] Would migrate {user_dir.name}")
                continue

            result = await migrate_user_profile(user_dir)
            results.append(result)

        except Exception as e:
            logger.error(f"❌ Error migrating {user_dir.name}: {e}", exc_info=True)
            errors.append({"telegram_id": user_dir.name, "error": str(e)})

    # Print summary
    logger.info("\n" + "="*50)
    logger.info("MIGRATION SUMMARY")
    logger.info("="*50)
    logger.info(f"Total users: {len(user_dirs)}")
    logger.info(f"Successful: {len(results)}")
    logger.info(f"Errors: {len(errors)}")

    if results:
        total_fields = sum(r["fields_migrated"] for r in results)
        users_with_allergies = sum(1 for r in results if r["has_allergies"])
        users_with_dietary = sum(1 for r in results if r["has_dietary_prefs"])

        logger.info(f"\nTotal fields migrated: {total_fields}")
        logger.info(f"Users with allergies: {users_with_allergies}")
        logger.info(f"Users with dietary preferences: {users_with_dietary}")

        # Timezone distribution
        timezones = {}
        for r in results:
            tz = r["timezone"]
            timezones[tz] = timezones.get(tz, 0) + 1

        logger.info("\nTimezone distribution:")
        for tz, count in sorted(timezones.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {tz}: {count} users")

    if errors:
        logger.error("\nErrors encountered:")
        for error in errors:
            logger.error(f"  {error['telegram_id']}: {error['error']}")

    await db.close_pool()


async def verify_migration():
    """Verify that migration was successful"""
    await db.init_pool()

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Count profiles
            await cur.execute("SELECT COUNT(*) FROM user_profiles")
            profile_count = (await cur.fetchone())[0]

            # Count users
            await cur.execute("SELECT COUNT(*) FROM users")
            user_count = (await cur.fetchone())[0]

            # Find profiles with data
            await cur.execute(
                "SELECT COUNT(*) FROM user_profiles WHERE jsonb_array_length(jsonb_object_keys(profile_data)) > 0"
            )
            profiles_with_data = (await cur.fetchone())[0]

            # Sample profile
            await cur.execute(
                """
                SELECT telegram_id, profile_data, timezone
                FROM user_profiles
                WHERE profile_data != '{}'::jsonb
                LIMIT 1
                """
            )
            sample = await cur.fetchone()

    logger.info("\n" + "="*50)
    logger.info("MIGRATION VERIFICATION")
    logger.info("="*50)
    logger.info(f"Total users in database: {user_count}")
    logger.info(f"Total profiles created: {profile_count}")
    logger.info(f"Profiles with data: {profiles_with_data}")

    if sample:
        logger.info(f"\nSample profile ({sample[0]}):")
        logger.info(f"  Timezone: {sample[2]}")
        logger.info(f"  Data: {json.dumps(sample[1], indent=2)}")

    await db.close_pool()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate user data from markdown to PostgreSQL")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually write to database")
    parser.add_argument("--verify", action="store_true", help="Verify migration results")

    args = parser.parse_args()

    if args.verify:
        asyncio.run(verify_migration())
    else:
        asyncio.run(migrate_all_users(dry_run=args.dry_run))
