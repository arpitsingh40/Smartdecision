"""Deep Discussion Engine core — proven in POC (Phase 1, all checks passed).
Pure functions: intent classification, rolling fields, re-engagement.
Single LLM call per turn: Gemini 3.5 Flash primary.
Multi-modal: attach image / PDF / Excel / CSV / text — engine reads and reasons on the file."""
import os
import io
import json
import re
import time
import base64
import logging
from datetime import datetime, timedelta, timezone

import requests

log = logging.getLogger(__name__)

PRIMARY_MODEL = os.environ.get("LLM_MODEL", "gemini-3.5-flash").strip()
ANALYTICAL_MODEL = os.environ.get("LLM_MODEL_ANALYTICAL", PRIMARY_MODEL).strip()
ULTRA_MODEL = os.environ.get("LLM_MODEL_ULTRA", PRIMARY_MODEL).strip()
FALLBACK_MODEL = os.environ.get("LLM_MODEL_FALLBACK", PRIMARY_MODEL).strip()


def _extract_json(txt: str) -> str:
    """Pull the first balanced JSON object out of a model reply.
    Tolerates code fences, leading prose, and trailing prose after the closing brace
    (the 'Extra data' failure mode). Returns best-effort substring if truncated."""
    s = re.sub(r"^```(json)?|```$", "", txt or "", flags=re.M).strip()
    start = s.find("{")
    if start == -1:
        return s
    depth, in_str, esc = 0, False, False
    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[start:i + 1]
    return s[start:]  # unterminated (truncated) — best effort

IMAGE_MIMES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}
MAX_FILE_CHARS = 50000  # cap extracted text — bounds cost; engine doesn't need the whole novel

# ---------- Gemini client adapter (Anthropic-compatible interface, direct HTTP) ----------

class _GeminiContentBlock:
    __slots__ = ("text", "type")
    def __init__(self, text: str):
        self.text = text
        self.type = "text"

class _GeminiUsage:
    __slots__ = ("input_tokens", "output_tokens")
    def __init__(self, input_tokens: int, output_tokens: int):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens

class _GeminiResponse:
    __slots__ = ("content", "usage")
    def __init__(self, text: str, input_tokens: int = 0, output_tokens: int = 0):
        self.content = [_GeminiContentBlock(text)]
        self.usage = _GeminiUsage(input_tokens, output_tokens)

_GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

class _GeminiMessages:
    def __init__(self, api_key: str):
        self._api_key = api_key

    def _url(self, model: str) -> str:
        return f"{_GEMINI_API_BASE}/{model}:generateContent?key={self._api_key}"

    @staticmethod
    def _convert_content(content):
        if isinstance(content, str):
            return [{"text": content}]
        parts = []
        for block in content:
            if not isinstance(block, dict):
                parts.append({"text": str(block)})
                continue
            t = block.get("type", "")
            if t == "text":
                parts.append({"text": block.get("text", "")})
            elif t == "image":
                src = block.get("source", {})
                if src.get("type") == "base64":
                    parts.append({"inline_data": {"mime_type": src.get("media_type", "image/png"), "data": src.get("data", "")}})
                elif src.get("type") == "url":
                    parts.append({"file_data": {"file_uri": src["url"], "mime_type": src.get("media_type", "image/png")}})
        return parts

    @staticmethod
    def _system_to_text(system):
        if not system:
            return None
        if isinstance(system, str):
            return system
        if isinstance(system, list):
            texts = [s["text"] for s in system if isinstance(s, dict) and isinstance(s.get("text"), str) and s["text"].strip()]
            return "\n".join(texts) if texts else None
        return None

    def create(self, model: str, system=None, messages=None, max_tokens=None, **kwargs):
        system_text = self._system_to_text(system)
        contents = []
        for m in messages or []:
            role = m.get("role", "user")
            content = m.get("content", "")
            gemini_role = "model" if role == "assistant" else "user"
            parts = self._convert_content(content)
            contents.append({"role": gemini_role, "parts": parts})
        body = {"contents": contents, "generationConfig": {"maxOutputTokens": max_tokens or 8192}}
        if system_text:
            body["system_instruction"] = {"parts": [{"text": system_text}]}
        last_err = None
        for attempt in range(4):
            try:
                resp = requests.post(self._url(model), json=body, timeout=120)
                resp.raise_for_status()
            except requests.exceptions.RequestException as e:
                detail = ""
                try:
                    detail = resp.text
                except Exception:
                    pass
                status = resp.status_code if hasattr(resp, 'status_code') else 0
                # Retry on 429 (rate limit) and 503 (overloaded)
                if status in (429, 503) and attempt < 3:
                    import re
                    m2 = re.search(r'retry in (\d+(?:\.\d+)?)s', detail, re.I)
                    delay = float(m2.group(1)) + 2 if m2 else (2 ** attempt * 5)
                    log.warning(f"Gemini {status}, retry {attempt+1}/3 after {delay:.0f}s: {detail[:120]}")
                    time.sleep(delay)
                    last_err = RuntimeError(f"Gemini API error: {e} {detail[:300]}")
                    continue
                raise RuntimeError(f"Gemini API error: {e} {detail[:500]}")
            data = resp.json()
            text = ""
            candidates = data.get("candidates") or []
            if candidates:
                c = candidates[0]
                finish = c.get("finishReason", "")
                if finish in ("SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT"):
                    log.warning(f"Gemini blocked: finishReason={finish}")
                parts = (c.get("content") or {}).get("parts") or []
                if parts:
                    text = parts[0].get("text", "")
            usage = data.get("usageMetadata") or {}
            in_tokens = usage.get("promptTokenCount", 0) or 0
            out_tokens = usage.get("candidatesTokenCount", 0) or 0
            return _GeminiResponse(text, in_tokens, out_tokens)
        raise last_err or RuntimeError("Gemini API failed after retries")

