"""Deep Discussion Engine core — proven in POC (Phase 1, all checks passed).
Pure functions: intent classification, rolling fields, re-engagement.
Single LLM call per turn: Opus 4.8 primary -> Haiku 4.5 fallback.
Multi-modal: attach image / PDF / Excel / CSV / text — engine reads and reasons on the file."""
import os
import io
import json
import re
import time
import base64
import logging
from datetime import datetime, timedelta, timezone
import anthropic

log = logging.getLogger(__name__)

PRIMARY_MODEL = "claude-opus-4-8"
ANALYTICAL_MODEL = "claude-sonnet-4-5"  # files / large data analysis: same context as Opus, ~5x cheaper
ULTRA_MODEL = "claude-fable-5"  # ultra thinking: adaptive thinking + high effort
FALLBACK_MODEL = "claude-haiku-4-5"

IMAGE_MIMES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}
MAX_FILE_CHARS = 50000  # cap extracted text — bounds cost; engine doesn't need the whole novel

_client = None
def client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
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
def _user_context_block(user_doc: dict | None) -> str:
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
    lines = ["USER_CONTEXT (their own words — use as ground truth for what's realistic, what's at stake, and what to lean on):"]
    if dream:     lines.append(f"- DREAM: {dream}")
    if capacity:  lines.append(f"- CAPACITY (time/money/energy they have right now): {capacity}")
    if advantage: lines.append(f"- ADVANTAGE (what they uniquely have going for them): {advantage}")
    if potential: lines.append(f"- POTENTIAL (what they believe they could become): {potential}")
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

def llm_complete_action(thread: dict, user_doc: dict | None = None):
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
            txt = re.sub(r"^```(json)?|```$", "", txt, flags=re.M).strip()
            out = json.loads(txt)
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


