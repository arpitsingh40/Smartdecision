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