class _GeminiClient:
    def __init__(self, api_key: str):
        self._messages = _GeminiMessages(api_key)

    @property
    def messages(self):
        return self._messages


# ---------- DeepSeek client adapter (OpenAI-compatible, direct HTTP) ----------

_DEEPSEEK_API_BASE = "https://api.deepseek.com"

class _DeepSeekMessages:
    def __init__(self, api_key: str):
        self._api_key = api_key
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    @staticmethod
    def _system_to_text(system):
        if not system:
            return None
        if isinstance(system, str):
            return system.strip() or None
        if isinstance(system, list):
            texts = [s["text"] for s in system if isinstance(s, dict) and isinstance(s.get("text"), str) and s["text"].strip()]
            return "\n".join(texts) if texts else None
        return None

    @staticmethod
    def _content_as_text(content):
        if isinstance(content, str):
            return content
        parts = []
        for block in (content or []):
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)

    def create(self, model: str, system=None, messages=None, max_tokens=None, **kwargs):
        system_text = self._system_to_text(system)
        ds_messages = []
        if system_text:
            ds_messages.append({"role": "system", "content": system_text})
        for m in messages or []:
            role = m.get("role", "user")
            ds_role = "assistant" if role == "assistant" else "user"
            text = self._content_as_text(m.get("content", ""))
            ds_messages.append({"role": ds_role, "content": text})
        body = {
            "model": model,
            "messages": ds_messages,
            "max_tokens": max_tokens or 8192,
            "temperature": kwargs.get("temperature", 0.7),
        }
        last_err = None
        for attempt in range(4):
            try:
                resp = self._session.post(f"{_DEEPSEEK_API_BASE}/v1/chat/completions", json=body, timeout=120)
                resp.raise_for_status()
            except requests.exceptions.RequestException as e:
                detail = ""
                try:
                    detail = resp.text
                except Exception:
                    pass
                status = resp.status_code if hasattr(resp, 'status_code') else 0
                if status in (429, 503) and attempt < 3:
                    import re
                    m2 = re.search(r'retry after (\d+)', detail, re.I)
                    delay = float(m2.group(1)) + 1 if m2 else (2 ** attempt * 5)
                    log.warning(f"DeepSeek {status}, retry {attempt+1}/3 after {delay:.0f}s")
                    time.sleep(delay)
                    last_err = RuntimeError(f"DeepSeek API error: {e} {detail[:300]}")
                    continue
                raise RuntimeError(f"DeepSeek API error: {e} {detail[:500]}")
            data = resp.json()
            text = ""
            choices = data.get("choices") or []
            if choices:
                text = (choices[0].get("message") or {}).get("content", "") or ""
            usage = data.get("usage") or {}
            in_tokens = usage.get("prompt_tokens", 0) or 0
            out_tokens = usage.get("completion_tokens", 0) or 0
            return _GeminiResponse(text, in_tokens, out_tokens)
        raise last_err or RuntimeError("DeepSeek API failed after retries")

