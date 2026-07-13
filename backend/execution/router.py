"""Execution API — public surface for the Execution Runtime.
Endpoints: connection status, tool listing, plan execution.
Uses composio CLI under the hood — one binary, no SDK deps.
"""
import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from security import current_user, now_utc
from db import members_col, orgs_col

from .mcp_client import (
    list_tools, search_tools, call_tool, mcp_enabled,
    tools_for_department, tools_for_founder,
    is_connected, linked_toolkits,
)
from .dispatcher import execute_plan, validate_plan
from .collector import collect_execution_result

log = logging.getLogger("execution.router")
router = APIRouter(prefix="/api/execution")


def _active_membership(user: dict) -> Optional[dict]:
    return members_col.find_one({"user_id": user["id"], "status": "active"})


def _org_for_user(user: dict) -> Optional[str]:
    m = _active_membership(user)
    return m["org_id"] if m else None


def _department_for_user(user: dict) -> str:
    return (user.get("function") or "general")


@router.get("/status")
def execution_status(user: dict = Depends(current_user)):
    """MCP health: CLI installed? logged in? toolkits connected?"""
    if not mcp_enabled():
        return {"mcp_enabled": False, "message": "Install composio CLI: curl -fsSL https://composio.dev/install | bash"}

    connected = is_connected()
    toolkits = linked_toolkits() if connected else []
    tools = list_tools() if connected else []

    return {
        "mcp_enabled": True,
        "cli_installed": True,
        "authenticated": connected,
        "connected_toolkits": toolkits,
        "tools_available": len(tools),
    }


@router.get("/tools")
def get_tools(query: Optional[str] = None, user: dict = Depends(current_user)):
    """List tools available to this user's department."""
    if not mcp_enabled():
        return {"tools": [], "mcp_enabled": False}

    if not is_connected():
        return {"tools": [], "mcp_enabled": True, "authenticated": False}

    m = _active_membership(user)
    if m and m.get("role") == "owner":
        tools = tools_for_founder()
    else:
        tools = tools_for_department(_department_for_user(user))

    if query:
        tools = search_tools(query)

    return {"tools": tools, "count": len(tools), "mcp_enabled": True, "authenticated": True}


@router.post("/execute")
def execute(body: dict, user: dict = Depends(current_user)):
    """Execute a plan of tool calls. Owner-only."""
    if not mcp_enabled():
        raise HTTPException(503, "MCP disabled")
    if not is_connected():
        raise HTTPException(412, "Not authenticated. Run 'composio login'")

    m = _active_membership(user)
    if not m:
        raise HTTPException(403, "Not in an organization")
    if m["role"] != "owner":
        raise HTTPException(403, "Only workspace owner")

    plan = body.get("plan", body)
    if not plan.get("actions"):
        raise HTTPException(422, "Plan must contain 'actions' array")

    issues = validate_plan(plan)
    if issues:
        return {"status": "rejected", "issues": issues}

    result = execute_plan(plan, _department_for_user(user))
    return {
        "execution_id": "exec_" + uuid.uuid4().hex[:16],
        "status": "completed",
        "actions": result["actions"],
        "summary": result["summary"],
    }


@router.post("/tools/{tool_name}")
def execute_single_tool(tool_name: str, body: dict, user: dict = Depends(current_user)):
    """Execute a single tool."""
    if not mcp_enabled():
        raise HTTPException(503, "MCP disabled")
    if not is_connected():
        raise HTTPException(412, "Not authenticated")

    m = _active_membership(user)
    if not m:
        raise HTTPException(403, "Not in an organization")
    if m["role"] != "owner":
        raise HTTPException(403, "Only workspace owner")

    result = call_tool(tool_name, body.get("args", {}))

    return {
        "tool": tool_name,
        "result": result.get("result", "")[:2000],
        "successful": result.get("successful", False),
        "elapsed_ms": result.get("execution_time_ms", 0),
    }


@router.get("/toolkits")
def get_linked_toolkits(user: dict = Depends(current_user)):
    """List connected toolkits (Gmail, GitHub, etc)."""
    if not mcp_enabled() or not is_connected():
        return {"toolkits": [], "authenticated": False}
    return {"toolkits": linked_toolkits(), "authenticated": True}
