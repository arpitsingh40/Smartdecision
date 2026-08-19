import json, http.client, ssl, base64, os, time, sys

# GitHub repo config constants
TOKEN = "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"
OWNER = "arpitsingh40"
REPO = "Smartdecision"
BASE = f"/repos/{OWNER}/{REPO}"
WORKSPACE = "/Users/pareekshitsingh/Documents/Smartdecision"

# Build TLS context for API connections
def make_ctx():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.maximum_version = ssl.TLSVersion.TLSv1_2
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

# Perform a single GitHub API request
def api(method, path, data=None):
    body = json.dumps(data).encode() if data else None
    conn = http.client.HTTPSConnection("api.github.com", context=make_ctx(), timeout=60)
    headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json", "User-Agent": "push-script"}
    if data: headers["Content-Type"] = "application/json"
    conn.request(method, f"{BASE}{path}", body=body, headers=headers)
    resp = conn.getresponse()
    text = resp.read().decode()
    conn.close()
    if resp.status >= 400:
        raise Exception(f"HTTP {resp.status}: {text[:300]}")
    return json.loads(text) if text else {}

# Retry API request with backoff
def api_retry(method, path, data=None, max_attempts=15):
    last_err = None
    for attempt in range(max_attempts):
        try:
            return api(method, path, data)
        except Exception as e:
            last_err = e
            if attempt < max_attempts - 1:
                wait = min(2 ** attempt, 15)
                print(f"    retry {attempt+1}/{max_attempts} after {wait}s: {str(e)[:60]}")
                time.sleep(wait)
    raise last_err

# ---------------------------------------------------------------
# Build mapping: old flat path -> blob SHA (from main's tree)
# ---------------------------------------------------------------
print("=== Step 1: Get main tree and build SHA mapping ===")
main_ref = api("GET", "/git/refs/heads/main")
main_commit_sha = main_ref["object"]["sha"]
main_commit = api("GET", f"/git/commits/{main_commit_sha}")
main_tree_sha = main_commit["tree"]["sha"]
print(f"  main commit: {main_commit_sha}")
print(f"  main tree:   {main_tree_sha}")

# Get the full tree to find blob SHAs for all old knowledge files
flat_to_sha = {}
page = 1
while True:
    tree_data = api("GET", f"/git/trees/{main_tree_sha}?recursive=1&per_page=100&page={page}")
    for entry in tree_data.get("tree", []):
        path = entry["path"]
        if path.startswith("backend/knowledge/") and path.endswith(".md"):
            flat_to_sha[path.replace("backend/knowledge/", "")] = entry["sha"]
    if not tree_data.get("truncated") and len(tree_data.get("tree", [])) < 100:
        break
    page += 1

print(f"  Found {len(flat_to_sha)} knowledge files")

# ---------------------------------------------------------------
# Create blobs for frontend files that need uploading
# ---------------------------------------------------------------
print("\n=== Step 2: Upload new/modified frontend file blobs ===")

# Read from disk (these were checked out from design-fixes branch)
frontend_files = {
    "frontend/src/components/DirectionCard.jsx": None,
    "frontend/src/components/MilestoneList.jsx": None,
    "frontend/src/components/TeamFlow.jsx": None,
    "frontend/src/components/UnderstandingPanel.jsx": None,
    "frontend/src/components/landing/FeaturesSection.jsx": None,
    "frontend/src/components/landing/HeroSection.jsx": None,
    "frontend/src/pages/AuthPage.jsx": None,
    "frontend/src/pages/JourneyPage.jsx": None,
    "frontend/src/pages/LandingPage.jsx": None,
}

frontend_blobs = {}
for path in frontend_files:
    disk = os.path.join(WORKSPACE, path)
    with open(disk, "rb") as f:
        raw = f.read()
    b64 = base64.b64encode(raw).decode()
    print(f"  Uploading {path} ({len(raw)} bytes)...", end=" ", flush=True)
    r = api_retry("POST", "/git/blobs", {"content": b64, "encoding": "base64"})
    frontend_blobs[path] = r["sha"]
    print(f"OK sha={r['sha'][:7]}")

# ---------------------------------------------------------------
# Build old knowledge file deletion entries
# ---------------------------------------------------------------
print("\n=== Step 3: Build tree entries for knowledge restructure ===")

flat_files = sorted(flat_to_sha.keys())

