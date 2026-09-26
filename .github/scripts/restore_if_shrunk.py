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

new = json.loads(Path("noticias-feed.json").read_text(encoding="utf-8"))
old = load_at("HEAD~1")
old_items, new_items = items(old), items(new)
print(f"old={len(old_items)} new={len(new_items)}")
if not old_items:
    print("no parent feed; ok")
    sys.exit(0)
if len(new_items) >= len(old_items) and not (len(new_items) == 1 and (new_items[0].get("title") or "").startswith("RESTORE")):
    print("ok append")
    sys.exit(0)

print("SHRINK or stub; merging restore")
seen, out = set(), []
for n in old_items + new_items:
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
if old.get("indicadores") and not (merged.get("indicadores") or {}).get("jet54"):
    merged["indicadores"] = old["indicadores"]
if (merged.get("briefing") or {}).get("title", "").startswith("RESTORE"):
    merged["briefing"] = old.get("briefing") or merged.get("briefing")
Path("noticias-feed.json").write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
subprocess.check_call(["git", "config", "user.name", "feed-append-only"])
subprocess.check_call(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"])
subprocess.check_call(["git", "add", "noticias-feed.json"])
subprocess.check_call(["git", "commit", "-m", "restore: no borrar notas del feed"])
subprocess.check_call(["git", "push"])
print(f"restored {len(out)} notes")
