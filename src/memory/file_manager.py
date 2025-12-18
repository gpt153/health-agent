"""Memory file management for user data"""
import logging
from pathlib import Path
from src.config import DATA_PATH
from src.memory.templates import (
    PROFILE_TEMPLATE,
    PREFERENCES_TEMPLATE,
    PATTERNS_TEMPLATE,
    FOOD_HISTORY_TEMPLATE,
    VISUAL_PATTERNS_TEMPLATE
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
        """Create default memory files for new user"""
        user_dir = self.get_user_dir(telegram_id)
        user_dir.mkdir(parents=True, exist_ok=True)

        files = {
            "profile.md": PROFILE_TEMPLATE,
            "preferences.md": PREFERENCES_TEMPLATE,
            "patterns.md": PATTERNS_TEMPLATE,
            "food_history.md": FOOD_HISTORY_TEMPLATE,
            "visual_patterns.md": VISUAL_PATTERNS_TEMPLATE
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
        """Load all memory files for user"""
        user_dir = self.get_user_dir(telegram_id)
        if not user_dir.exists():
            await self.create_user_files(telegram_id)

        return {
            "profile": await self.read_file(telegram_id, "profile.md"),
            "preferences": await self.read_file(telegram_id, "preferences.md"),
            "patterns": await self.read_file(telegram_id, "patterns.md"),
            "food_history": await self.read_file(telegram_id, "food_history.md"),
            "visual_patterns": await self.read_file(telegram_id, "visual_patterns.md")
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

    async def add_visual_pattern(self, telegram_id: str, item_name: str, description: str) -> None:
        """Add or update a visual pattern in visual_patterns.md"""
        content = await self.read_file(telegram_id, "visual_patterns.md")

        # Create pattern entry
        pattern_entry = f"- **{item_name}**: {description}\n"

        lines = content.split("\n")
        updated = False

        # Look for existing entry with same item_name
        for i, line in enumerate(lines):
            if line.startswith(f"- **{item_name}**:"):
                lines[i] = pattern_entry.rstrip()
                updated = True
                break

        if not updated:
            # Find the "## Known Foods & Items" section and add after it
            for i, line in enumerate(lines):
                if line.startswith("## Known Foods & Items"):
                    # Skip the description line and any blank lines
                    insert_pos = i + 1
                    while insert_pos < len(lines) and (
                        lines[insert_pos].startswith("(") or lines[insert_pos].strip() == ""
                    ):
                        insert_pos += 1
                    # Insert after section header
                    lines.insert(insert_pos, pattern_entry.rstrip())
                    break

        await self.write_file(telegram_id, "visual_patterns.md", "\n".join(lines))
        logger.info(f"Added visual pattern '{item_name}' for user {telegram_id}")

    async def save_observation(self, telegram_id: str, category: str, information: str) -> None:
        """Save any user observation/information to patterns.md"""
        content = await self.read_file(telegram_id, "patterns.md")

        lines = content.split("\n")

        # Find or create the category section
        section_header = f"## {category}"
        section_exists = False
        insert_pos = -1

        for i, line in enumerate(lines):
            if line.strip() == section_header:
                section_exists = True
                insert_pos = i + 1
                # Skip to next section or end
                while insert_pos < len(lines) and not lines[insert_pos].startswith("##"):
                    insert_pos += 1
                break

        # If section doesn't exist, add it before "## Notes"
        if not section_exists:
            for i, line in enumerate(lines):
                if line.startswith("## Notes"):
                    insert_pos = i
                    lines.insert(insert_pos, "")
                    lines.insert(insert_pos, f"- {information}")
                    lines.insert(insert_pos, section_header)
                    break
        else:
            # Add to existing section
            lines.insert(insert_pos, f"- {information}")

        await self.write_file(telegram_id, "patterns.md", "\n".join(lines))
        logger.info(f"Saved observation to '{category}' for user {telegram_id}")


# Global instance
memory_manager = MemoryFileManager()