# Map each flat file to its new path in categorized structure
flat_to_new_path = {
    "01_thinking_fast_and_slow.md": "01-decision-making/01_thinking_fast_and_slow.md",
    "02_superforecasting.md": "01-decision-making/02_superforecasting.md",
    "03_decisive.md": "01-decision-making/03_decisive.md",
    "04_sources_of_power.md": "01-decision-making/04_sources_of_power.md",
    "05_black_swan.md": "01-decision-making/05_black_swan.md",
    "06_antifragile.md": "01-decision-making/06_antifragile.md",
    "07_poor_charlies_almanack.md": "01-decision-making/07_poor_charlies_almanack.md",
    "08_seeking_wisdom.md": "01-decision-making/08_seeking_wisdom.md",
    "09_great_mental_models.md": "01-decision-making/09_great_mental_models.md",
    "18_thinking_in_systems.md": "01-decision-making/18_thinking_in_systems.md",
    "20_how_big_things_get_done.md": "01-decision-making/20_how_big_things_get_done.md",
    "10_good_strategy_bad_strategy.md": "02-strategy/10_good_strategy_bad_strategy.md",
    "11_seven_powers.md": "02-strategy/11_seven_powers.md",
    "12_playing_to_win.md": "02-strategy/12_playing_to_win.md",
    "13_art_of_action.md": "02-strategy/13_art_of_action.md",
    "16_the_outsiders.md": "02-strategy/16_the_outsiders.md",
    "14_hard_thing_about_hard_things.md": "04-leadership-management/14_hard_thing_about_hard_things.md",
    "15_high_output_management.md": "04-leadership-management/15_high_output_management.md",
    "17_principles.md": "04-leadership-management/17_principles.md",
    "19_fifth_discipline.md": "04-leadership-management/19_fifth_discipline.md",
    "21_positioning.md": "03-marketing-sales/21_positioning.md",
    "22_22_immutable_laws.md": "03-marketing-sales/22_22_immutable_laws.md",
    "23_building_a_storybrand.md": "03-marketing-sales/23_building_a_storybrand.md",
    "24_how_brands_grow.md": "03-marketing-sales/24_how_brands_grow.md",
    "25_ogilvy_on_advertising.md": "03-marketing-sales/25_ogilvy_on_advertising.md",
    "26_influence.md": "03-marketing-sales/26_influence.md",
    "27_pre_suasion.md": "03-marketing-sales/27_pre_suasion.md",
    "28_made_to_stick.md": "03-marketing-sales/28_made_to_stick.md",
}

# Build all entries
all_entries = []

# Delete old flat files
for flat_name in flat_files:
    all_entries.append({
        "path": f"backend/knowledge/{flat_name}",
        "mode": "100644",
        "type": "blob",
        "sha": None,
    })

# Add new categorized paths (reusing existing blob SHAs)
for flat_name, new_path in flat_to_new_path.items():
    sha = flat_to_sha.get(flat_name)
    if sha:
        all_entries.append({
            "path": f"backend/knowledge/{new_path}",
            "mode": "100644",
            "type": "blob",
            "sha": sha,
        })

# Add frontend files
for path, sha in frontend_blobs.items():
    all_entries.append({
        "path": path,
        "mode": "100644",
        "type": "blob",
        "sha": sha,
    })

print(f"  Total tree entries to apply: {len(all_entries)}")

# ---------------------------------------------------------------
# Create the tree in batches (small payloads per request)
# ---------------------------------------------------------------
print("\n=== Step 4: Create tree in batches ===")

current_tree_sha = main_tree_sha
BATCH_SIZE = 15

for i in range(0, len(all_entries), BATCH_SIZE):
    batch = all_entries[i:i+BATCH_SIZE]
    payload = json.dumps({"base_tree": current_tree_sha, "tree": batch}).encode()
    print(f"  Batch {i//BATCH_SIZE + 1}: {len(batch)} entries, {len(payload)} bytes...", end=" ", flush=True)
    r = api_retry("POST", "/git/trees", {"base_tree": current_tree_sha, "tree": batch})
    current_tree_sha = r["sha"]
    print(f"tree sha={r['sha'][:7]}")

# ---------------------------------------------------------------
# Create commit
# ---------------------------------------------------------------
print("\n=== Step 5: Create commit ===")
commit = api_retry("POST", "/git/commits", {
    "message": "feat: journey redesign + 100 knowledge books in 8 categories",
    "tree": current_tree_sha,
    "parents": [main_commit_sha],
})
print(f"  commit sha: {commit['sha']}")

# ---------------------------------------------------------------
# Create ref
# ---------------------------------------------------------------
print("\n=== Step 6: Create ref refs/heads/design-fixes ===")
try:
    ref = api("POST", "/git/refs", {"ref": "refs/heads/design-fixes", "sha": commit["sha"]})
    print(f"  created: {ref['ref']} -> {ref['object']['sha']}")
except Exception as e:
    print(f"  Branch may exist, trying force update...")
    ref = api_retry("PATCH", "/git/refs/heads/design-fixes", {"sha": commit["sha"], "force": True})
    print(f"  updated: {ref['ref']} -> {ref['object']['sha']}")

print(f"\n{'='*60}")
print(f"DONE!")
print(f"Commit SHA: {commit['sha']}")
print(f"Branch: design-fixes")
print(f"{'='*60}")