class _DeepSeekClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._messages = _DeepSeekMessages(api_key)

    @property
    def messages(self):
        return self._messages


# ---------- Provider factory ----------

_client = None

def client():
    global _client
    if _client is not None:
        return _client
    provider = os.environ.get("LLM_PROVIDER", "gemini").strip().lower()
    if provider == "deepseek":
        key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("DEEPSEEK_API_KEY not set")
        _client = _DeepSeekClient(key)
        log.info("LLM provider: DeepSeek (%s)", os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash"))
    else:
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY not set")
        _client = _GeminiClient(key)
        log.info("LLM provider: Gemini")
    return _client

# ---------------------------------------------------------------- intent (pure)
ACK = re.compile(r"\b(did it|done|completed|finished|shipped|sent it|made the call|i did)\b", re.I)
SETBACK = re.compile(r"\b(couldn'?t|didn'?t|failed|stuck|blocked|gave up|too hard|avoided|put it off|procrastinat)\b", re.I)
QUESTION = re.compile(r"\?\s*$|^\s*(how|what|should|why|when|can i|do i|is it)\b", re.I)

def classify_intent(msg: str, days_since_last: float) -> str:
    if days_since_last >= 14:
        return "silence_breaker"
    if ACK.search(msg):
        return "acknowledgment"
    if SETBACK.search(msg):
        return "setback"
    if QUESTION.search(msg):
        return "question"
    if len(msg.split()) < 4:
        return "drift"
    return "update"

# ------------------------------------------------- rolling fields (pure, replayable)
def rolling_fields(events: list, now: datetime) -> dict:
    cutoff = now - timedelta(days=14)
    recent = [e for e in events if e["at"] >= cutoff]
    temps = [e["emotional_temperature"] for e in recent if e.get("emotional_temperature") is not None]
    acts = [e for e in recent if e.get("action_assigned")]
    done = [e for e in acts if e.get("action_done")]
    consistency = (len(done) / len(acts)) if acts else 0.5
    expected_turns = 14 / 3.5  # own-pace baseline: ~2 turns/week
    pace = "on-track"
    if len(recent) >= expected_turns * 1.4 and consistency >= 0.6:
        pace = "ahead"
    elif len(recent) <= expected_turns * 0.5 or consistency < 0.3:
        pace = "behind"
    return {
        "emotional_temperature": round(sum(temps)/len(temps), 2) if temps else 0.5,
        "execution_consistency": round(consistency, 2),
        "pace_calibration": pace,
        "contradiction_history": [e["contradiction"] for e in events if e.get("contradiction")],
    }

# ------------------------------------------------- re-engagement (pure, NO LLM, founder-locked phrase bank)
PHRASE_BANK = {
    "execution_up":   "{days} days away. Last time: {prior}. Your follow-through is up {mag}% since then — whatever you changed, it is working.",
    "execution_down": "{days} days away. Last time: {prior}. Execution consistency dropped {mag}% — worth naming before anything else.",
    "emotional_up":   "{days} days since we spoke. You left at: {prior}. The resistance reads lower now.",
    "emotional_down": "{days} days since we spoke. You left at: {prior}. Something is heavier than it was — that comes first.",
    "contradiction":  "While you were gone, a tension surfaced: {extra} Worth looking at before moving.",
}
PRIORITY = ["contradiction", "execution", "emotional"]

def compute_reengagement_line(last_snap: dict, now_snap: dict, days_absent: int):
    if days_absent < 7 or not last_snap:
        return None
    deltas = []
    de = now_snap["execution_consistency"] - last_snap.get("execution_consistency", 0.5)
    if abs(de) >= 0.15:
        deltas.append(("execution", de, abs(round(de*100))))
    dt = now_snap["emotional_temperature"] - last_snap.get("emotional_temperature", 0.5)
    if abs(dt) >= 0.2:
        deltas.append(("emotional", dt, abs(round(dt*100))))
    new_contra = [c for c in now_snap["contradiction_history"] if c not in last_snap.get("contradiction_history", [])]
    if new_contra:
        deltas.append(("contradiction", 0, new_contra[-1]))
    if not deltas:
        return None  # silence-preserving
    deltas.sort(key=lambda d: PRIORITY.index(d[0]))
    kind, sign, extra = deltas[0]
    if kind == "contradiction":
        x = str(extra).rstrip(".") + "."
        return PHRASE_BANK["contradiction"].format(extra=x)
    key = f"{kind}_{'up' if sign > 0 else 'down'}"
    return PHRASE_BANK[key].format(days=days_absent, prior=last_snap.get("summary_line", "your last position"), mag=extra)

# ------------------------------------------------- action assist: "Do it for me" (1 LLM call)
def _user_context_block(user_doc) -> str:
    """Render the user's questionnaire (Dream/Capacity/Advantage/Potential) into a tight
    prompt block. Returns empty string if the questionnaire isn't completed yet, so threads
    opened before answering keep the prior behaviour."""
    if not user_doc:
        return ""
    q = user_doc.get("questionnaire") or {}
    dream = (q.get("dream") or "").strip()
    capacity = (q.get("capacity") or "").strip()
    advantage = (q.get("advantage") or "").strip()
    potential = (q.get("potential") or "").strip()
    if not (dream or capacity or advantage or potential):
        return ""
    lines = ["What they've told me about themselves (use this as ground truth for what's realistic, what's at stake, and what to lean on):"]
    if dream:
        lines.append(f"- DREAM: {dream}")
    if capacity:
        lines.append(f"- CAPACITY (time/money/energy they have right now): {capacity}")
    if advantage:
        lines.append(f"- ADVANTAGE (what they uniquely have going for them): {advantage}")
    if potential:
        lines.append(f"- POTENTIAL (what they believe they could become): {potential}")
    return "\n".join(lines) + "\n\n"


ASSIST_SYSTEM = """You are the Deep Discussion Engine's execution hand. The user has ONE next action. Your job: remove every ounce of friction so they finish it in minutes, not days — and they should feel cared for, not lectured to.
VOICE: write like a thoughtful friend who happens to be sharp. Plain English, short sentences, easy to scan, in the USER'S register (match their tone — if they're casual, you're casual; if they're crisp, you're crisp). Skip jargon. No "Dear Sir/Madam" stiffness in drafts; no corporate "I hope this email finds you well" unless that's truly how they speak. Contractions welcome. The artifact must read like THEY wrote it on a good day.
FILE-AWARE EXECUTION (critical): if the thread state shows the user has attached a file with the data needed for this action (visible via FILE_FACTS in the context), the artifact IS the computation — not instructions to do the computation. NEVER produce a checklist of 'open the sheet, find the column, count the rows' for data the engine has already seen. Instead, state the answer with the numbers ('I counted 5 Disbursed out of your 70 rows. Now we just need your fee per disbursed case — that one isn't in the sheet.') and ask for ONLY the missing piece. If both numbers are available, do the math and present the result.
Decide the kind:
- "draft": the action produces a sendable/usable artifact (email, message, list, script, post, plan, outline, research summary, COMPUTED table from attached data). Write the FINISHED artifact in the user's voice — specific, ready to ship, grounded in everything known from the thread. No placeholders unless a fact is truly unknowable, then use [[FILL: what goes here]] sparingly.
- "kit": the action is physical/real-world (a call, a visit, signing, a workout, a meeting). Produce the 10-minute version: the exact words to say or script to follow, what to bring/open, the smallest viable version that still counts as done.
Rules: concrete over generic; their stated goal and why-it-matters are your material; zero fluff; the artifact must be genuinely shippable as-is; if it's an email or message, sound human, not templated; if it's analysis on attached data, do the math and present results, do not instruct the user to do it.
Return ONLY valid JSON, no markdown fences:
{"kind": "draft" or "kit",
 "title": "3-6 words naming the artifact",
 "channel": "email"|"whatsapp"|"call"|"document"|"calendar"|"other",
 "subject": "email subject line, or null if not an email",
 "artifact": "the complete artifact text (for kit: the exact script/words + what to bring; for computed analysis: the answers with numbers, not instructions to compute)",
 "steps": ["2-4 micro-steps to ship it, each under 10 words"],
 "handoff": "1 warm line: exactly what to do with this in the next 5 minutes",
 "time_estimate_min": minutes_to_complete_as_integer}"""

ASSIST_REQUIRED = ("kind", "title", "artifact", "handoff")

def llm_complete_action(thread: dict, user_doc=None):
    """Generate the ship-ready artifact (or 10-minute kit) for the current next action."""
    saved_facts = (thread.get("current_file_facts") or "").strip()
    facts_block = f"FILE_FACTS (from a file the user attached earlier — the artifact must USE these numbers, not ask the user to re-derive them):\n{saved_facts}\n" if saved_facts else ""
    user_ctx_block = _user_context_block(user_doc)
    prompt = (
        f"{user_ctx_block}"
        f"GOAL: {thread['goal']}\n"
        f"WHY IT MATTERS TO THEM: {thread.get('why_now', '(not stated)')}\n"
        f"STATE SUMMARY:\n{thread['current_state_summary']}\n"
        f"EASIEST PATH: {thread['current_easiest_path']}\n"
        f"NEXT ACTION TO COMPLETE: {thread['current_next_action']}\n"
        f"PAYOFF WHEN DONE: {thread.get('current_action_payoff') or '(not stated)'}\n"
        f"BIG PICTURE: {thread.get('current_big_picture') or '(not stated)'}\n"
        f"{facts_block}"
        "Produce the artifact or kit that completes this next action with minimal user effort."
    )
    last_err = None
    # System block is cached (prompt caching = 90% cheaper from 2nd call onward, identical block).
    system_blocks = [{"type": "text", "text": ASSIST_SYSTEM,
                      "cache_control": {"type": "ephemeral"}}]
    for model in (PRIMARY_MODEL, FALLBACK_MODEL):
        try:
            r = client().messages.create(model=model, max_tokens=3000, system=system_blocks,
                                         messages=[{"role": "user", "content": prompt}])
            txt = next((b.text for b in r.content if getattr(b, "type", "") == "text"), "").strip()
            out = json.loads(_extract_json(txt))
            if not all(k in out for k in ASSIST_REQUIRED):
                raise ValueError("incomplete JSON keys")
            usage = {"input_tokens": int(getattr(r.usage, "input_tokens", 0) or 0),
                     "output_tokens": int(getattr(r.usage, "output_tokens", 0) or 0)}
            return out, model, usage
        except Exception as e:
            last_err = e
    raise RuntimeError(f"All models failed: {last_err}")

# ------------------------------------------------- multi-modal attachments (file/image -> LLM-readable)
def _extract_pdf(b: bytes) -> str:
    """PyMuPDF — extract text from first 30 pages, cap at MAX_FILE_CHARS."""
    import fitz
    parts = []
    with fitz.open(stream=b, filetype="pdf") as doc:
        for i, page in enumerate(doc):
            if i >= 30:
                break
            parts.append(page.get_text())
    return "\n".join(parts)[:MAX_FILE_CHARS]


def _extract_xlsx(b: bytes) -> str:
    """openpyxl — first 5 sheets, 200 rows each, tab-separated."""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(b), data_only=True, read_only=True)
    parts = []
    for sheet in wb.sheetnames[:5]:
        ws = wb[sheet]
        parts.append(f"### Sheet: {sheet}")
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i >= 200:
                break
            parts.append("\t".join("" if v is None else str(v) for v in row))
    return "\n".join(parts)[:MAX_FILE_CHARS]


