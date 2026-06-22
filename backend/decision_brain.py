"""Decision Brain — Step 0 POC.

One ask box for a whole company. A user (owner, manager, or ground employee) types a
question, a judgment call, or an objective. We retrieve from the company's own documents
(reusing doc_memory's RAPTOR tree + local embeddings) and make ONE grounded LLM call that
auto-routes to ANSWER / DECIDE / PLAN, cites its sources, and refuses to invent facts.

Isolated from the existing coach engine: new router (/api/brain), its own retrieval over a
per-user knowledge-base namespace, never modifies engine.py or doc_memory.py behaviour.
"""
import os
import re
import json
import math
import uuid
import base64
import logging
from datetime import datetime, timezone

import numpy as np
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from pymongo import ReturnDocument

import doc_memory
from engine import client
from db import users_col, db
from security import current_user

log = logging.getLogger("brain")
router = APIRouter(prefix="/api/brain")

trees_col = db.doc_trees
nodes_col = db.doc_nodes

PRIMARY_MODEL = "claude-sonnet-4-5"   # grounded analysis: same context as Opus, ~5x cheaper
FALLBACK_MODEL = "claude-haiku-4-5"

CREDITS_PER_1K_TOKENS = int(os.environ.get("CREDITS_PER_1K_TOKENS", "2"))
BRAIN_RESERVE = int(os.environ.get("BRAIN_RESERVE", "16"))   # ~8k tokens; refund unused

TOP_CHAPTERS = 3
TOP_PASSAGES = 6
MAX_KB_TREES = 25            # how many docs we scan per query (well above POC needs)
SNIPPET_CHARS = 1000
IMAGE_PREFIX = "image/"

SUPPORTED_HINT = "PDF, Word (.docx), PowerPoint (.pptx), Excel (.xlsx), CSV, Markdown, HTML, JSON, or plain text"


def now_utc():
    return datetime.now(timezone.utc)


def kb_id(user_id: str) -> str:
    """The knowledge-base namespace for a user (stored in the doc_memory tree's thread_id field)."""
    return f"kb_{user_id}"


def token_cost(tin: int, tout: int) -> int:
    total = (tin or 0) + (tout or 0)
    return max(1, math.ceil(total / 1000) * CREDITS_PER_1K_TOKENS)


# ---------------------------------------------------------------- retrieval (KB-scoped)
def kb_retrieve(user_id: str, question: str):
    """Hierarchical retrieval over ALL ready docs in the user's KB.
    Returns (passages, doc_map_text, doc_names). passages = [{doc, chapter, score, text}]."""
    kid = kb_id(user_id)
    trees = list(trees_col.find({"thread_id": kid, "status": "ready"}).limit(MAX_KB_TREES))
    doc_names = [t.get("filename", "document") for t in trees]
    if not trees:
        return [], "", doc_names
    try:
        qvec = doc_memory._embed_one(question)
    except Exception as e:
        log.warning(f"kb embed failed: {e}")
        return [], "", doc_names

    chosen = []          # [(score, filename, chapter_title, text)]
    doc_map_lines = []
    for tr in trees:
        tid = tr["tree_id"]
        fname = tr.get("filename", "document")
        chapters = list(nodes_col.find({"tree_id": tid, "level": 1}))
        if not chapters:
            continue
        scored_ch = []
        for ch in chapters:
            vec = np.array(ch.get("summary_embedding") or [], dtype=np.float32)
            if vec.size:
                scored_ch.append((doc_memory._cos(qvec, vec), ch))
        scored_ch.sort(key=lambda x: x[0], reverse=True)
        top_ch = scored_ch[:TOP_CHAPTERS]
        if scored_ch:
            doc_map_lines.append(f"From '{fname}':")
            for s, ch in scored_ch[:5]:
                mark = " <-- relevant" if (s, ch) in top_ch else ""
                doc_map_lines.append(f"  - {ch.get('title', 'section')} [score {s:.2f}]{mark}")
        for s_ch, ch in top_ch:
            paras = list(nodes_col.find({"tree_id": tid, "parent_id": ch["node_id"], "level": 4}))
            scored_p = []
            for p in paras:
                pv = np.array(p.get("text_embedding") or [], dtype=np.float32)
                if pv.size:
                    scored_p.append((doc_memory._cos(qvec, pv), fname, ch.get("title", "section"), p.get("text") or ""))
            scored_p.sort(key=lambda x: x[0], reverse=True)
            chosen.extend(scored_p[:TOP_PASSAGES])

    chosen.sort(key=lambda x: x[0], reverse=True)
    chosen = chosen[:TOP_PASSAGES]
    passages = [{"doc": c[1], "chapter": c[2], "score": round(float(c[0]), 2), "text": (c[3] or "")[:SNIPPET_CHARS]}
                for c in chosen]
    return passages, "\n".join(doc_map_lines), doc_names


