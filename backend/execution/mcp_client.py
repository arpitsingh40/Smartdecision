"""Composio MCP client via CLI — infrastructure, not architecture.
Uses the composio CLI binary for auth, tool listing, and execution.
The CLI handles OAuth natively — no API key, no SDK deps.

CLI must be installed: curl -fsSL https://composio.dev/install | bash
Then: composio login (once), composio link <toolkit> (per app)
"""
import os
import json
import time
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

log = logging.getLogger("execution.mcp")

COMPOSIO_BIN = os.path.expanduser(os.environ.get("COMPOSIO_BIN", "~/.composio/composio"))
MCP_REQUEST_TIMEOUT = int(os.environ.get("MCP_REQUEST_TIMEOUT", "30"))
DISABLE_MCP = bool(os.environ.get("DISABLE_MCP"))

_tool_registry: list = []
_tool_cache_at: Optional[float] = None
_toolkit_cache: list = []
_toolkit_cache_at: Optional[float] = None
TOOL_CACHE_TTL = int(os.environ.get("MCP_TOOL_CACHE_TTL", "300"))


def mcp_enabled() -> bool:
    if DISABLE_MCP:
        return False
    return os.path.isfile(COMPOSIO_BIN)


def is_connected(org_id: str = None) -> bool:
    """Check if CLI is authenticated."""
    if not mcp_enabled():
        return False
    try:
        result = subprocess.run([COMPOSIO_BIN, "whoami"], capture_output=True, text=True,
                                stdin=subprocess.DEVNULL, timeout=15)
        return result.returncode == 0 and "email" in result.stdout
    except Exception:
        return False


def _run(args: list, timeout: int = None) -> dict:
    """Run a composio CLI command and parse JSON output."""
    if not mcp_enabled():
        return {"error": "MCP disabled — install composio CLI"}
    try:
        result = subprocess.run(
            [COMPOSIO_BIN] + args,
            capture_output=True, text=True,
            stdin=subprocess.DEVNULL,
            timeout=timeout or MCP_REQUEST_TIMEOUT
        )
        stdout = result.stdout.strip()
        if result.returncode != 0:
            err = result.stderr.strip() or stdout or "unknown error"
            if err:
                log.warning(f"composio CLI error: {' '.join(args)} -> {err[:200]}")
                return {"error": err[:500]}
        if not stdout:
            return {"error": "empty output"}
        return json.loads(stdout)
    except subprocess.TimeoutExpired:
        return {"error": "CLI timeout"}
    except json.JSONDecodeError:
        return {"error": f"CLI output not JSON: {result.stdout[:300]}", "raw": result.stdout}
    except Exception as e:
        return {"error": str(e)[:500]}


def list_tools(refresh: bool = False, toolkit: str = None, org_id: str = None) -> list:
    """List tools. Optionally filter by toolkit (gmail, github, etc).
    If no toolkit specified, aggregates from all connected toolkits."""
    global _tool_registry, _tool_cache_at
    now = time.time()
    if not refresh and _tool_registry and _tool_cache_at and (now - _tool_cache_at < TOOL_CACHE_TTL):
        return _tool_registry

    if toolkit:
        result = _run(["tools", "list", toolkit])
    else:
        # ponytail: aggregate from connected toolkits; search requires a query
        tks = linked_toolkits()
        all_tools = []
        for tk in tks:
            tk_result = _run(["tools", "list", tk["toolkit"]])
            if "error" not in tk_result:
                items = tk_result if isinstance(tk_result, list) else []
                all_tools.extend(items)
        result = all_tools

    if isinstance(result, dict) and result.get("error"):
        log.warning(f"tools/list: {result['error']}")
        return _tool_registry

    tools = result if isinstance(result, list) else result.get("items", result.get("tools", []))
    _tool_registry = [{"name": t.get("slug", t.get("name", "")),
                        "description": (t.get("description") or "")[:300],
                        "inputSchema": t.get("input_schema", t.get("parameters", {}))}
                       for t in tools if isinstance(t, dict)]
    _tool_cache_at = now
    log.info(f"MCP tools: {len(_tool_registry)}")
    return _tool_registry