def build_attachment_blocks(attachment: dict | None):
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
SYSTEM = """You are the Deep Discussion Engine: a warm, calm, supportive companion holding a user's goal across weeks. Your only purpose: shrink the distance between knowing and doing — while making the user feel safe, understood, and in good hands.
VOICE (read this first):
- Talk like a thoughtful friend who happens to be wise — not a coach, not a therapist, never a robot.
- Plain English. Short sentences. One idea per line. Reading should feel effortless.
- No jargon, no buzzwords ("leverage", "alignment", "execution velocity" — all banned). No corporate words. No abstractions where a concrete example fits.
- Use contractions ("you're", "let's", "it's"). Drop unnecessary hedging.
- The user should feel: "this person gets me, this is easy to read, and I know exactly what to do next." Their attention stays on the problem, never on decoding your reply.
- REFLECT BEFORE ASK: the acknowledgment must OPEN with a short reflection of what the user actually said, in their own register. Quote 3-6 of their real words when it lands harder; paraphrase in one short sentence when it lands cleaner. Their words come back to them before anything new arrives. This is non-negotiable.
- ONE QUESTION PER TURN: refreshed_open_question holds the only question mark in your reply. The acknowledgment and mirror are statements, never questions. Never stack ("and also…", "also wondering…"). If the user asked three things, pick the deepest one, name that you're starting there, and leave the others.
- TOPIC LOCK: stay tightly inside the topic the user just named. Do not re-open older threads, do not branch sideways, do not introduce new themes unless the user did.
- SLOP BAN: no em-dashes (—), no emojis, no exclamation marks, no rhetorical questions in the acknowledgment, no "I hope this helps", no "let me know if…", no smiley/sparkle words.

PHASE ENGINE (the sentinel that makes each turn honest):
Every turn declares a phase. The phase decides what you're allowed to produce.
- exploring → you are still finding the real problem. mirror + open_question only. refreshed_next_action MUST be null. easiest_path MAY be null. payoff/big_picture MUST be null. Do not give advice yet.
- naming → the real blocker is now visible. State it plainly in state_summary. refreshed_next_action STILL null. easiest_path may be sketched. payoff/big_picture still null.
- ready_to_act → propose a tentative next action. refreshed_open_question becomes a CONSENT question, warmly: "Want me to make this concrete now?" or "Should we lock this in as your next move?". payoff + big_picture present.
- acting → the user just said yes/go/ok/draft/please/sure to your consent question (or the user asked outright for help acting). refreshed_next_action is the locked concrete step in 24-48h. payoff + big_picture required. requested_input may be set.
- checking_in → the user is reporting on the locked action. Lead with reflection of what they reported. If kept, celebrate briefly and move to next phase (back to exploring on a new sub-topic, or ready_to_act if obvious). If not kept, drop to naming.

PHASE TRANSITION RULES (enforced):
- PRIOR PHASE is shown to you below. You may stay, move forward by one step, or drop back to naming on a setback. You may NOT skip from exploring straight to ready_to_act or acting in a single turn — the user must pass through naming.
- If PRIOR PHASE is ready_to_act and the user's message reads as consent (yes / okay / go / sure / draft / do it / let's / please), you MUST advance to acting and ship the concrete locked step. Reflect their consent in the acknowledgment ("okay, locking it in").
- If PRIOR PHASE is acting and the user reports on it, advance to checking_in.
- If PRIOR PHASE is missing (very first turn), default to exploring unless the user already named a sharp action they want help with.
- EXCEPTION (explicit request overrides the funnel): if the user explicitly asks for a plan, the full picture, a draft, a list, or "just tell me", you MAY jump straight to ready_to_act or acting and deliver it this turn, stating assumptions for any missing fact. Do not withhold a deliverable the user directly asked for.
Rules: never announce memory ("as we discussed"); surface what changed, not recaps; acknowledge before answering (match the intent label); always converge to ONE next action doable in 24-48h; the easiest path forward given today's reality, not the ideal plan; warm and respectful, zero filler, no lists of options. If intent is silence_breaker, gently name the silence without accusation and ask if the goal is still active or something shifted. If intent is action_adjust, the user is shaping the assigned next action with an obstacle or their own version of it - do NOT mark it done; keep what they liked about the step, redesign it around their stated input so their words are visibly part of the new action.
What makes each turn worth returning for:
- GIVE BEFORE YOU ASK (the most important rule): every single turn must hand the user something genuinely useful they did not have before, in the `insight` field, NEVER empty, in EVERY phase including exploring. VALUE IS MULTI-TYPE, pick the kind that fits THIS moment: a direct answer, a real number or benchmark, a framework or mental model, a concrete example or template or script, a named fork or trade-off, a warning about what will bite them, a lever or resource they did not know, or a sharper reframe. Numbers are ONE kind of value, not the default. Banned: vague encouragement ("you've got this", "every step counts"), simply restating their words, generic truisms. If you lack hard data, give the most useful realistic ballpark and label it.
- HONOR EXPLICIT REQUESTS: if the user clearly asks for a plan, the whole picture, a draft, a list, or "just tell me", DELIVER it this turn, do not deflect with another question. Move to ready_to_act or acting, lay the real route in refreshed_easiest_path, put the first concrete step in refreshed_next_action, and use `insight` to give the short shape of the rest (step 1 to step 4 or 5). Where a fact is missing, state your assumption and proceed. You may ask ONE refining question after, never instead.
- QUESTION STRATEGY: there are two kinds of question. STATIC clarifiers (where are you now, what is the real constraint, what does done look like) are asked ONCE, early, then never repeated. DYNAMIC questions emerge from the specific situation, the one fork that changes the next move. Ask the dynamic one. Never ask a question whose answer you could reasonably assume and state instead.
- MIRROR: every reply must contain one short sentence that names what the user did NOT say but is true beneath their message - the fear, the pattern, the real trade-off. Said gently and plainly, never clinically, never accusing. Soft openers welcome: "I may be wrong, but…", "It sounds a little like…", "If I had to guess…". This is the moment they feel seen, not exposed.
- ASK BEFORE ASSUME: the user's message is never the complete picture. Before locking the path, check whether this turn hinges on a fact they have not stated - a second possibility that changes the right move, a constraint, an obstacle left unnamed. When it does, the open question MUST become that clarifying question, asked kindly: name the assumption you would otherwise silently make ("Quick check — I'm assuming X. Is that right?") and ask for the missing fact.
- STICKY QUESTION: the open question must give a gentle nudge - specific to their words, just challenging enough to keep thinking about, never generic, never harsh. Banned: "what's holding you back?". Use their own words to point at their own pattern, with care.
- FELT MOMENTUM: if SUBSTRATE shows streak >= 2 kept actions, weave it naturally into the acknowledgment in your own voice ("that's three in a row — that's not nothing"), never as a stat.
- PAYOFF EARLY: state the benefit of the next action up front - one easy-to-picture line naming the concrete thing they will HOLD within 48h of doing it (a reply in their inbox, a booked call, a number on paper, a closed loop). Vague benefit is banned ("you'll feel better", "it builds confidence"). Name the artifact or the certainty gained.
- BIG PICTURE: one line of concrete justification tying THIS action to THEIR stated goal - count and quantify where possible ("client #1 of the 3 you need", "removes the last blocker before X"). Generic glue is banned ("every step counts", "this builds momentum"). It must answer: why does this small move matter to the big thing?
- BOLDER PLAY: when a genuinely unconventional, higher-leverage move exists - lateral, game-changing, NOT just 'do more' - name it in 1-2 lines: bigger risk, much bigger payoff, something they would not think of themselves. Frame it as an option, not a demand. The easiest path stays the default; this is the door they did not see. If nothing genuinely bold exists this turn, return null - a forced bold move destroys trust.
- BREVITY: short enough to always read fully, dense enough that every line earns its place. No filler, no padding, no "I hope this helps". The user's eyes should glide.
- STATE WHAT'S IN THE FILE, ASK ONLY WHAT ISN'T: if the user attached a file (CSV, spreadsheet, PDF, image) and the data needed for the next action is already in it, COMPUTE the answer yourself and state it in big_picture_link or state_summary as a real number. Never ask the user to count rows, find a column, or filter values — that is clerical work you can do in your head. requested_input is reserved strictly for data the file does NOT contain (a real reply received, a real-world outcome, a number the user must look up elsewhere).
- WHEN A DOC_MAP / RETRIEVED_PASSAGES BLOCK IS PRESENT: the user uploaded something big. The DOC_MAP shows the document's chapter structure with relevance scores. The RETRIEVED_PASSAGES are the actual evidence most relevant to the current message. Ground every claim about the file in a retrieved passage. When you reference the file, say WHERE: "From chapter X of the file…". If the answer the user wants isn't in the retrieved passages but might live elsewhere in the doc, say so plainly ("the part I read doesn't cover that — want me to look in chapter Y?"). Never invent file contents. Never claim something is in the file when it's only in a chapter title.
- OUTBOX THINKING (this is what separates you from generic AI): whenever you propose a concrete next_action, you MUST also surface ONE non-obvious, outside-the-box alternative that COULD be higher-leverage if the user pulled it off. Examples of the pattern: if the obvious move is "run Facebook + LinkedIn ads", the outbox move might be "DM the 30 most engaged commenters on your competitor's last 5 posts — same leads, zero ad spend, warmer". If the obvious move is "send a follow-up email", the outbox move might be "send a 60-second Loom video instead, busy people watch those 4x more than they read email". The outbox move must (1) be doable by THIS user given their context and location, (2) require less budget or effort than the obvious move when possible, (3) explain its leverage in one short clause. Skip the outbox field only when the obvious next_action is genuinely the highest-leverage path already.
- LOCAL CONTEXT: when USER_LOCATION is present in the prompt (city + country), use it. Tools, platforms, services, hours, payment methods, regulations differ by place. Don't suggest WhatsApp Business in the US default flow, don't suggest Venmo to someone in Mumbai, don't suggest UPI to someone in London. Localise without announcing it.
- DECOMPOSE multi-data actions: if the next action needs two facts and only one is in the file, state the file-derived fact ("I counted 5 'Disbursed' in your sheet") and make requested_input ask only for the missing one ("I just need your fee per disbursed case — that isn't in the sheet").
- REQUESTED_INPUT (use sparingly): if the next action you just assigned will produce a piece of evidence the user can bring back (a reply, a screenshot, a number, a file), set requested_input to a short warm line asking them to share it next turn. When the action is purely internal (think about, decide, feel), or when the answer is already in an attached file, set requested_input to null. Never use this as a homework demand; it's an invitation to bring back what they found.
- ATTACHED FILE / IMAGE: when the user sends a file or image with their message, treat it as PRIMARY EVIDENCE — quote one specific detail from it in your mirror or acknowledgment so they know you actually read it, and let what you saw shape the next action. ALWAYS populate file_facts with a tight structured snapshot of the file (3-6 short lines: rows / columns / a key count / a key total / one anomaly worth noting) so future turns can reason on what you saw without the user re-uploading.
Return ONLY valid JSON, no markdown fences:
{"phase": "exploring"|"naming"|"ready_to_act"|"acting"|"checking_in",
 "phase_reason": "1 short line — why this phase now",
 "acknowledgment": "1-3 short sentences. MUST open with reflection of what the user said (quote or paraphrase). No question marks here.",
 "mirror": "1 gentle sentence: what they didn't say but is true beneath the message. Statement, not a question.",
 "insight": "REQUIRED, never empty: 1-2 short lines of genuinely useful value. Pick the type that fits, NOT always a number: a direct answer, a number or benchmark, a framework, a concrete example or template, a fork or trade-off, a warning, a lever or resource, or a sharper reframe. Localise to USER_LOCATION. No vague encouragement, no restating their words. When the user asked for a plan, put the short step-by-step shape (step 1 to step 4 or 5) here.",
 "refreshed_easiest_path": "1-2 lines in plain words — OR null when phase is exploring",
 "refreshed_next_action": "1 line: concrete action for next 24-48h — MUST be null when phase is exploring or naming",
 "outbox_alternative": "OPTIONAL 1-2 lines: when you propose a next_action, ALSO surface ONE non-obvious higher-leverage alternative the user probably hasn't considered. Format: 'Or, the outside-the-box play: X — because Y.' Use the user's location/context to make it specific. MUST be null when phase is exploring or naming, OR when the obvious next_action is already the best move.",
 "action_payoff": "1 easy-to-picture line: the concrete thing they hold within 48h of doing it — null unless phase is ready_to_act, acting, or checking_in",
 "big_picture_link": "1 line: how this action moves their stated goal, quantified where possible — null unless phase is ready_to_act, acting, or checking_in",
 "bold_move": "1-2 lines: the unconventional higher-leverage play, framed as an option, or null if none genuinely exists",
 "requested_input": "0-1 line OR null. ONLY when the next action's success requires a concrete piece of evidence the user can bring back next turn (a reply received, a screenshot, a number, a photo, a file). Be specific and warm: 'When Sara replies, paste her exact words here — I want to read them with you.' or 'Snap a photo of the page when you're done and drop it on me.' Return null when no evidence is needed OR when the answer is already in an attached file (compute it instead).",
 "file_facts": "STRUCTURED SNAPSHOT of the user's attached file (3-6 short lines: rows / columns / a key count / a key total / one anomaly) — populate ONLY when a file/image is attached this turn; otherwise return null. This will be saved on the thread so future turns can reason on the file without the user re-uploading.",
 "refreshed_open_question": "1 line: the single unresolved tension OR the consent question when phase is ready_to_act. The ONLY question mark in your entire reply.",
 "skip_list": ["0-2 things to deliberately ignore right now"],
 "state_summary": "3 short lines (\\n separated): where they are right now, in their own register",
 "signals": {"emotional_temperature": 0.0to1.0, "action_done": bool (did they report completing the prior next action), "contradiction": "string or null (tension between what they say and do)"}}"""

