"""Famous haunted sites layer. No model runs here.

For each site in data/sites.json:
  1. its quote must appear word for word in exactly one story (the story that tells it)
  2. its location comes from the gazetteer (name in that county); hand-set coordinates
     are used only where the gazetteer has nothing, and they carry their source

Photos (freely licensed, with credits) come from data/site_images.json, written by
scripts/site_images.py. Writes web/data/sites.json. Run after verify.py.
"""
import json
from collections import defaultdict
from pathlib import Path

from verify import norm

ROOT = Path(__file__).resolve().parents[1]


def main():
    cfg = json.loads((ROOT / "data/sites.json").read_text(encoding="utf-8"))
    tales = json.loads((ROOT / "web/data/tales.json").read_text(encoding="utf-8"))
    gaz = json.loads((ROOT / "data/gazetteer.json").read_text(encoding="utf-8"))
    index = defaultdict(list)
    for p in gaz:
        for n in [p["name"], *(p.get("alt") or [])]:
            index[norm(n)].append(p)

    img_file = ROOT / "data/site_images.json"
    images = json.loads(img_file.read_text(encoding="utf-8")) if img_file.exists() else {}
    out = []
    for s in cfg["sites"]:
        told = [t for t in tales if norm(s["quote"]) in norm(t["text"])]
        if len(told) != 1:
            raise SystemExit(f"{s['name']}: quote found in {len(told)} stories, need exactly 1")
        t = told[0]
        found = [p for p in index.get(norm(s["name"]), []) if p["county"] == s["county"]]
        if found:
            # a point at the site itself (castle, ruin, lake) rather than a townland of the same name
            p = sorted(found, key=lambda p: p["kind"] == "townland")[0]
            lat, lon, located = p["lat"], p["lon"], f"{'GeoNames' if p['id'].startswith('gn:') else 'townland'}: {p['name']}, Co. {p['county']}"
        elif "lat" in s:
            lat, lon, located = s["lat"], s["lon"], f"coordinates from {s['coords_source']}"
        else:
            raise SystemExit(f"{s['name']}: not in the gazetteer and no coordinates given")
        out.append({"name": s["name"], "county": s["county"], "lat": lat, "lon": lon, "located": located,
                    "quote": s["quote"], "tale": t["id"], "note": s.get("note"), "note_source": s.get("note_source"),
                    "image": images.get(s["name"])})
        print(f"{s['name']:20} story {t['id']:3} {t['title'][:40]:40} {located}")
    (ROOT / "web/data/sites.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