# ---------------------------------------------------------------- the single LLM call
SYSTEM = """You are SmartDeciGen's Decision Brain for a company. You serve everyone from the owner to a ground-floor employee. Read the user's message and decide which ONE of three jobs it needs, then do exactly that job:

- ANSWER: a factual question about the company's own documents. Give the direct answer, grounded ONLY in the RETRIEVED_PASSAGES, and name the source.
- DECIDE: a judgment call ("should we...", "what do I do about...", "is it okay to..."). Recommend the single best option FOR THE COMPANY, using the documents and COMPANY_RULES when present. Give a short, plain reason.
- PLAN: the user names an objective or asks how to achieve something. Produce a tight, ordered, realistic plan of concrete steps to reach it, anchored to the company's real situation from the documents where relevant.

HARD RULES:
- Ground every factual claim in a RETRIEVED_PASSAGE. Cite each source you used as its document name and chapter.
- If the mode is ANSWER and the answer is NOT in the passages, set found_in_docs=false and say plainly that you could not find it in the company's documents. NEVER invent a policy, number, date, name, or fact.
- For DECIDE and PLAN you may reason beyond the documents, but anchor to documented facts whenever they exist and NEVER contradict COMPANY_RULES.
- Plain English. Short sentences. No fluff, no emojis, no em-dashes, no exclamation marks.

Return ONLY valid JSON, no markdown fences:
{"mode": "answer" | "decide" | "plan",
 "found_in_docs": true or false,
 "answer": "the main response. For answer mode: the direct answer. For decide mode: a short read of the situation. For plan mode: one line naming the objective.",
 "recommendation": "decide mode ONLY: 1-3 lines stating the company-favoured choice and why. Otherwise null.",
 "plan": ["plan mode ONLY: ordered concrete steps, each one short line"] or null,
 "citations": [{"doc": "document name", "chapter": "chapter title"}],
 "confidence": "high" | "medium" | "low"}"""

REQUIRED = ("mode", "answer")
VALID_MODES = ("answer", "decide", "plan")


def _clean(s):
    if isinstance(s, str):
        return s.replace("—", ", ").replace("–", ", ").strip()
    return s


def brain_answer(question: str, passages: list, doc_names: list, instructions: str):
    """ONE LLM call. Returns (out_dict, model, usage)."""
    if passages:
        psg = "\n\n".join(f"[{p['doc']} -> {p['chapter']}] (score {p['score']})\n{p['text']}" for p in passages)
        passages_block = f"RETRIEVED_PASSAGES (the most relevant evidence from the company's documents):\n{psg}\n\n"
    else:
        passages_block = "RETRIEVED_PASSAGES: (none found in the company's documents for this message)\n\n"
    docs_line = f"DOCUMENTS IN THE COMPANY KNOWLEDGE BASE: {', '.join(doc_names) if doc_names else '(none uploaded yet)'}\n"
    rules_block = f"COMPANY_RULES (set by the admin, treat as policy you must respect):\n{instructions.strip()}\n\n" if (instructions or "").strip() else ""
    prompt = f"{docs_line}\n{rules_block}{passages_block}USER MESSAGE: {question}"

    system_blocks = [{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}]
    last_err = None
    for model in (PRIMARY_MODEL, FALLBACK_MODEL):
        try:
            r = client().messages.create(model=model, max_tokens=1600, system=system_blocks,
                                         messages=[{"role": "user", "content": prompt}])
            txt = next((b.text for b in r.content if getattr(b, "type", "") == "text"), "").strip()
            txt = re.sub(r"^```(json)?|```$", "", txt, flags=re.M).strip()
            out = json.loads(txt)
            if not all(k in out for k in REQUIRED):
                raise ValueError("incomplete JSON")
            # guardrails
            mode = str(out.get("mode", "answer")).lower().strip()
            out["mode"] = mode if mode in VALID_MODES else "answer"
            out["found_in_docs"] = bool(out.get("found_in_docs")) if passages else False
            out["answer"] = _clean(out.get("answer", ""))
            out["recommendation"] = _clean(out.get("recommendation")) if out.get("mode") == "decide" else None
            plan = out.get("plan")
            out["plan"] = [_clean(s) for s in plan if isinstance(s, str) and s.strip()] if (out.get("mode") == "plan" and isinstance(plan, list)) else None
            cits = out.get("citations")
            out["citations"] = [{"doc": str(c.get("doc", "")), "chapter": str(c.get("chapter", ""))}
                                for c in cits if isinstance(c, dict)] if isinstance(cits, list) else []
            if out.get("confidence") not in ("high", "medium", "low"):
                out["confidence"] = "medium"
            usage = {"input_tokens": int(getattr(r.usage, "input_tokens", 0) or 0),
                     "output_tokens": int(getattr(r.usage, "output_tokens", 0) or 0)}
            return out, model, usage
        except Exception as e:
            last_err = e
    raise RuntimeError(f"All models failed: {last_err}")


# ---------------------------------------------------------------- models
class UploadIn(BaseModel):
    filename: str = Field(min_length=1, max_length=300)
    mime: str = ""
    base64: str = Field(min_length=1)


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class SettingsIn(BaseModel):
    instructions: str = Field(default="", max_length=4000)


