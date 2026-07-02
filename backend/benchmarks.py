"""Cross-founder benchmarks: an EVOLVING aggregation structure, useful from day 1.

Design principles (per the founder's spec):
- No waiting for volume. The structure works with n=1 and simply gets richer forever.
- Honesty is the brand: every digest line carries its real sample size, and anything
  under MIN_SOLID_N is explicitly labelled an early signal, never a statistic.
- Zero extra LLM calls: facts are extracted inside the SAME turn call the user already
  pays for (journey turn / brain ask emit a small `benchmark_facts` field).
- Privacy: only numeric metric aggregates keyed by industry. No names, no emails, no
  conversation text, no org ids ever enter this collection. One sample per founder per
  metric (a founder updating their number replaces their sample, never double counts).

Doc shape in `benchmarks` collection (one per industry+metric):
  {id, industry, metric, unit, samples:[{uid_hash, value, at}], count, updated_at}
"""
import hashlib
import logging
import statistics
import uuid

from db import benchmarks_col

log = logging.getLogger("benchmarks")

MAX_SAMPLES = 200          # cap per (industry, metric); oldest replaced beyond this
MIN_SOLID_N = 5            # below this, digests label the line an "early signal"
MAX_DIGEST_LINES = 8

# crude normalisation so "Cloud Kitchen"/"cloud-kitchen" aggregate together
def _norm_key(s, max_len=60):
    return "-".join("".join(c.lower() if (c.isalnum() or c == " ") else " " for c in str(s or "")).split())[:max_len]


def _uid_hash(user_id):
    return hashlib.sha256(f"sdg-bench:{user_id}".encode()).hexdigest()[:16]


def _to_float(v):
    try:
        f = float(v)
        if f != f or f in (float("inf"), float("-inf")):
            return None
        return f
    except Exception:
        return None


def normalize_facts(raw):
    """Sanitize the LLM-emitted benchmark_facts blob -> (industry, [{metric,value,unit}]).
    Returns ("", []) when nothing usable was emitted."""
    if not isinstance(raw, dict):
        return "", []
    industry = _norm_key(raw.get("industry", ""))
    facts_in = raw.get("facts") if isinstance(raw.get("facts"), list) else []
    facts = []
    for f in facts_in[:10]:
        if not isinstance(f, dict):
            continue
        metric = _norm_key(f.get("metric", ""))
        value = _to_float(f.get("value"))
        if not metric or value is None:
            continue
        facts.append({"metric": metric, "value": value, "unit": str(f.get("unit", ""))[:24]})
    return industry, facts


def ingest_facts(user_id, industry, facts, now):
    """Fold one founder's facts into the evolving aggregates. Fire-and-forget safe:
    every failure is swallowed and logged, never breaks a turn."""
    if not industry or not facts:
        return 0
    uid = _uid_hash(user_id)
    written = 0
    for f in facts:
        try:
            doc = benchmarks_col.find_one({"industry": industry, "metric": f["metric"]})
            if not doc:
                benchmarks_col.insert_one({
                    "id": str(uuid.uuid4()), "industry": industry, "metric": f["metric"],
                    "unit": f.get("unit", ""),
                    "samples": [{"uid": uid, "value": f["value"], "at": now}],
                    "count": 1, "updated_at": now})
                written += 1
                continue
            samples = [s for s in (doc.get("samples") or []) if s.get("uid") != uid]
            samples.append({"uid": uid, "value": f["value"], "at": now})
            samples = samples[-MAX_SAMPLES:]
            benchmarks_col.update_one({"id": doc["id"]}, {"$set": {
                "samples": samples, "count": len(samples),
                "unit": f.get("unit") or doc.get("unit", ""), "updated_at": now}})
            written += 1
        except Exception as e:
            log.warning(f"benchmark ingest failed metric={f.get('metric')}: {e}")
    return written


def benchmark_digest(industry):
    """Compact, honest text block of what the platform ACTUALLY knows about this industry.
    Returns "" when nothing is known yet (the engine then relies on its own knowledge)."""
    industry = _norm_key(industry)
    if not industry:
        return ""
    try:
        rows = list(benchmarks_col.find({"industry": industry})
                    .sort("count", -1).limit(MAX_DIGEST_LINES))
    except Exception as e:
        log.warning(f"benchmark digest failed: {e}")
        return ""
    lines = []
    for r in rows:
        vals = [s.get("value") for s in (r.get("samples") or []) if _to_float(s.get("value")) is not None]
        if not vals:
            continue
        n = len(vals)
        med = statistics.median(vals)
        unit = (r.get("unit") or "").strip()
        u = f" {unit}" if unit else ""
        tag = "" if n >= MIN_SOLID_N else " (EARLY SIGNAL, small sample)"
        if n == 1:
            lines.append(f"- {r['metric']}: one founder reported {vals[0]:g}{u}{tag}")
        else:
            lines.append(f"- {r['metric']}: n={n} founders, median {med:g}{u}, "
                         f"range {min(vals):g} to {max(vals):g}{u}{tag}")
    if not lines:
        return ""
    return ("REAL PLATFORM BENCHMARKS for this industry (from actual founders using this product; "
            f"n = distinct founders; anything under n={MIN_SOLID_N} is an early signal, NOT a statistic. "
            "You may cite these as 'founders on this platform report...' with the sample size. "
            "NEVER present an early signal as an established benchmark):\n" + "\n".join(lines))


def ensure_benchmarks_startup():
    """Idempotent indexes for the benchmarks collection."""
    benchmarks_col.create_index("id", unique=True)
    benchmarks_col.create_index([("industry", 1), ("metric", 1)], unique=True)