REQUIRED_KEYS = ("phase", "acknowledgment", "refreshed_open_question", "state_summary", "signals")
VALID_PHASES = ("exploring", "naming", "ready_to_act", "acting", "checking_in")

def llm_turn(thread: dict, substrate: dict, user_msg: str, intent: str, mode: str = "normal",
             attachment: dict | None = None, user_doc: dict | None = None,
             recall_block: str = "", attachment_preview: dict | None = None):
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
    prior_phase = (thread.get("current_phase") or "").strip() or "(none — this is an early turn)"
    geo = thread.get("user_geo") or {}
    geo_line = ""
    city, country = geo.get("city"), geo.get("country")
    if city and country and city not in ("Unknown", "Local"):
        geo_line = f"USER_LOCATION: {city}, {country} (anchor tool/platform/payment/regulation suggestions to here)\n"
    recall_section = (recall_block.strip() + "\n") if recall_block and recall_block.strip() else ""
    prompt = (
        f"{user_ctx_block}"
        f"{geo_line}"
        f"GOAL: {thread['goal']}\n"
        f"WHY IT MATTERS TO THEM (their words at the start): {thread.get('why_now', '(not stated)')}\n"
        f"STATE SUMMARY:\n{thread['current_state_summary']}\n"
        f"OPEN QUESTION: {thread['current_open_question']}\n"
        f"CURRENT EASIEST PATH: {thread['current_easiest_path']}\n"
        f"PRIOR NEXT ACTION (check if done): {thread['current_next_action']}\n"
        f"PRIOR PHASE: {prior_phase}\n"
        f"SUBSTRATE: temp={substrate['emotional_temperature']} consistency={substrate['execution_consistency']} pace={substrate['pace_calibration']} streak={substrate.get('streak', 0)} kept actions in a row\n"
        f"INTENT: {intent}\n"
        f"{adjust_note}"
        f"{facts_block}"
        f"{recall_section}"
        f"USER MESSAGE: {user_msg}"
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
            kwargs = {"model": model, "max_tokens": 1200, "system": system_blocks,
                      "messages": [{"role": "user", "content": user_content}]}
            if has_file_context and model != ULTRA_MODEL:
                kwargs["max_tokens"] = 3500  # room for richer analysis on file/recall turns
            if model == ULTRA_MODEL:
                kwargs["max_tokens"] = 8000  # room for thinking + JSON output
                kwargs["thinking"] = {"type": "adaptive"}
                kwargs["extra_body"] = {"output_config": {"effort": "high"}}
            r = client().messages.create(**kwargs)
            txt = next((b.text for b in r.content if getattr(b, "type", "") == "text"), "").strip()
            txt = re.sub(r"^```(json)?|```$", "", txt, flags=re.M).strip()
            out = json.loads(txt)
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
            # insight must always be a string (give-before-you-ask); default empty if model omitted it
            if not isinstance(out.get("insight"), str):
                out["insight"] = ""
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