def _extract_csv(b: bytes) -> str:
    import csv
    rdr = csv.reader(io.StringIO(b.decode("utf-8", errors="replace")))
    lines = []
    for i, row in enumerate(rdr):
        if i >= 500:
            break
        lines.append(",".join(row))
    return "\n".join(lines)[:MAX_FILE_CHARS]


def build_attachment_blocks(attachment):
    """Turn an uploaded file into LLM-ready content.
    Images -> Anthropic vision content block (the model sees the image).
    PDF/Excel/CSV/text -> server-side extraction, appended to the text prompt (cheaper + reliable).
    Returns (vision_blocks, text_appendix). Either or both may be empty.
    """
    if not attachment:
        return [], ""
    mime = (attachment.get("mime") or "").lower()
    name = attachment.get("filename") or "file"
    b64 = attachment.get("base64") or ""
    if not b64:
        return [], ""
    if mime in IMAGE_MIMES:
        return ([{"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}}],
                f"\n\nATTACHED_IMAGE: {name} — read it as evidence/context for the user's situation.")
    try:
        raw = base64.b64decode(b64)
        lower = name.lower()
        if mime == "application/pdf" or lower.endswith(".pdf"):
            text = _extract_pdf(raw)
        elif "spreadsheet" in mime or lower.endswith((".xlsx", ".xls")):
            text = _extract_xlsx(raw)
        elif mime == "text/csv" or lower.endswith(".csv"):
            text = _extract_csv(raw)
        else:
            text = raw.decode("utf-8", errors="replace")[:MAX_FILE_CHARS]
        return [], f"\n\n--- ATTACHED FILE: {name} ---\n{text}\n--- END FILE ---"
    except Exception as e:
        log.warning(f"attachment '{name}' could not be parsed: {e}")
        return [], f"\n\n[attached file '{name}' could not be read — ignore it and continue]"


# ------------------------------------------------- single LLM call per turn
SYSTEM = """You are someone who genuinely cares about the person you're talking to. Not a coach, not a therapist, not a system — a thoughtful human who's sat across from enough people to know what works and what doesn't, but stays curious about each new person.

Here's who you are:

YOU LISTEN FIRST. Before any insight, before any question, you show them you actually heard what they said. Their words come back to them before anything new arrives. Not parroting — reflecting. So they feel: "this person gets it."

YOU NOTICE WHAT'S UNDERNEATH. People rarely say the real thing. They say the safe thing. You have a gift for sensing the fear, the pattern, the contradiction they haven't named. Sometimes you name it gently. Sometimes you hold it and wait. You know the difference.

YOU GIVE SOMETHING REAL EVERY TIME. Not empty encouragement. Not generic wisdom. A real observation, a useful frame, a number that matters, a question they haven't asked themselves. Every turn leaves them with something they didn't have before. If you don't have hard data, you say so and give your best read.

YOU KNOW WHEN TO PUSH AND WHEN TO BE QUIET. Some turns need a gentle nudge. Some need a hard truth wrapped in care. Some need you to get out of the way entirely. You read the room. You don't force depth where there isn't safety. You don't hold back when there is.

YOU REMEMBER. Across turns. Across sessions. You never ask what you already know. You notice what's changed. You connect what's happening now to what happened before. The person you're talking to feels known.

THE WAY YOU SPEAK:
- Plain English. Short sentences. One idea at a time.
- Like you're sitting across from them at a quiet table.
- Contractions welcome. Jargon banned. No corporate speak.
- No "I hope this helps", no "let me know if", no filler.
- Every line earns its place. Their eyes should glide.

HOW YOU STRUCTURE EACH TURN:
1. Start by showing you heard them. A short reflection in your own words.
2. Then one thing that moves them forward — an observation, a question, a possibility.
3. End with one question or opening. Not more than one.

The phase guide (internal — use it to track where you are):
- exploring: still finding the real problem. Listen and reflect. No action yet.
- naming: the blocker is visible. State it plainly. Still no action.
- ready_to_act: propose a tentative next step. Ask for consent warmly.
- acting: they said yes. Lock the concrete step. Give payoff + big picture.
- checking_in: they're reporting back. Celebrate or regroup.

These fields below are your internal notes — they track state so the conversation
builds coherently across turns. The acknowledgment is what the user sees.

Return ONLY valid JSON, no markdown fences:
{"phase": "exploring"|"naming"|"ready_to_act"|"acting"|"checking_in",
 "phase_reason": "1 short line — why this phase now",
 "acknowledgment": "Your reply to them. Natural, flowing, warm. Start by reflecting what they said. If a fear or blocker is in play, unfold it gently and point toward a way through. No question marks here — the question goes in refreshed_open_question.",
 "mirror": "1 gentle sentence: what they didn't say but you sense beneath their words. Statement, not a question. Soft openers welcome: 'I may be wrong, but…'",
 "understanding": {"focus": "their current focus area", "fears": "the fear under the surface, or empty", "blockers": "the concrete blocker, or empty", "constraints": "limits you've learned, or empty", "tried": "what they've already tried, or empty", "motivators": "what actually drives them, or empty", "stage": "where they stand in 1 short line", "gap_to_goal": "the gap from here to their result in 1 line", "emotional_read": "how they seem to feel", "needs_now": "what they most need: heard | decision | plan | reality_check | encouragement | answer"},
 "refreshed_easiest_path": "1-2 lines — null when exploring",
 "refreshed_next_action": "1 line: concrete 24-48h action — null when exploring or naming",
 "outbox_alternative": "1-2 lines: one non-obvious higher-leverage alternative — null when exploring/naming or when the obvious move is already best",
 "action_payoff": "1 line: what they'll hold within 48h — null unless ready_to_act/acting/checking_in",
 "big_picture_link": "1 line: how this action moves their goal, quantified — null unless ready_to_act/acting/checking_in",
 "bold_move": "1-2 lines: the unconventional higher-leverage play, or null",
 "requested_input": "0-1 line or null. Only when the next action needs evidence they can bring back. Be specific and warm.",
 "file_facts": "3-6 lines snapshot of attached file — null if no file this turn",
 "refreshed_open_question": "1 line: the unresolved tension. The ONLY question mark in your reply.",
 "skip_list": ["0-2 things to ignore right now"],
 "state_summary": "3 short lines: where they are in their own register",
 "signals": {"emotional_temperature": 0.0to1.0, "action_done": bool, "contradiction": "string or null"}}"""

REQUIRED_KEYS = ("phase", "acknowledgment", "refreshed_open_question", "state_summary", "signals")
VALID_PHASES = ("exploring", "naming", "ready_to_act", "acting", "checking_in")

def llm_turn(thread: dict, substrate: dict, user_msg: str, intent: str, mode: str = "normal",
             attachment=None, user_doc=None,
             recall_block: str = "", attachment_preview=None,
             understanding=None, strategy=None):
    adjust_note = ""
    if intent == "action_adjust":
        adjust_note = ("ADJUSTMENT: the user is pushing back on the PRIOR NEXT ACTION above - "
                       "their message holds an obstacle or their own version of the step. Do not mark it done. "
                       "Recalibrate: keep what works about it, redesign it around their input. "
                       "The refreshed_next_action must visibly incorporate their words.\n")
    # Server may have pre-extracted the attachment via doc_memory (preferred path: handles all formats
    # + decides inline-vs-tree). Fall back to the legacy internal extractor if no preview was supplied.
    if attachment_preview is not None:
        vision_blocks = attachment_preview.get("vision_blocks") or []
        file_text = attachment_preview.get("inline_text") or ""
    else:
        vision_blocks, file_text = build_attachment_blocks(attachment)
    # Saved file snapshot from a prior turn (set when the user attached a file earlier).
    # Inject so the engine reasons on what it already saw, without the user re-uploading.
    saved_facts = (thread.get("current_file_facts") or "").strip()
    facts_block = f"\nFILE_FACTS (from a file the user attached earlier — still valid this turn):\n{saved_facts}\n" if saved_facts else ""
    user_ctx_block = _user_context_block(user_doc)
    # Living memory of this person (the "understanding trail"), injected so the engine remembers
    # across turns and threads and never re-asks what it already knows.
    _u = understanding if isinstance(understanding, dict) else {}
    _u_keys = ("focus", "fears", "blockers", "constraints", "tried", "motivators",
               "stage", "gap_to_goal", "emotional_read", "needs_now")
    _u_lines = [f"- {k}: {_u[k]}" for k in _u_keys if isinstance(_u.get(k), str) and _u.get(k).strip()]
    understanding_block = ("What I know about them (my living memory, update it this turn):\n"
                           + "\n".join(_u_lines) + "\n") if _u_lines else ""
    prior_phase = (thread.get("current_phase") or "").strip() or "(none — this is an early turn)"
    geo = thread.get("user_geo") or {}
    geo_line = ""
    city, country = geo.get("city"), geo.get("country")
    if city and country and city not in ("Unknown", "Local"):
        geo_line = f"USER_LOCATION: {city}, {country} (anchor tool/platform/payment/regulation suggestions to here)\n"
    # Strategy instruction from question_strategy engine
    strategy_block = ""
    if strategy:
        try:
            from question_strategy import strategy_prompt_block
            strategy_block = strategy_prompt_block(strategy)
        except Exception:
            pass
    recall_section = (recall_block.strip() + "\n") if recall_block and recall_block.strip() else ""
    prompt = (
        f"{user_ctx_block}"
        f"{understanding_block}"
        f"{geo_line}"
        f"Their goal: {thread['goal']}\n"
        f"What this means to them (their own words): {thread.get('why_now', '(not stated)')}\n"
        f"Where they are right now:\n{thread['current_state_summary']}\n"
        f"The question they're sitting with: {thread['current_open_question']}\n"
        f"The easiest path forward: {thread['current_easiest_path']}\n"
        f"The last action they committed to (check if it's done): {thread['current_next_action']}\n"
        f"Conversation stage: {prior_phase}\n"
        f"How they're doing: temperature={substrate['emotional_temperature']} consistency={substrate['execution_consistency']} pace={substrate['pace_calibration']} streak={substrate.get('streak', 0)} actions kept in a row\n"
        f"What this message feels like: {intent}\n"
        f"{adjust_note}"
        f"{facts_block}"
        f"{recall_section}"
        f"{strategy_block}"
        f"Their message: {user_msg}"
        f"{file_text}"
    )
    user_content = vision_blocks + [{"type": "text", "text": prompt}] if vision_blocks else prompt
    # Routing:
    #  ultra              -> Fable 5 (deep thinking) then Opus then Haiku
    #  file/recall present -> Sonnet 4.5 (cheaper, same context, great at analysis) then Opus then Haiku
    #  normal              -> Opus 4.8 then Haiku
    has_file_context = bool(vision_blocks) or bool(file_text) or bool(recall_section)
    if mode == "ultra":
        chain = (ULTRA_MODEL, PRIMARY_MODEL, FALLBACK_MODEL)
    elif has_file_context:
        chain = (ANALYTICAL_MODEL, PRIMARY_MODEL, FALLBACK_MODEL)
    else:
        chain = (PRIMARY_MODEL, FALLBACK_MODEL)
    last_err = None
    # System block is cached: SYSTEM is large and identical across turns, prompt caching cuts
    # ~90% off its repeated read cost from the 2nd turn onward (same model + same content).
    system_blocks = [{"type": "text", "text": SYSTEM,
                      "cache_control": {"type": "ephemeral"}}]
    for model in chain:
        try:
            kwargs = {"model": model, "max_tokens": 2000, "system": system_blocks,
                      "messages": [{"role": "user", "content": user_content}]}
            if has_file_context and model != ULTRA_MODEL:
                kwargs["max_tokens"] = 3500  # room for richer analysis on file/recall turns
            if model == ULTRA_MODEL:
                kwargs["max_tokens"] = 8000  # room for thinking + JSON output
                kwargs["thinking"] = {"type": "adaptive"}
                kwargs["extra_body"] = {"output_config": {"effort": "high"}}
            r = client().messages.create(**kwargs)
            txt = next((b.text for b in r.content if getattr(b, "type", "") == "text"), "").strip()
            out = json.loads(_extract_json(txt))
            if not all(k in out for k in REQUIRED_KEYS):
                raise ValueError("incomplete JSON keys")
            # phase guardrails: clamp invalid phases, enforce null-fields by phase, enforce
            # single-question rule, strip em-dashes from voice-bearing fields.
            phase = (out.get("phase") or "exploring").strip().lower()
            if phase not in VALID_PHASES:
                phase = "exploring"
            out["phase"] = phase
            # Pre-action phases must not ship an action / payoff / big_picture / outbox
            if phase in ("exploring", "naming"):
                out["refreshed_next_action"] = None
                out["action_payoff"] = None
                out["big_picture_link"] = None
                out["outbox_alternative"] = None
                if phase == "exploring":
                    out["refreshed_easiest_path"] = None
            # If there's no concrete action, an outbox alternative makes no sense either.
            if not (out.get("refreshed_next_action") or "").strip():
                out["outbox_alternative"] = None
            # Clean em-dashes -> comma without a stray leading space (slop ban + polish fix).
            def _dedash(s):
                s = s.replace(" — ", ", ").replace(" – ", ", ").replace("—", ", ").replace("–", ", ")
                return s.replace(" ,", ",")
            for k in ("acknowledgment", "mirror", "insight", "refreshed_easiest_path",
                      "refreshed_next_action", "outbox_alternative", "action_payoff",
                      "big_picture_link", "bold_move", "refreshed_open_question", "state_summary"):
                v = out.get(k)
                if isinstance(v, str):
                    out[k] = _dedash(v)
            # insight removed from UI (no boxes); keep harmless default if a model still emits it
            if not isinstance(out.get("insight"), str):
                out["insight"] = ""
            # understanding trail must be a dict (living memory, persisted across turns)
            if not isinstance(out.get("understanding"), dict):
                out["understanding"] = {}
            # Enforce ONE question per turn: strip stray '?' from non-question fields.
            for k in ("acknowledgment", "mirror"):
                if isinstance(out.get(k), str):
                    out[k] = out[k].replace("?", ".")
            usage = {"input_tokens": int(getattr(r.usage, "input_tokens", 0) or 0),
                     "output_tokens": int(getattr(r.usage, "output_tokens", 0) or 0)}
            return out, model, usage
        except Exception as e:
            last_err = e
    raise RuntimeError(f"All models failed: {last_err}")
