"""Tool catalog — loads composio_catalog.json for tool definitions.
Provides schemas for all 1,403 toolkits without needing the CLI.
"""

import json
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("execution.catalog")

_here = Path(__file__).parent
# Try Docker path first, then local path
CATALOG_PATH = _here.parent.parent / "memory" / "composio_catalog.json"
if not CATALOG_PATH.exists():
    CATALOG_PATH = _here.parent.parent.parent / "memory" / "composio_catalog.json"

_toolkits: dict = {}
_capabilities: dict = {}
_loaded = False


def _load():
    global _toolkits, _capabilities, _loaded
    if _loaded:
        return
    if not CATALOG_PATH.exists():
        log.warning(f"Catalog not found at {CATALOG_PATH}")
        _loaded = True
        return
    try:
        with open(CATALOG_PATH) as f:
            cat = json.load(f)
        _toolkits = {slug.lower(): tk for slug, tk in cat.get("toolkits", {}).items() if tk.get("tools")}
        for slug, tk in _toolkits.items():
            for tool in tk.get("tools", []):
                cap = (tk.get("category") or "General").lower().replace(" & ", "_").replace(" ", "_")
                tool["_toolkit"] = slug
                tool["_toolkit_name"] = tk.get("name", slug)
                tool["_capability"] = cap
                if cap not in _capabilities:
                    _capabilities[cap] = []
                _capabilities[cap].append(tool)
        _loaded = True
        log.info(f"Catalog loaded: {len(_toolkits)} toolkits, {sum(len(tk.get('tools',[])) for tk in _toolkits.values())} tools")
    except Exception as e:
        log.warning(f"Failed to load catalog: {e}")


def get_toolkits(refresh: bool = False) -> dict:
    _load()
    return _toolkits


def list_tools(toolkit: Optional[str] = None, limit: int = 50) -> list:
    _load()
    if toolkit:
        tk = _toolkits.get(toolkit.lower())
        if not tk:
            return []
        return [{
            "name": t["slug"],
            "description": (t.get("description") or "")[:300],
            "inputSchema": t.get("input_schema", t.get("parameters", {})),
            "toolkit": toolkit.lower(),
            "toolkit_name": tk.get("name", toolkit),
        } for t in (tk.get("tools") or [])[:limit]]

    result = []
    for slug, tk in _toolkits.items():
        for t in (tk.get("tools") or []):
            result.append({
                "name": t["slug"],
                "description": (t.get("description") or "")[:300],
                "inputSchema": t.get("input_schema", t.get("parameters", {})),
                "toolkit": slug,
                "toolkit_name": tk.get("name", slug),
            })
    return result


def search_tools(query: str, limit: int = 10) -> list:
    _load()
    q = query.lower()
    result = []
    for slug, tk in _toolkits.items():
        for t in (tk.get("tools") or []):
            if q in t["slug"].lower() or q in (t.get("description") or "").lower():
                result.append({
                    "name": t["slug"],
                    "description": (t.get("description") or "")[:300],
                    "inputSchema": t.get("input_schema", t.get("parameters", {})),
                    "toolkit": slug,
                    "toolkit_name": tk.get("name", slug),
                })
                if len(result) >= limit:
                    return result
    return result


def toolkits_with_handlers() -> list:
    from .handlers import registered_handlers
    return list(registered_handlers().keys())
