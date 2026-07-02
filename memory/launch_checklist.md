# SmartDecigen — Founder Decision Intelligence Launch Checklist (founder-agreed, July 2026)

> Companion to strategy_north_star.md. This is the RELEASE-READINESS framework.
> Not "does it work?" but "can founders consistently make better decisions because of it?"

## The 12 pre-launch checks (launch only if…)
| Priority | Check | Launch only if… |
|---|---|---|
| 5⭐ | Decision Quality | AI consistently produces decisions expert founders agree are useful |
| 5⭐ | Problem Discovery | Finds the user's REAL problem, not the surface question |
| 5⭐ | Clarifying Questions | Asks only the minimum questions needed to raise decision quality |
| 5⭐ | Reasoning | Every recommendation includes assumptions, evidence, trade-offs, risks, confidence |
| 5⭐ | Execution | Every conversation ends with concrete action plan + measurable next steps |
| 4⭐ | Memory | Remembers relevant context; users never repeat themselves |
| 4⭐ | Knowledge | Knows when it lacks info and ASKS instead of guessing |
| 4⭐ | Accuracy | Facts, calculations, recommendations consistently correct |
| 4⭐ | UX | Founder gets value within first 2–3 minutes |
| 4⭐ | Speed | Responses stay fast even during deep reasoning |
| 4⭐ | Reliability | Long conversations never lose context / go inconsistent |
| 5⭐ | Trust | Users understand WHY a recommendation was made and when NOT to follow it |

## The 5 launch KPIs
1. Problem Detection Accuracy — did the AI identify the actual business problem?
2. Decision Improvement Rate — did founders change/improve their decision after using it?
3. Execution Rate — did users complete the recommended actions?
4. Outcome Improvement — did those actions improve measurable business results?
5. Return Rate — do founders come back because it helped them decide better?

## The one question before every release
"If a founder follows this conversation exactly, will they make a meaningfully better
decision than they would have without SmartDecigen?" Not confidently yes -> don't launch.

## The four gates (every release must pass ALL)
- Truth — is the information correct?
- Reasoning — is the logic sound?
- Actionability — can the founder act immediately?
- Impact — does it raise the probability of a better business outcome?

## North-star metric
DECISION QUALITY — not engagement, tokens, or conversation length.

## Honest product-vs-checklist gap map (assessed July 2026)
BUILT & STRONG: Problem Discovery (10-dim uncertainty sweep + hidden_desire), Clarifying
Questions (one highest-EV question + sufficient stop-rule), Reasoning (public trace,
server-computed confidence), Execution (next_action always + commit/done + milestones),
Memory (understanding trail + learning digest + founder profile), Knowledge partial
(grounding guardrail + ASK-BEFORE-ASSUME; NO live web = Organ 3 gap).
GAPS: (1) Decision Quality has no repeatable eval harness / golden-scenario release gate;
(2) Accuracy has no fact-check layer; (3) Trust lacks explicit "when NOT to follow this"
in recommendations; (4) KPIs 1, 2, 4 are NOT instrumented (KPI 3 = follow_through_pct
exists; KPI 5 partial via traffic sessions). Organ 1 (Decision Record + outcome loop,
predicted vs actual + Rs impact) is the single build that powers KPIs 2/3/4 + Impact gate.
