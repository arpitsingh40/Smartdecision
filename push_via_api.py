#!/usr/bin/env python3
"""Push current commit to GitHub via Git Data API (blob by blob, tree, commit, ref)."""
import base64, json, os, sys, time, subprocess, urllib.request, urllib.error

# GitHub auth and repo config constants
TOKEN = os.environ.get("GH_PAT") or input("GH_PAT: ").strip()
if not TOKEN:
    sys.exit("Need GH_PAT")
OWNER, REPO = "arpitsingh40", "Smartdecision"
API = "https://api.github.com"
H = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}

# Send API request with retry loop
def req(method, url, **kw):
    h = dict(H); data = None
    if "json" in kw:
        data = json.dumps(kw["json"]).encode(); h["Content-Type"] = "application/json"
    for i in range(25):
        r = urllib.request.Request(url, data=data, headers=h, method=method)
        try:
            with urllib.request.urlopen(r, timeout=60) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            if e.code == 401: sys.exit("Token invalid")
            if e.code == 422: print(f"  422: {body[:200]}"); return None
            print(f"  retry {i+1} {e.code}", flush=True)
        except Exception as e:
            print(f"  retry {i+1} {type(e).__name__}", flush=True)
        time.sleep(5)
    return None

# Get current HEAD  
head_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
msg = subprocess.check_output(["git", "log", "--format=%B", "-1", "HEAD"], text=True).strip()

# Always get parent from API (local ref may be stale)
print("Getting parent from API...")
r = req("GET", f"{API}/repos/{OWNER}/{REPO}/git/ref/heads/main")
parent_sha = r["object"]["sha"] if r else None
if not parent_sha:
    sys.exit("Cannot determine parent")

print(f"Parent: {parent_sha[:12]}")
print(f"HEAD:   {head_sha[:12]}")

# Get tree from HEAD commit
tree_sha = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], text=True).strip()
print(f"Tree:   {tree_sha[:12]}")

# List tree entries
entries_raw = subprocess.check_output(["git", "ls-tree", "-r", "HEAD"], text=True).strip().split("\n")
entries = []
for line in entries_raw:
    if not line.strip(): continue
    mode, typ, sha, path = line.split(None, 3)
    if path.startswith("ui-ux-pro-max-skill"): continue
    if path == "push_via_api.py": continue
    entries.append({"path": path, "mode": mode, "type": typ, "sha": sha})

print(f"Entries: {len(entries)}")

# Get parent tree SHA so we can skip unchanged blobs
parent_commit = req("GET", f"{API}/repos/{OWNER}/{REPO}/git/commits/{parent_sha}")
parent_tree_sha = parent_commit["tree"]["sha"] if parent_commit else ""
parent_tree = req("GET", f"{API}/repos/{OWNER}/{REPO}/git/trees/{parent_tree_sha}?recursive=1") if parent_tree_sha else None
parent_blobs = {}
if parent_tree and not parent_tree.get("truncated"):
    for item in parent_tree.get("tree", []):
        parent_blobs[item["path"]] = item["sha"]

# Upload blobs that don't exist on remote
print(f"\nUploading blobs ({len(parent_blobs)} known on remote, skipping unchanged)...")
skipped = 0
for i, e in enumerate(entries):
    if parent_blobs.get(e["path"]) == e["sha"]:
        skipped += 1
        continue
    print(f"  [{i+1}/{len(entries)}] {e['path']}...", end=" ", flush=True)
    payload = {"content": base64.b64encode(subprocess.check_output(["git", "cat-file", "-p", e["sha"]])).decode(), "encoding": "base64"}
    r = req("POST", f"{API}/repos/{OWNER}/{REPO}/git/blobs", json=payload)
    if r:
        e["sha"] = r["sha"]
        print(f"ok")
    else:
        print(f"FAILED")
        sys.exit(1)
print(f"  Skipped {skipped} unchanged blobs")

# Create tree
print(f"\nCreating tree...", end=" ", flush=True)
r = req("POST", f"{API}/repos/{OWNER}/{REPO}/git/trees", json={"base_tree": parent_sha, "tree": entries})
if not r: sys.exit("FAILED tree")
tree_sha = r["sha"]
print(f"{tree_sha[:12]}")

# Create commit
print(f"Creating commit...", end=" ", flush=True)
r = req("POST", f"{API}/repos/{OWNER}/{REPO}/git/commits", json={"message": msg, "tree": tree_sha, "parents": [parent_sha]})
if not r: sys.exit("FAILED commit")
commit_sha = r["sha"]
print(f"{commit_sha[:12]}")

# Update ref
print(f"Updating main...", end=" ", flush=True)
r = req("PATCH", f"{API}/repos/{OWNER}/{REPO}/git/refs/heads/main", json={"sha": commit_sha, "force": False})
if r:
    print(f"DONE! {commit_sha}")
else:
    print("FAILED")
