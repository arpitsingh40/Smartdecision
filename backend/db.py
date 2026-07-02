"""Single Mongo client shared by every module (no duplicate connections).
All collection handles live here so routers never create their own clients."""
import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo = MongoClient(os.environ["MONGO_URL"], maxPoolSize=100)
db = mongo[os.environ.get("DB_NAME", "test_database")]

users_col = db.users
threads_col = db.goal_threads
events_col = db.substrate_events
telemetry_col = db.telemetry_events
ledger_col = db.credit_ledger          # every credit movement (grant/purchase/spend)
stats_col = db.stats                   # single pre-aggregated counters doc (O(1) admin reads)
traffic_col = db.traffic_sessions      # visitor sessions: ip/city/country/time-spent
geo_col = db.geo_cache                 # ip -> city/country (permanent cache, 1 lookup per ip ever)
orders_col = db.payment_orders         # zoho top-up orders (immutable amounts + status history)
feedback_col = db.feedback             # user feedback (rating/category/message, founder-reviewed)
orgs_col = db.organizations            # one row per company workspace (+ hidden strategy in Phase 2)
members_col = db.org_members           # user <-> org membership with role (owner|member)
invites_col = db.org_invites           # invite codes / join links for a company workspace
decisions_col = db.decisions           # every brain decision (history, execution status, founder-only alignment)
plans_col = db.org_plans               # Layer 6: founder-ratified objective cascades (autonomous planning)
journeys_col = db.journeys             # chat-first founder journey: live understanding model + stage + unlocks
shares_col = db.shares                 # public Decision Cards (virality layer): share links, views, second opinions
benchmarks_col = db.benchmarks         # evolving cross-founder aggregates: (industry, metric) -> samples/stats
kpi_events_col = db.kpi_events         # one-tap launch-KPI signals (problem detection / decision improvement)
gates_col = db.release_gates           # release-gate runs (four gates: truth/reasoning/actionability/impact)
