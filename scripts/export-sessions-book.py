import sqlite3
import json
import os
import re
from datetime import datetime, timezone

# Paths to the OpenCode SQLite DB and output markdown
DB_PATH = os.path.expanduser("~/.local/share/opencode/opencode.db")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "book-of-sessions.md")

# Display labels for each agent type
AGENT_LABELS = {
    "build": "Build",
    "explore": "Explore",
    "plan": "Plan",
    "general": "General",
}

AGENT_ORDER = ["build", "explore", "plan", "general"]


# Open the OpenCode database read-only
def connect_db():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"OpenCode database not found at {DB_PATH}")
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


# Fetch all sessions ordered by creation time
def fetch_sessions(cursor):
    rows = cursor.execute("""
        SELECT
            s.id, s.title, s.agent, s.parent_id, s.time_created,
            s.time_updated, s.model, s.cost,
            s.tokens_input, s.tokens_output, s.tokens_reasoning,
            s.summary_additions, s.summary_deletions, s.summary_files,
            s.summary_diffs, s.directory, s.slug
        FROM session s
        ORDER BY s.time_created
    """).fetchall()
    return [dict(r) for r in rows]


# Fetch messages for a single session
def fetch_messages(cursor, session_id):
    rows = cursor.execute("""
        SELECT id, session_id, time_created, data
        FROM message
        WHERE session_id = ?
        ORDER BY time_created, rowid
    """, (session_id,)).fetchall()
    return [dict(r) for r in rows]


# Fetch message parts for a single message
def fetch_parts(cursor, message_id):
    rows = cursor.execute("""
        SELECT id, message_id, time_created, data
        FROM part
        WHERE message_id = ?
        ORDER BY time_created, rowid
    """, (message_id,)).fetchall()
    return [dict(r) for r in rows]


# Split sessions into roots and parent-to-children map
def build_tree(sessions):
    children_map = {}
    root_sessions = []
    for s in sessions:
        pid = s["parent_id"]
        if pid:
            children_map.setdefault(pid, []).append(s)
        else:
            root_sessions.append(s)
    return root_sessions, children_map


# Format millisecond timestamp as UTC date
def fmt_date(ts_ms):
    if not ts_ms:
        return "N/A"
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M UTC")


# Parse model JSON into a display name
def fmt_model(model_json):
    if not model_json:
        return "Unknown"
    try:
        m = json.loads(model_json)
        return m.get("modelID", m.get("id", "Unknown"))
    except (json.JSONDecodeError, TypeError):
        return str(model_json)[:40]


# Build a markdown anchor slug from text
def anchor(text):
    slug = text.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    return slug[:60]


def escape_headings(text):
    """Escape markdown headings in assistant text to prevent structure breakage."""
    lines = text.split("\n")
    result = []
    for line in lines:
        stripped = line.lstrip()
        if re.match(r"^#{1,6}\s", stripped):
            result.append("\\" + line)
        else:
            result.append(line)
    return "\n".join(result)


# Render one message part to markdown
def render_part(part, heading_level=6):
    data = json.loads(part["data"])
    typ = data.get("type")
    lines = []

    if typ == "text":
        text = data.get("text", "")
        text = escape_headings(text)
        lines.append(f"{text}\n")

    elif typ == "reasoning":
        text = data.get("text", "")
        text = escape_headings(text)
        lines.append(f"<details>")
        lines.append(f"<summary>💭 Reasoning</summary>")
        lines.append(f"\n{text}\n")
        lines.append(f"</details>\n")

    elif typ == "tool":
        tool_name = data.get("tool", "unknown")
        state = data.get("state", {})
        status = state.get("status", "unknown")
        inp = state.get("input", {})
        output = state.get("output", "")

        lines.append(f"> **Tool: {tool_name}** ({status})")
        if inp:
            inp_str = json.dumps(inp, indent=2) if isinstance(inp, dict) else str(inp)
            inp_str = inp_str.replace("```", "\\`\\`\\`")
            lines.append(f"```json")
            lines.append(f"{inp_str}")
            lines.append(f"```")
        if output:
            out_str = str(output)
            if len(out_str) > 2000:
                out_str = out_str[:2000] + "\n... (truncated)"
            out_str = out_str.replace("```", "\\`\\`\\`")
            lines.append(f"```")
            lines.append(f"{out_str}")
            lines.append(f"```")
        lines.append("")

    elif typ == "patch":
        files = data.get("files", [])
        lines.append(f"> **Patch:** {', '.join(files)}\n")

    elif typ == "compaction":
        pass

    return "\n".join(lines)