# ---------------------------------------------------------------- endpoints
@router.post("/upload")
def upload(body: UploadIn, background: BackgroundTasks, user: dict = Depends(current_user)):
    """Ingest a document into the user's company knowledge base. Every doc becomes a queryable tree."""
    mime = (body.mime or "").lower()
    if mime.startswith(IMAGE_PREFIX):
        raise HTTPException(415, f"Images aren't supported in the knowledge base yet. Upload {SUPPORTED_HINT}.")
    if len(body.base64) > 12_000_000:
        raise HTTPException(413, "File too large. Keep documents under 8 MB.")
    try:
        raw = base64.b64decode(body.base64)
    except Exception:
        raise HTTPException(400, "Could not decode the file.")
    try:
        kind, full_text, chapters = doc_memory.parse_file(body.filename, mime, raw)
    except Exception as e:
        raise HTTPException(422, f"Could not read this file: {e}")
    if not (full_text or "").strip():
        raise HTTPException(422, "This file appears to be empty or unreadable.")

    tree_id = "tree_" + uuid.uuid4().hex[:16]
    trees_col.insert_one({
        "tree_id": tree_id, "thread_id": kb_id(user["id"]), "owner_id": user["id"],
        "filename": body.filename, "mime": mime, "kind": kind, "status": "processing",
        "total_chars": len(full_text), "node_count": 0,
        "created_at": now_utc().isoformat(),
    })
    background.add_task(doc_memory.build_tree_sync, tree_id, full_text, chapters, body.filename)
    return {"tree_id": tree_id, "filename": body.filename, "status": "processing",
            "total_chars": len(full_text)}


@router.get("/documents")
def documents(user: dict = Depends(current_user)):
    docs = list(trees_col.find(
        {"thread_id": kb_id(user["id"])},
        {"_id": 0, "tree_id": 1, "filename": 1, "status": 1, "node_count": 1,
         "kind": 1, "created_at": 1, "doc_summary": 1, "total_chars": 1},
    ).sort("created_at", -1).limit(100))
    return {"documents": docs,
            "ready_count": sum(1 for d in docs if d.get("status") == "ready")}


@router.delete("/documents/{tree_id}")
def delete_document(tree_id: str, user: dict = Depends(current_user)):
    tr = trees_col.find_one({"tree_id": tree_id, "thread_id": kb_id(user["id"])})
    if not tr:
        raise HTTPException(404, "Document not found")
    nodes_col.delete_many({"tree_id": tree_id})
    trees_col.delete_one({"tree_id": tree_id})
    return {"ok": True}


@router.get("/settings")
def get_settings(user: dict = Depends(current_user)):
    u = users_col.find_one({"id": user["id"]}) or {}
    return {"instructions": u.get("brain_instructions", "")}


@router.post("/settings")
def set_settings(body: SettingsIn, user: dict = Depends(current_user)):
    users_col.update_one({"id": user["id"]}, {"$set": {"brain_instructions": body.instructions.strip()}})
    return {"ok": True, "instructions": body.instructions.strip()}


@router.post("/ask")
def ask(body: AskIn, user: dict = Depends(current_user)):
    # reserve credits, run one LLM call, reconcile to actual token usage
    reserve = BRAIN_RESERVE
    u = users_col.find_one_and_update({"id": user["id"], "credits": {"$gte": reserve}},
                                      {"$inc": {"credits": -reserve}}, return_document=ReturnDocument.AFTER)
    if not u:
        raise HTTPException(402, "Not enough credits")
    try:
        passages, doc_map, doc_names = kb_retrieve(user["id"], body.question.strip())
        instructions = (u.get("brain_instructions") or "")
        out, model, usage = brain_answer(body.question.strip(), passages, doc_names, instructions)
    except Exception as e:
        try:
            users_col.update_one({"id": user["id"]}, {"$inc": {"credits": reserve}})  # full refund
        except Exception as refund_err:
            log.error(f"CRITICAL: brain refund failed user={user['id']}: {refund_err}")
        log.error(f"brain ask failed: {e}")
        raise HTTPException(502, "The brain could not respond. You were not charged, please try again.")

    actual = token_cost(usage["input_tokens"], usage["output_tokens"])
    refund = max(0, reserve - actual)
    if refund:
        u = users_col.find_one_and_update({"id": user["id"]}, {"$inc": {"credits": refund}},
                                          return_document=ReturnDocument.AFTER)
    users_col.update_one({"id": user["id"]}, {
        "$inc": {"tokens_in": usage["input_tokens"], "tokens_out": usage["output_tokens"]},
        "$set": {"last_active_at": now_utc()}})

    return {**out, "model": model, "credits": u.get("credits", 0),
            "cost": actual, "tokens": usage["input_tokens"] + usage["output_tokens"],
            "sources_found": len(passages), "docs_in_kb": len(doc_names)}
