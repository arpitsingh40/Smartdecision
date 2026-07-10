"""Single Mongo client shared by every module (no duplicate connections).
All collection handles live here so routers never create their own clients."""
import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ.get("MONGO_URL", "")
mongo = MongoClient(mongo_url, maxPoolSize=100, serverSelectionTimeoutMS=5000) if mongo_url else None
_db = mongo[os.environ.get("DB_NAME", "test_database")] if mongo else None


def _col(name):
    return _db[name] if _db is not None else None


users_col = _col("users")
threads_col = _col("goal_threads")
events_col = _col("substrate_events")
telemetry_col = _col("telemetry_events")
ledger_col = _col("credit_ledger")
stats_col = _col("stats")
traffic_col = _col("traffic_sessions")
geo_col = _col("geo_cache")
orders_col = _col("payment_orders")
feedback_col = _col("feedback")
orgs_col = _col("organizations")
members_col = _col("org_members")
invites_col = _col("org_invites")
decisions_col = _col("decisions")
plans_col = _col("org_plans")
journeys_col = _col("journeys")
shares_col = _col("shares")
benchmarks_col = _col("benchmarks")
kpi_events_col = _col("kpi_events")
gates_col = _col("release_gates")
tasks_col = _col("tasks")
subscriptions_col = _col("subscriptions")
token_usage_col = _col("token_usage")
