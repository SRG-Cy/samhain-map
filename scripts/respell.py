"""Second, small Gemma pass: suggest modern spellings for places the gazetteer didn't find.

Curtin wrote down names as he heard them in the 1890s (Lochlein, Rahonain), and
modern maps spell them differently. Gemma only suggests; verify.py accepts a
suggestion only if that place exists and is near the tale's other places.

Writes data/respell.json: {normalized old name: {"name", "quote", "suggestions": [...]}}
"""
import json
from pathlib import Path

from extract import call_gemma, load_key
from verify import norm

ROOT = Path(__file__).resolve().parents[1]

PROMPT = """These place names come from Irish folk tales collected in south-west Munster (mostly County Kerry, some Cork) and printed in 1895. The collector spelled names as he heard them, so many differ from modern maps.

For each name, give up to 3 modern English spellings of the same real place, as they would appear on a modern Irish map (townland, village, lake, mountain, castle). Use the quote for context. If you do not know the place, give an empty list. Do not guess wildly.

Return ONLY a JSON object: {{"answers": [{{"name": "...", "suggestions": ["...", "..."]}}]}}

NAMES:
{items}
"""


def main():
    tales = json.loads((ROOT / "web/data/tales.json").read_text(encoding="utf-8"))
    out_file = ROOT / "data/respell.json"
    done = json.loads(out_file.read_text(encoding="utf-8")) if out_file.exists() else {}
    todo = {}
    for t in tales:
        for p in t["places"]:
            if p["status"].startswith("not pinned") and norm(p["name"]) not in done:
                todo.setdefault(norm(p["name"]), {"name": p["name"], "quote": p["quote"]})
    if not todo:
        print("nothing to respell")
        return
    key = load_key()
    names = list(todo.values())
    # one name per call, with a time limit: batches of 29 and then 5 names reasoned for over
    # six minutes. A name that times out is skipped (left unpinned), not retried forever.
    for v in names:
        items = f'- "{v["name"]}" (from: "{v["quote"]}")'
        try:
            raw, usage = call_gemma("gemma-4-26b-a4b-it", key, PROMPT.format(items=items),
                                    max_tokens=12000, timeout=150)
        except (TimeoutError, OSError) as e:
            print(f"{v['name']!r:28} -> skipped ({type(e).__name__})")
            continue
        if "{" not in raw:
            print(f"{v['name']!r:28} -> no answer ({usage.get('thoughtsTokenCount')} reasoning tokens)")
            continue
        for a in json.loads(raw[raw.find("{"): raw.rfind("}") + 1])["answers"]:
            k = norm(a.get("name"))
            if k in todo:
                done[k] = {**todo[k], "suggestions": a.get("suggestions") or []}
                print(f"{todo[k]['name']!r:28} -> {done[k]['suggestions']}")
        out_file.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
