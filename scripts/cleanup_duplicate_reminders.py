"""Emergency cleanup script for duplicate reminders"""
import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.connection import db
from src.db.queries import find_duplicate_reminders, deactivate_duplicate_reminders

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def main():
    """Run duplicate cleanup"""
    try:
        # Initialize database
        logger.info("Initializing database connection...")
        await db.init_pool()

        # Find duplicates
        logger.info("\nSearching for duplicate reminders...")
        duplicates = await find_duplicate_reminders()

        if not duplicates:
            logger.info("✅ No duplicates found! Your reminder database is clean.")
            return

        # Show duplicates
        logger.info(f"\n⚠️  Found {len(duplicates)} groups of duplicates:\n")
        logger.info("=" * 80)

        total_duplicates = 0
        for dup in duplicates:
            duplicate_count = dup['duplicate_count']
            total_duplicates += (duplicate_count - 1)  # Don't count the one we'll keep

            logger.info(
                f"\nUser: {dup['user_id']}\n"
                f"  Message: {dup['message']}\n"
                f"  Time: {dup['time']} {dup['timezone']}\n"
                f"  Copies: {duplicate_count}x\n"
                f"  Keep: {dup['keep_id']}\n"
                f"  Remove: {len(dup['remove_ids'])} duplicates"
            )

        logger.info("=" * 80)
        logger.info(
            f"\nSummary:\n"
            f"  - Duplicate groups: {len(duplicates)}\n"
            f"  - Total reminders to deactivate: {total_duplicates}\n"
            f"  - Reminders to keep: {len(duplicates)}"
        )

        # Confirm
        print("\n" + "=" * 80)
        response = input("\n⚠️  Deactivate duplicate reminders? (yes/no): ").strip().lower()

        if response != "yes":
            logger.info("❌ Cancelled - no changes made")
            return

        # Clean up
        logger.info("\n🧹 Cleaning up duplicates...")
        result = await deactivate_duplicate_reminders()

        logger.info(
            f"\n✅ Cleanup complete!\n"
            f"   - Checked: {result['checked']} reminders\n"
            f"   - Deactivated: {result['deactivated']} duplicates\n"
            f"   - Kept: {result['groups']} original reminders\n"
        )

        logger.info(
            "\n⚠️  IMPORTANT: Restart the bot to reload the job queue!\n"
            "   Without restart, scheduled jobs may still send duplicate notifications.\n"
        )

    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}", exc_info=True)
        sys.exit(1)

    finally:
        await db.close_pool()
        logger.info("Database connection closed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n❌ Interrupted by user")
        sys.exit(1)
