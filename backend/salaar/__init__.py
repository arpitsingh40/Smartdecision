"""SALAAR — The Shadow Agent.
Awareness → Threat Detection → Action → People → Causal Chain → Execution.

Key entry points:
  salaar_realtime_scan() — run every 5 min (wired to server scheduler)
  salaar_deep_scan()     — run every 30 min (wired to server scheduler)
  scan_org(org_id)       — manual trigger for a single org
  build_actor_map()       — build complete incentive profiles for all actors
  simulate_causal_chain() — forward-simulate if-this-then-that chain
  execute_chain_step()    — execute one link via internet tools
"""
from .engine import salaar_realtime_scan, salaar_deep_scan, scan_org, deep_scan_org
from .insight import generate_salaar_brief, generate_people_insight
from .causal import build_actor_map, simulate_causal_chain, execute_chain_step
