#!/usr/bin/env python3
import json, subprocess, sys
from pathlib import Path

def load_at(rev, path="noticias-feed.json"):
    try:
        raw = subprocess.check_output(["git", "show", f"{rev}:{path}"], text=True)
        return json.loads(raw)
    except Exception:
        return {}

def items(d):
    return [n for n in (d.get("noticias") or []) if isinstance(n, dict)]

def key(n):
    u = (n.get("sourceUrl") or n.get("source_url") or "").strip().rstrip("/").lower()
    return ("u:" + u) if u else ("t:" + (n.get("title") or "").strip().lower())

# --- merge pending-notes.json if present ---
pending_path = Path("pending-notes.json")
pending_notes = []
pending_briefing = None
pending_indicadores = None
if pending_path.exists():
    try:
        p = json.loads(pending_path.read_text(encoding="utf-8"))
        pending_notes = [n for n in (p.get("notes") or []) if isinstance(n, dict)]
        pending_briefing = p.get("briefing")
        pending_indicadores = p.get("indicadores")
        print(f"found pending-notes: {len(pending_notes)} notes")
    except Exception as e:
        print(f"pending-notes invalid: {e}")

try:
    new = json.loads(Path("noticias-feed.json").read_text(encoding="utf-8"))
    if not isinstance(new, dict):
        new = {}
except Exception:
    print("new feed is not valid JSON; treating as empty")
    new = {}

# compare against the largest valid feed in recent history
old = {}
for i in range(1, 30):
    cand = load_at(f"HEAD~{i}")
    if len(items(cand)) > len(items(old)):
        old = cand
old_items, new_items = items(old), items(new)
print(f"old={len(old_items)} new={len(new_items)}")

# If we have pending notes, force a merge even if sizes look ok
force_merge = bool(pending_notes)

if not old_items and not force_merge:
    print("no parent feed; ok")
    sys.exit(0)
if (len(new_items) >= len(old_items) and not force_merge
    and not (len(new_items) == 1 and (new_items[0].get("title") or "").startswith("RESTORE"))):
    print("ok append")
    sys.exit(0)

print("SHRINK, stub, or pending notes; merging")
seen, out = set(), []
# pending first (newest), then old, then any new
for n in pending_notes + old_items + new_items:
    k = key(n)
    if not k or k in ("u:", "t:") or k in seen:
        continue
    if (n.get("title") or "") in ("RESTORE-SEE-FILE",):
        continue
    seen.add(k)
    out.append(n)
out.sort(key=lambda n: n.get("publishedAt") or "", reverse=True)

merged = dict(new or old)
merged["noticias"] = out

# indicadores: prefer pending, else preserve from old
if pending_indicadores:
    merged["indicadores"] = pending_indicadores
elif old.get("indicadores") and not (merged.get("indicadores") or {}).get("jet54"):
    merged["indicadores"] = old["indicadores"]

if pending_briefing:
    merged["briefing"] = pending_briefing
elif (merged.get("briefing") or {}).get("title", "").startswith("RESTORE"):
    merged["briefing"] = old.get("briefing") or merged.get("briefing")

Path("noticias-feed.json").write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
subprocess.check_call(["git", "config", "user.name", "feed-append-only"])
subprocess.check_call(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"])
subprocess.check_call(["git", "add", "noticias-feed.json"])
if pending_path.exists():
    subprocess.check_call(["git", "rm", "-f", "pending-notes.json"])
subprocess.check_call(["git", "commit", "-m", "restore+merge: notas pendientes aplicadas"])
subprocess.check_call(["git", "push"])
print(f"restored/merged {len(out)} notes")
