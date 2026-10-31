"""Print what the checker decided for each place in the 1914 stories (debug view)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for t in json.loads((ROOT / "web/data/tales.json").read_text(encoding="utf-8")):
    if t["book"] != "seymour1914":
        continue
    print(f"{t['id']} {t['title']}  {t['beings']}")
    for p in t["places"]:
        where = f"-> {p.get('matched_name')}, {p.get('county')}" if p.get("lat") else ""
        print(f"    {p['name']!r:30} {p['status'][:80]} {where} {p.get('note') or ''}")
