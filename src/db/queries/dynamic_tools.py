"""Dynamic tool management database queries"""
import json
import logging
from typing import Optional
from datetime import datetime
from src.db.connection import db

logger = logging.getLogger(__name__)


# ==========================================
# Dynamic Tools Functions
# ==========================================

async def save_dynamic_tool(
    tool_name: str,
    tool_type: str,
    description: str,
    parameters_schema: dict,
    return_schema: dict,
    function_code: str,
    created_by: str = "system"
) -> str:
    """
    Save a new dynamic tool to database

    Args:
        tool_name: Unique tool name (e.g., 'get_weekly_calories')
        tool_type: 'read' or 'write'
        description: Human-readable description
        parameters_schema: JSON Schema for function parameters
        return_schema: JSON Schema for return type
        function_code: Python function code as string
        created_by: Creator ID (default: 'system')

    Returns:
        Tool UUID as string
    """
    from uuid import uuid4
    tool_id = str(uuid4())

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO dynamic_tools
                (id, tool_name, tool_type, description, parameters_schema,
                 return_schema, function_code, enabled, version, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    tool_id,
                    tool_name,
                    tool_type,
                    description,
                    json.dumps(parameters_schema),
                    json.dumps(return_schema),
                    function_code,
                    True,  # enabled
                    1,     # version
                    created_by
                )
            )

            # Save initial version to history
            await cur.execute(
                """
                INSERT INTO dynamic_tool_versions
                (tool_id, version, function_code, change_summary)
                VALUES (%s, %s, %s, %s)
                """,
                (tool_id, 1, function_code, "Initial creation")
            )

            await conn.commit()

    logger.info(f"Saved dynamic tool: {tool_name} (type: {tool_type}, id: {tool_id})")
    return tool_id


async def get_all_enabled_tools() -> list[dict]:
    """Get all enabled dynamic tools"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, tool_name, tool_type, description,
                       parameters_schema, return_schema, function_code,
                       version, created_at, last_used_at, usage_count
                FROM dynamic_tools
                WHERE enabled = true
                ORDER BY tool_name
                """
            )
            return await cur.fetchall()


async def get_tool_by_name(tool_name: str) -> Optional[dict]:
    """Get specific tool by name"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT * FROM dynamic_tools
                WHERE tool_name = %s
                """,
                (tool_name,)
            )
            return await cur.fetchone()


async def update_tool_version(
    tool_id: str,
    new_function_code: str,
    change_summary: str
) -> int:
    """
    Update tool code and increment version

    Returns:
        New version number
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Get current version
            await cur.execute(
                "SELECT version FROM dynamic_tools WHERE id = %s",
                (tool_id,)
            )
            row = await cur.fetchone()
            if not row:
                raise ValueError(f"Tool {tool_id} not found")

            new_version = row["version"] + 1

            # Update tool
            await cur.execute(
                """
                UPDATE dynamic_tools
                SET function_code = %s, version = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (new_function_code, new_version, tool_id)
            )

            # Save version history
            await cur.execute(
                """
                INSERT INTO dynamic_tool_versions
                (tool_id, version, function_code, change_summary)
                VALUES (%s, %s, %s, %s)
                """,
                (tool_id, new_version, new_function_code, change_summary)
            )

            await conn.commit()

    logger.info(f"Updated tool {tool_id} to version {new_version}")
    return new_version


async def disable_tool(tool_id: str) -> None:
    """Disable a tool (soft delete)"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE dynamic_tools SET enabled = false WHERE id = %s",
                (tool_id,)
            )
            await conn.commit()
    logger.info(f"Disabled tool {tool_id}")


async def enable_tool(tool_id: str) -> None:
    """Re-enable a disabled tool"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE dynamic_tools SET enabled = true WHERE id = %s",
                (tool_id,)
            )
            await conn.commit()
    logger.info(f"Enabled tool {tool_id}")


async def log_tool_execution(
    tool_id: str,
    user_id: str,
    parameters: dict,
    result: any,
    success: bool,
    error_message: Optional[str] = None,
    execution_time_ms: int = 0
) -> None:
    """Log tool execution for audit trail"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Log execution
            await cur.execute(
                """
                INSERT INTO dynamic_tool_executions
                (tool_id, user_id, parameters, result, success,
                 error_message, execution_time_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    tool_id,
                    user_id,
                    json.dumps(parameters),
                    json.dumps(result) if success else None,
                    success,
                    error_message,
                    execution_time_ms
                )
            )

            # Update tool usage stats
            if success:
                await cur.execute(
                    """
                    UPDATE dynamic_tools
                    SET usage_count = usage_count + 1,
                        last_used_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (tool_id,)
                )
            else:
                await cur.execute(
                    """
                    UPDATE dynamic_tools
                    SET error_count = error_count + 1
                    WHERE id = %s
                    """,
                    (tool_id,)
                )

            await conn.commit()


async def create_tool_approval_request(
    tool_id: str,
    requested_by: str,
    request_message: str
) -> str:
    """Create approval request for write tool"""
    from uuid import uuid4
    approval_id = str(uuid4())

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO dynamic_tool_approvals
                (id, tool_id, requested_by, request_message, status)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (approval_id, tool_id, requested_by, request_message, "pending")
            )
            await conn.commit()

    logger.info(f"Created approval request {approval_id} for tool {tool_id}")
    return approval_id


async def approve_tool(
    approval_id: str,
    admin_user_id: str
) -> None:
    """Approve a pending tool creation"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE dynamic_tool_approvals
                SET status = 'approved',
                    admin_user_id = %s,
                    admin_response_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (admin_user_id, approval_id)
            )
            await conn.commit()
    logger.info(f"Approved tool creation request {approval_id}")


async def reject_tool(
    approval_id: str,
    admin_user_id: str
) -> None:
    """Reject a pending tool creation"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE dynamic_tool_approvals
                SET status = 'rejected',
                    admin_user_id = %s,
                    admin_response_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (admin_user_id, approval_id)
            )
            await conn.commit()
    logger.info(f"Rejected tool creation request {approval_id}")


async def get_pending_approvals() -> list[dict]:
    """Get all pending tool approval requests"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT
                    a.id as approval_id,
                    a.tool_id,
                    a.requested_by,
                    a.request_message,
                    a.created_at,
                    t.tool_name,
                    t.tool_type,
                    t.description
                FROM dynamic_tool_approvals a
                JOIN dynamic_tools t ON a.tool_id = t.id
                WHERE a.status = 'pending'
                ORDER BY a.created_at DESC
                """
            )
            return await cur.fetchall()
