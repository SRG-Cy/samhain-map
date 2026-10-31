"""Decide which of Gemma's answers are kept. No model runs here: only string and map checks.

For every place Gemma reported:
  1. the quote must really be in the tale, and the name must be in the quote
  2. the name (or Gemma's suggested modern spelling) must be a real place in the
     Munster gazetteer (Tailte Éireann townlands + GeoNames)
  3. if several real places share the name, pick the one closest to the tale's
     other verified places, and say that it was a choice

Anything that fails is kept in the output with the reason, so the map can show
what was thrown away.

Writes web/data/tales.json, web/data/places.geojson and data/report.json.
"""
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COUNTY_ORDER = ["Kerry", "Cork", "Limerick", "Clare", "Tipperary", "Waterford"]
BEINGS = {
    "ghost", "fairy", "banshee", "pooka", "mermaid_or_seal_woman", "devil",
    "dead_returning", "changeling", "fairy_doctor", "saint", "other",
}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("’", "'").replace("‘", "'").lower()
    s = re.sub(r"[^a-z0-9' ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def quote_in(quote, text_norm):
    q = norm(quote)
    return bool(q) and q in text_norm


def dist(a, b):
    return math.hypot(a["lat"] - b["lat"], (a["lon"] - b["lon"]) * math.cos(math.radians(52)))


def main():
    tales = json.loads((ROOT / "data/tales.json").read_text(encoding="utf-8"))
    gaz = json.loads((ROOT / "data/gazetteer.json").read_text(encoding="utf-8"))
    shapes = json.loads((ROOT / "data/townland_shapes.json").read_text(encoding="utf-8"))

    index = defaultdict(list)
    for p in gaz:
        for n in [p["name"], *(p.get("alt") or [])]:
            index[norm(n)].append(p)

    stats = Counter()
    out_tales, features = [], {}
    for t in tales:
        f = ROOT / f"data/extract/{t['id']:02d}.json"
        if not f.exists():
            continue
        rec = json.loads(f.read_text(encoding="utf-8"))
        res = rec["result"]
        text_norm = norm(t["text"]) + " " + norm(t["title"])

        beings = [b for b in res.get("beings", []) if b in BEINGS]
        bq = res.get("beings_quote")
        beings_quote_ok = quote_in(bq, text_norm)
        stats["beings_quote_ok" if beings_quote_ok else "beings_quote_bad"] += 1

        places, seen = [], set()
        for pl in res.get("places", []):
            name, quote = pl.get("name") or "", pl.get("quote") or ""
            item = {"name": name, "quote": quote, "role": pl.get("role"), "modern_name": pl.get("modern_name")}
            stats["reported"] += 1
            if not quote_in(quote, text_norm) or norm(name) not in norm(quote):
                item["status"] = "rejected: quote not in tale"
                stats["rejected_quote"] += 1
                places.append(item)
                continue
            cands = index.get(norm(name), [])
            via = "spelling in tale"
            if not cands and pl.get("modern_name"):
                cands = index.get(norm(pl["modern_name"]), [])
                via = "modern spelling suggested by Gemma"
            if not cands:
                item["status"] = "unmatched: not in gazetteer"
                stats["unmatched"] += 1
                places.append(item)
                continue
            item["candidates"] = cands
            item["via"] = via
            places.append(item)

        # resolve candidates: prefer a single unambiguous match, then closeness to the others
        anchors = [p["candidates"][0] for p in places if p.get("candidates") and len(p["candidates"]) == 1]
        for p in places:
            cands = p.pop("candidates", None)
            if not cands:
                continue
            if len(cands) == 1:
                pick, note = cands[0], None
            else:
                ref = anchors or [c for c in cands if c["kind"].startswith("geonames:PPL")] or cands
                cy = sum(a["lat"] for a in ref) / len(ref)
                cx = sum(a["lon"] for a in ref) / len(ref)
                centre = {"lat": cy, "lon": cx}
                cands = sorted(
                    cands,
                    key=lambda c: (dist(c, centre), COUNTY_ORDER.index(c["county"]) if c["county"] in COUNTY_ORDER else 9),
                )
                pick, note = cands[0], f"{len(cands)} places share this name; chose the one nearest the tale's other places"
            key = (pick["id"])
            if key in seen:
                p["status"] = "duplicate"
                continue
            seen.add(key)
            p.update(
                status="verified" if p["via"] == "spelling in tale" else "verified (modern spelling)",
                place_id=pick["id"], matched_name=pick["name"], county=pick["county"],
                kind=pick["kind"], lat=pick["lat"], lon=pick["lon"], note=note,
            )
            stats["verified" if p["via"] == "spelling in tale" else "verified_modern"] += 1
            if note:
                stats["ambiguous_resolved"] += 1
            feat = features.setdefault(pick["id"], {
                "type": "Feature",
                "geometry": shapes.get(pick["id"]) or {"type": "Point", "coordinates": [pick["lon"], pick["lat"]]},
                "properties": {"id": pick["id"], "name": pick["name"], "county": pick["county"], "kind": pick["kind"],
                               "lat": pick["lat"], "lon": pick["lon"], "tales": []},
            })
            if t["id"] not in feat["properties"]["tales"]:
                feat["properties"]["tales"].append(t["id"])

        out_tales.append({
            "id": t["id"], "title": t["title"], "pages": t["pages"], "teller": t["teller"],
            "beings": beings, "beings_quote": bq if beings_quote_ok else None,
            "summary": res.get("summary"), "places": [p for p in places if p.get("status") != "duplicate"],
            "model": rec["model"], "text": t["text"],
        })

    (ROOT / "web/data").mkdir(parents=True, exist_ok=True)
    (ROOT / "web/data/tales.json").write_text(json.dumps(out_tales, ensure_ascii=False), encoding="utf-8")
    (ROOT / "web/data/places.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": list(features.values())}), encoding="utf-8")
    (ROOT / "data/report.json").write_text(json.dumps(stats, indent=1), encoding="utf-8")
    print(dict(stats))
    print(len(out_tales), "tales,", len(features), "places on the map")


if __name__ == "__main__":
    main()
