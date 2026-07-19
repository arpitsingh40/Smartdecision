"""SALAAR — The Shadow Agent.
Awareness → Threat Detection → Action → People → Insight → Shadow Summary.

Key entry points:
  salaar_realtime_scan() — run every 5 min (wired to server scheduler)
  salaar_deep_scan()     — run every 30 min (wired to server scheduler)
  scan_org(org_id)       — manual trigger for a single org
"""
from .engine import salaar_realtime_scan, salaar_deep_scan, scan_org, deep_scan_org
from .insight import generate_salaar_brief, generate_people_insight
