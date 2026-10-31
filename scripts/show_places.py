"""Print every place per tale with what the checker decided (for debugging and the post)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for t in json.loads((ROOT / "web/data/tales.json").read_text(encoding="utf-8")):
    print(f"\n{t['id']:2d} {t['title']}")
    for p in t["places"]:
        got = f"-> {p['matched_name']} ({p['county']}, {p['kind']})" if p.get("matched_name") else ""
        print(f"   {p['name']!r:28} {p['status']:32} {got} {p.get('note') or ''}")