# Render a message with its parts
def render_message(msg, session_level):
    data = json.loads(msg["data"])
    role = data.get("role", "unknown")
    lines = []

    parts = fetch_parts(db_cursor, msg["id"])
    msg_h = "#" * (session_level + 2)

    if role == "user":
        lines.append(f"\n{msg_h} 🧑 You")
        lines.append(f"*{fmt_date(msg['time_created'])}*\n")
        for p in parts:
            pd = json.loads(p["data"])
            if pd.get("type") == "text":
                text = escape_headings(pd["text"])
                lines.append(f"> {text}\n")
                break

    elif role == "assistant":
        tokens = data.get("tokens") or {}
        cost = data.get("cost") or 0
        model = data.get("modelID", "")
        tok_total = tokens.get("total") if isinstance(tokens, dict) else None
        tok_str = f"*{tok_total or '?'} tokens*"
        if cost:
            tok_str += f", ${cost:.6f}"
        lines.append(f"\n{msg_h} 🤖 Assistant ({model})")
        lines.append(f"{tok_str}\n")

        for p in parts:
            pdata = json.loads(p["data"])
            ptype = pdata.get("type")
            if ptype in ("step-start", "step-finish"):
                continue
            lines.append(render_part(p))

    return "\n".join(lines)


# Render a session and recurse into children
def render_session(session, children_map, level):
    lines = []
    heading = "#" * level
    title = session["title"] or "Untitled Session"
    aid = anchor(title)

    lines.append(f"\n{heading} {title} {{#{aid}}}\n")

    created = fmt_date(session.get("time_created"))
    tokens = (session.get("tokens_input") or 0) + (session.get("tokens_output") or 0)
    cost = session.get("cost") or 0
    additions = session.get("summary_additions") or 0
    deletions = session.get("summary_deletions") or 0
    files_changed = session.get("summary_files") or 0
    model_id = fmt_model(session.get("model"))
    agent = session.get("agent", "")
    agent_label = AGENT_LABELS.get(agent, agent)

    lines.append(f"| | |")
    lines.append(f"|---|---|")
    lines.append(f"| **Agent** | {agent_label} |")
    lines.append(f"| **Date** | {created} |")
    lines.append(f"| **Model** | {model_id} |")
    lines.append(f"| **Tokens** | {tokens:,} |")
    lines.append(f"| **Cost** | ${cost:.6f} |")
    lines.append(f"| **Files changed** | {files_changed} (+{additions}/-{deletions}) |")
    lines.append(f"| **Directory** | `{session.get('directory', '')}` |")
    lines.append("")

    messages = fetch_messages(db_cursor, session["id"])
    for msg in messages:
        lines.append(render_message(msg, level))

    children = children_map.get(session["id"], [])
    for child in sorted(children, key=lambda x: x["time_created"]):
        lines.append(render_session(child, children_map, level + 1))

    return "\n".join(lines)


# Build the table of contents by agent
def build_toc(root_sessions, children_map):
    lines = []
    lines.append("## Table of Contents\n")

    chapters = {}
    for s in root_sessions:
        agent = s.get("agent", "unknown")
        chapters.setdefault(agent, []).append(s)

    for agent in AGENT_ORDER:
        if agent not in chapters:
            continue
        agent_label = AGENT_LABELS.get(agent, agent)
        sessions = sorted(chapters[agent], key=lambda x: x["time_created"])
        lines.append(f"- [{agent_label} ({len(sessions)} sessions)](#{anchor(agent_label)})\n")
        for s in sessions:
            title = s["title"] or "Untitled"
            aid = anchor(title)
            lines.append(f"  - [{title}](#{aid})\n")
            for child in children_map.get(s["id"], []):
                ctitle = child["title"] or "Untitled"
                caid = anchor(ctitle)
                lines.append(f"    - [{ctitle}](#{caid})\n")
        lines.append("")

    return "".join(lines)


# Build chapter sections grouped by agent
def build_chapters(root_sessions, children_map):
    lines = []

    chapters = {}
    for s in root_sessions:
        agent = s.get("agent", "unknown")
        chapters.setdefault(agent, []).append(s)

    for agent in AGENT_ORDER:
        if agent not in chapters:
            continue
        agent_label = AGENT_LABELS.get(agent, agent)
        sessions = sorted(chapters[agent], key=lambda x: x["time_created"])
        lines.append(f"\n---\n\n## Chapter {agent_label} ({len(sessions)} sessions) {{#{anchor(agent_label)}}}\n")
        for s in sessions:
            lines.append(render_session(s, children_map, level=3))

    return "\n".join(lines)


# Entry point that assembles and writes the book
def main():
    global db_cursor
    conn = connect_db()
    db_cursor = conn.cursor()

    all_sessions = fetch_sessions(db_cursor)
    root_sessions, children_map = build_tree(all_sessions)

    lines = []
    lines.append("# Book of Sessions\n")
    lines.append(f"*Generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} from OpenCode session database*\n")
    lines.append(f"**{len(all_sessions)} total sessions** ({len(root_sessions)} root sessions)\n")

    lines.append(build_toc(root_sessions, children_map))
    lines.append(build_chapters(root_sessions, children_map))

    content = "\n".join(lines)
    output_path = os.path.abspath(OUTPUT_PATH)
    with open(output_path, "w") as f:
        f.write(content)

    word_count = len(content.split())
    print(f"✓ Book written to {output_path}")
    print(f"  {word_count:,} words, {len(all_sessions)} sessions, {len(root_sessions)} root sessions")

    conn.close()


if __name__ == "__main__":
    main()
