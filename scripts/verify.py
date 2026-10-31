"""Decide which of Gemma's answers are kept. No model runs here: only string and map checks.

For every place Gemma reported:
  1. the quote must really be in the tale, and the name must be in the quote
  2. counties, provinces and countries are listed but not pinned (too broad)
  3. the name must be a real place in the Munster gazetteer (Tailte Éireann
     townlands + GeoNames). If the tale's 1890s spelling isn't found, Gemma's
     suggested modern spelling (from extract.py or respell.py) is tried, but it is
     only accepted within MAX_KM of the tale's other places
  4. if several real places share the name, pick the one closest to the tale's
     other verified places, and say that it was a choice

Anything that fails is kept in the output with the reason, so the map can show
what was thrown away.

Writes web/data/tales.json, web/data/places.geojson and data/report.json.
"""
import json
import math
import re
import unicodedata
from collections import Counter
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_KM = 30  # a respelled place further than this from the tale's other places is refused
SAME_PLACE_KM = 4  # a townland and a GeoNames point this close with one name are one place
BROAD = {
    "ireland", "erin", "munster", "ulster", "leinster", "connacht", "connaught", "kerry", "cork county",
    "county kerry", "county cork", "county limerick", "county clare", "limerick county", "america",
    "england", "scotland", "france", "spain", "rome",
}
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


def km(a, b):
    dy = (a["lat"] - b["lat"]) * 111.0
    dx = (a["lon"] - b["lon"]) * 111.0 * math.cos(math.radians(52))
    return math.hypot(dx, dy)


def clusters(cands):
    """Group candidates that are the same place (townland + town point a few km apart)."""
    groups = []
    for c in cands:
        for g in groups:
            if km(g[0], c) <= SAME_PLACE_KM:
                g.append(c)
                break
        else:
            groups.append([c])
    # represent each group by a townland polygon if there is one (clickable area), else the point
    return [sorted(g, key=lambda c: 0 if c["kind"] == "townland" else 1)[0] for g in groups]


def main():
    tales = json.loads((ROOT / "data/tales.json").read_text(encoding="utf-8"))
    gaz = json.loads((ROOT / "data/gazetteer.json").read_text(encoding="utf-8"))
    shapes = json.loads((ROOT / "data/townland_shapes.json").read_text(encoding="utf-8"))
    respell_file = ROOT / "data/respell.json"
    respell = json.loads(respell_file.read_text(encoding="utf-8")) if respell_file.exists() else {}

    index = defaultdict(list)
    for p in gaz:
        if p["kind"].startswith("geonames:ADM") or p["kind"] in ("geonames:RGN", "geonames:AREA"):
            continue
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

        places = []
        for pl in res.get("places", []):
            name, quote = pl.get("name") or "", pl.get("quote") or ""
            item = {"name": name, "quote": quote, "role": pl.get("role")}
            stats["reported"] += 1
            if not quote_in(quote, text_norm) or norm(name) not in norm(quote):
                item["status"] = "refused: quote not in the tale"
                stats["refused_quote"] += 1
            elif norm(name) in BROAD or norm(name).startswith("county "):
                item["status"] = "listed: too broad to pin"
                stats["too_broad"] += 1
            else:
                exact = index.get(norm(name), [])
                if exact:
                    item.update(cands=clusters(exact), via="tale")
                else:
                    tries = [pl.get("modern_name"), *(respell.get(norm(name), {}).get("suggestions", []))]
                    for alt in [a for a in tries if a]:
                        if index.get(norm(alt)):
                            item.update(cands=clusters(index[norm(alt)]), via="modern", suggested=alt)
                            break
                    else:
                        item["status"] = "not pinned: no such place found"
                        stats["unmatched"] += 1
            places.append(item)

        # anchors: places that match the tale's own spelling with exactly one real location
        anchors = [p["cands"][0] for p in places if p.get("via") == "tale" and len(p["cands"]) == 1]
        if not anchors:
            anchors = [c for p in places if p.get("via") == "tale" for c in p["cands"] if c["county"] == "Kerry"][:3]
        centre = None
        if anchors:
            centre = {"lat": sum(a["lat"] for a in anchors) / len(anchors),
                      "lon": sum(a["lon"] for a in anchors) / len(anchors)}

        seen = set()
        for p in places:
            cands = p.pop("cands", None)
            if not cands:
                continue
            via = p.pop("via")
            ref = centre or {"lat": 52.1, "lon": -9.7}  # middle of Kerry, where Curtin collected
            cands = sorted(cands, key=lambda c: km(c, ref))
            pick = cands[0]
            if via == "modern" and centre and km(pick, centre) > MAX_KM:
                p["status"] = f"refused: '{p['suggested']}' exists, but {round(km(pick, centre))} km from the tale's other places"
                stats["refused_far"] += 1
                continue
            if pick["id"] in seen:
                p["status"] = "duplicate"
                continue
            seen.add(pick["id"])
            note = f"{len(cands)} places share this name; chose the one nearest the tale's other places" if len(cands) > 1 else None
            p.update(
                status="pinned" if via == "tale" else f"pinned via modern spelling '{p['suggested']}' (suggested by Gemma)",
                place_id=pick["id"], matched_name=pick["name"], county=pick["county"],
                kind=pick["kind"], lat=pick["lat"], lon=pick["lon"], note=note,
            )
            stats["pinned" if via == "tale" else "pinned_modern"] += 1
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
