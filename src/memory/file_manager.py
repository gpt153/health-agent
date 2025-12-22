"""Memory file management for user data

MEMORY ARCHITECTURE:
- PostgreSQL: Structured data (food, reminders, XP, streaks, achievements)
- Markdown files: User-inspectable profile & preferences ONLY
- Mem0: Semantic search for unstructured patterns (optional)
"""
import logging
from pathlib import Path
from src.config import DATA_PATH
from src.memory.templates import (
    PROFILE_TEMPLATE,
    PREFERENCES_TEMPLATE
)

logger = logging.getLogger(__name__)


class MemoryFileManager:
    """Manage user memory markdown files"""

    def __init__(self, data_path: Path = DATA_PATH):
        self.data_path = data_path

    def get_user_dir(self, telegram_id: str) -> Path:
        """Get user's memory directory"""
        return self.data_path / telegram_id

    async def create_user_files(self, telegram_id: str) -> None:
        """Create default memory files for new user

        Only creates profile.md and preferences.md.
        Other data lives in PostgreSQL (food, reminders, XP) or Mem0 (patterns).
        """
        user_dir = self.get_user_dir(telegram_id)
        user_dir.mkdir(parents=True, exist_ok=True)

        files = {
            "profile.md": PROFILE_TEMPLATE,
            "preferences.md": PREFERENCES_TEMPLATE
        }

        for filename, template in files.items():
            filepath = user_dir / filename
            if not filepath.exists():
                filepath.write_text(template)
                logger.info(f"Created {filename} for user {telegram_id}")

    async def read_file(self, telegram_id: str, filename: str) -> str:
        """Read a memory file"""
        filepath = self.get_user_dir(telegram_id) / filename
        if not filepath.exists():
            await self.create_user_files(telegram_id)
        return filepath.read_text()

    async def write_file(self, telegram_id: str, filename: str, content: str) -> None:
        """Write to a memory file"""
        filepath = self.get_user_dir(telegram_id) / filename
        filepath.write_text(content)
        logger.info(f"Updated {filename} for user {telegram_id}")

    async def load_user_memory(self, telegram_id: str) -> dict:
        """Load all memory files for user

        Only loads profile and preferences from markdown files.
        Food history comes from PostgreSQL, patterns from Mem0.
        """
        user_dir = self.get_user_dir(telegram_id)
        if not user_dir.exists():
            await self.create_user_files(telegram_id)

        return {
            "profile": await self.read_file(telegram_id, "profile.md"),
            "preferences": await self.read_file(telegram_id, "preferences.md")
        }

    async def update_profile(self, telegram_id: str, field: str, value: str) -> None:
        """Update a profile field in profile.md"""
        content = await self.read_file(telegram_id, "profile.md")

        # Simple markdown update - append or update field
        field_line = f"- **{field}**: {value}\n"

        # Check if field exists and update, otherwise append
        lines = content.split("\n")
        updated = False
        for i, line in enumerate(lines):
            if line.startswith(f"- **{field}**:"):
                lines[i] = field_line.rstrip()
                updated = True
                break

        if not updated:
            # Append to end
            lines.append(field_line.rstrip())

        await self.write_file(telegram_id, "profile.md", "\n".join(lines))
        logger.info(f"Updated profile field {field} for user {telegram_id}")

    async def update_preferences(self, telegram_id: str, preference: str, value: str) -> None:
        """Update a preference in preferences.md"""
        content = await self.read_file(telegram_id, "preferences.md")

        # Simple markdown update
        pref_line = f"- **{preference}**: {value}\n"

        # Check if preference exists and update, otherwise append
        lines = content.split("\n")
        updated = False
        for i, line in enumerate(lines):
            if line.startswith(f"- **{preference}**:"):
                lines[i] = pref_line.rstrip()
                updated = True
                break

        if not updated:
            # Append to end
            lines.append(pref_line.rstrip())

        await self.write_file(telegram_id, "preferences.md", "\n".join(lines))
        logger.info(f"Updated preference {preference} for user {telegram_id}")



# Global instance
memory_manager = MemoryFileManager()