def search_tools(query: str, limit: int = 10, org_id: str = None) -> list:
    if not mcp_enabled():
        return []
    result = _run(["search", query])
    if "error" in result:
        return []
    tools = result if isinstance(result, list) else result.get("items", result.get("tools", []))
    out = [{"name": t.get("slug", t.get("name", "")),
            "description": (t.get("description") or "")[:200]}
           for t in tools[:limit] if isinstance(t, dict)]
    return out


def call_tool(tool_name: str, arguments: dict, org_id: str = None) -> dict:
    """Execute a tool via composio CLI. Returns {result, successful, execution_time_ms}."""
    if not mcp_enabled():
        return {"error": "MCP disabled", "successful": False}

    args_json = json.dumps(arguments, ensure_ascii=False)
    t0 = time.time()
    result = _run(["execute", tool_name, "-d", args_json], timeout=60)
    elapsed_ms = round((time.time() - t0) * 1000)

    if result.get("error"):
        return {"error": str(result["error"]), "execution_time_ms": elapsed_ms, "successful": False}

    # CLI may return data inline or via output file
    output_file = result.get("outputFilePath", "")
    if output_file and os.path.isfile(output_file):
        try:
            with open(output_file, "r") as f:
                file_data = json.load(f)
            actual = file_data.get("data", file_data)
        except Exception:
            actual = result
    else:
        actual = result.get("data", result)

    # Extract useful text from result
    if isinstance(actual, dict):
        msgs = actual.get("messages", actual.get("items", []))
        if msgs:
            previews = []
            for m in msgs[:5]:
                if isinstance(m, dict):
                    previews.append(f"- {m.get('subject', m.get('name', ''))}: {(m.get('preview',{}).get('body','') or m.get('messageText',''))[:120]}")
            actual = "\n".join(previews) if previews else json.dumps(actual, ensure_ascii=False)

    return {
        "result": str(actual)[:5000] if actual else "(empty response)",
        "execution_time_ms": elapsed_ms,
        "successful": result.get("successful", True),
    }


def linked_toolkits() -> list:
    """List all connected toolkits (Gmail, GitHub, etc). Cached for 5 minutes."""
    global _toolkit_cache, _toolkit_cache_at
    now = time.time()
    if _toolkit_cache and _toolkit_cache_at and (now - _toolkit_cache_at < 300):
        return _toolkit_cache

    if not mcp_enabled():
        return []
    toolkits = []
    for tk in ["gmail", "github", "slack", "notion", "calendar", "sheets"]:
        result = _run(["link", tk, "--list"], timeout=10)
        if isinstance(result, dict) and not result.get("error"):
            items = result.get("items", [])
            if items:
                toolkits.append({"toolkit": tk, "connections": len(items)})
    _toolkit_cache = toolkits
    _toolkit_cache_at = now
    return toolkits


DEPARTMENT_TOOL_SCOPE = {
    "sales": ["gmail", "hubspot", "linkedin", "calendar", "stripe"],
    "marketing": ["gmail", "linkedin", "twitter", "youtube", "notion"],
    "engineering": ["github", "gitlab", "vercel", "aws", "jira", "slack"],
    "product": ["github", "jira", "notion", "slack", "linear"],
    "operations": ["gmail", "notion", "jira", "slack", "calendar"],
    "finance": ["stripe", "quickbooks", "gmail", "sheets"],
    "leadership": [],
    "general": ["gmail", "calendar", "notion"],
}


def tools_for_department(function: str, org_id: str = None) -> list:
    scope = DEPARTMENT_TOOL_SCOPE.get(function, [])
    if not scope:
        return list_tools()
    all_tools = list_tools()
    return [t for t in all_tools if any(t["name"].lower().startswith(prefix) for prefix in scope)]


def tools_for_founder(org_id: str = None) -> list:
    return list_tools()
