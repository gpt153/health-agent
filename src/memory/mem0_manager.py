"""Mem0 memory manager with PostgreSQL+pgvector backend"""
import logging
import os
from typing import Optional, List, Dict, Any
from mem0 import Memory

logger = logging.getLogger(__name__)


class Mem0Manager:
    """
    Manages semantic memory using Mem0 OSS with PostgreSQL+pgvector backend

    This provides:
    - Automatic fact extraction from conversations
    - Semantic search for relevant context
    - Long-term memory storage beyond 20-message window
    """

    def __init__(self):
        """Initialize Mem0Manager (actual initialization happens on first use)"""
        self.memory: Optional[Memory] = None
        self._initialized = False

    def _ensure_initialized(self):
        """Ensure Mem0 is initialized (lazy initialization)"""
        if self._initialized:
            return

        try:
            # Get database connection details from env
            db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/health_agent")
            openai_key = os.getenv("OPENAI_API_KEY")

            if not openai_key:
                raise ValueError("OPENAI_API_KEY required for embeddings")

            # Parse database URL
            # Format: postgresql://user:pass@host:port/dbname
            parts = db_url.replace("postgresql://", "").split("@")
            user_pass = parts[0].split(":")
            host_port_db = parts[1].split("/")
            host_port = host_port_db[0].split(":")

            config = {
                "vector_store": {
                    "provider": "pgvector",
                    "config": {
                        "host": host_port[0],
                        "port": int(host_port[1]),
                        "user": user_pass[0],
                        "password": user_pass[1],
                        "dbname": host_port_db[1],
                    }
                },
                "embedder": {
                    "provider": "openai",
                    "config": {
                        "model": "text-embedding-3-small",
                        "api_key": openai_key
                    }
                },
                "version": "v1.1"  # Use latest Mem0 version
            }

            self.memory = Memory.from_config(config)
            self._initialized = True
            logger.info("✅ Mem0 initialized successfully with PostgreSQL+pgvector backend")

        except Exception as e:
            logger.error(f"❌ Failed to initialize Mem0: {e}")
            self.memory = None
            self._initialized = False

    def add_message(self, user_id: str, message: str, role: str = "user", metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a message to memory for automatic fact extraction

        Args:
            user_id: User's telegram ID
            message: The message content
            role: Message role (user/assistant)
            metadata: Optional metadata (timestamp, message_type, etc.)
        """
        self._ensure_initialized()

        if not self.memory:
            logger.warning("Mem0 not initialized, skipping add_message")
            return

        try:
            # Mem0 will automatically extract facts from this message
            self.memory.add(
                messages=[{"role": role, "content": message}],
                user_id=user_id,
                metadata=metadata or {}
            )
            logger.debug(f"Added message to Mem0 for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to add message to Mem0: {e}")

    def search(self, user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search user's memory for relevant context

        Args:
            user_id: User's telegram ID
            query: Search query
            limit: Maximum number of results

        Returns:
            List of relevant memory items with their content and metadata
        """
        self._ensure_initialized()

        if not self.memory:
            logger.warning("Mem0 not initialized, returning empty results")
            return []

        try:
            results = self.memory.search(
                query=query,
                user_id=user_id,
                limit=limit
            )
            logger.debug(f"Found {len(results)} memories for query: {query}")
            return results

        except Exception as e:
            logger.error(f"Failed to search Mem0: {e}")
            return []

    def get_all_memories(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all memories for a user

        Args:
            user_id: User's telegram ID

        Returns:
            List of all memory items for this user
        """
        self._ensure_initialized()

        if not self.memory:
            logger.warning("Mem0 not initialized, returning empty results")
            return []

        try:
            memories = self.memory.get_all(user_id=user_id)
            logger.debug(f"Retrieved {len(memories)} total memories for user {user_id}")
            return memories

        except Exception as e:
            logger.error(f"Failed to get all memories from Mem0: {e}")
            return []

    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a specific memory by ID

        Args:
            memory_id: The ID of the memory to delete

        Returns:
            True if successful, False otherwise
        """
        self._ensure_initialized()

        if not self.memory:
            logger.warning("Mem0 not initialized")
            return False

        try:
            self.memory.delete(memory_id=memory_id)
            logger.info(f"Deleted memory {memory_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False


# Global instance
mem0_manager = Mem0Manager()
