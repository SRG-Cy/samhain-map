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

from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[1]
MAX_KM = 30  # a respelled place further than this from the tale's other places is refused
SAME_PLACE_KM = 4  # a townland and a GeoNames point this close with one name are one place
FAR_KM = 60  # an exact match further than this from the tale's other places is refused
# Curtin collected in south-west Munster; the 1914 book was sent in from anywhere in Ireland
HOME = {"curtin1895": {"Kerry", "Cork"}, "seymour1914": None, "croker1825": None, "mcanally1888": None}
TRAVEL_KINDS = {"geonames:PPLA", "geonames:PPLA2", "geonames:PPLC"}  # county towns and cities
BROAD = {
    "ireland", "erin", "munster", "ulster", "leinster", "connacht", "connaught", "kerry", "cork county",
    "county kerry", "county cork", "county limerick", "county clare", "limerick county", "america",
    "england", "scotland", "france", "spain", "rome",
    # counties with no town of the same name, and the old names for two of them
    "clare", "tipperary", "meath", "westmeath", "offaly", "laois", "fermanagh", "tyrone", "down",
    "king's county", "queen's county", "the north", "north of ireland", "south of ireland", "west of ireland",
    "london", "wales", "india", "australia", "canada", "europe", "united states", "south africa",
}
OLD_COUNTY = {"king's": "Offaly", "queen's": "Laois", "londonderry": "Londonderry", "derry": "Londonderry"}
BEINGS = {
    "ghost", "fairy", "banshee", "pooka", "mermaid_or_seal_woman", "devil",
    "dead_returning", "changeling", "fairy_doctor", "saint", "other",
    "poltergeist", "death_warning",
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
    out = []
    for g in groups:
        # townland polygon first, then the town itself, never "Waterford North Station" or "Larne River"
        rep = dict(sorted(g, key=lambda c: 0 if c["kind"] == "townland" else 1 if c["kind"].startswith("geonames:PPL") else 2)[0])
        rep["town"] = any(c["kind"].startswith("geonames:PPL") for c in g)
        out.append(rep)
    return out


def counties_named(text, counties):
    """Counties the story itself names: 'Co. Galway', 'County Wexford', 'King's County'."""
    found = {}
    for m in re.finditer(r"\b(?:co\.?|county)\s+([A-Z][a-z]+)|\b([A-Z][a-z]+)\s+county\b|\b(King's|Queen's) County", text, re.I):
        word = next(g for g in m.groups() if g)
        name = OLD_COUNTY.get(word.lower(), word.title())
        if name in counties:
            found.setdefault(name, m.group(0))
    return found


def tidy(places):
    """Drop duplicate pins and names Gemma reported twice with the same outcome."""
    out, seen = [], set()
    for p in places:
        k = (norm(p["name"]), p.get("status"))
        if p.get("status") == "duplicate" or k in seen:
            continue
        seen.add(k)
        out.append({key: v for key, v in p.items() if key != "modern"})
    return out


def is_county(name):
    n = norm(name)
    return n.startswith(("county ", "co ")) or n.endswith(" county")


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

    all_counties = {p["county"] for p in gaz}
    county_points = {}
    for f in json.loads((ROOT / "web/data/counties.geojson").read_text(encoding="utf-8"))["features"]:
        c = shape(f["geometry"]).representative_point()
        county_points[f["properties"]["county"]] = {"lat": round(c.y, 5), "lon": round(c.x, 5)}
    stats = Counter()
    out_tales, features = [], {}
    for t in tales:
        f = ROOT / f"data/extract/{t['id']:02d}.json"
        if not f.exists():
            continue
        rec = json.loads(f.read_text(encoding="utf-8"))
        res = rec["result"]
        book = t.get("book", "curtin1895")
        home = HOME[book]
        named = counties_named(t["text"], all_counties)
        # a title Gemma wrote is not the book's text, so it can't vouch for a quote
        text_norm = norm(t["text"]) + ("" if t.get("title_by") == "gemma" else " " + norm(t["title"]))

        beings = [b for b in res.get("beings", []) if b in BEINGS]
        bq = res.get("beings_quote")
        beings_quote_ok = quote_in(bq, text_norm)
        stats["beings_quote_ok" if beings_quote_ok else "beings_quote_bad"] += 1

        places = []
        for pl in res.get("places", []):
            name, quote = pl.get("name") or "", pl.get("quote") or ""
            item = {"name": name, "quote": quote, "role": pl.get("role"), "modern": pl.get("modern_name")}
            stats["reported"] += 1
            if not quote_in(quote, text_norm) or norm(name) not in norm(quote):
                item["status"] = "refused: quote not in the tale"
                stats["refused_quote"] += 1
            elif norm(name) in BROAD or is_county(name):
                item["status"] = "listed: too broad to pin"
                stats["too_broad"] += 1
            elif home is None and pl.get("role") != "setting":
                # the 1914 book names where each correspondent lived ("the Archdeacon of Limerick",
                # "fought at Waterloo"); the map is for where the story happens
                item["status"] = "listed: mentioned, but the story doesn't happen there"
                stats["mentioned_only"] += 1
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
            # the story says which county: only same-name places in that county are candidates
            if item.get("cands") and named:
                if not any(c["county"] in named for c in item["cands"]) and item["via"] == "tale":
                    # every exact match is in another county: an old name? (Kingstown is now Dún Laoghaire)
                    alt = pl.get("modern_name")
                    in_county = [c for c in index.get(norm(alt), []) if c["county"] in named] if alt else []
                    if in_county:
                        item.update(cands=clusters(in_county), via="modern", suggested=alt)
                if any(c["county"] in named for c in item["cands"]):
                    item["cands"] = [c for c in item["cands"] if c["county"] in named]
                    item["county_from_text"] = True
            places.append(item)

        # anchors: places that match the tale's own spelling with exactly one real location, in the
        # region Curtin collected in. (A lone "Drummond" in Tipperary once dragged Waterville to Limerick.)
        anchors = [p["cands"][0] for p in places
                   if p.get("via") == "tale" and len(p["cands"]) == 1
                   and (home is None or p["cands"][0]["county"] in home)
                   and p["cands"][0]["kind"] not in TRAVEL_KINDS]  # a trip to Cork city isn't where the tale is set
        if not anchors and home:
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
            by_county = p.pop("county_from_text", False)
            if home is None and not centre and len(cands) > 1:
                # nothing else in the story to choose by: take the only town of that name, else the only
                # town with Gemma's modern name (Kingstown -> Dún Laoghaire), else refuse
                towns = [c for c in cands if c["town"]]
                modern = [c for c in clusters(index.get(norm(p["modern"]), [])) if c["town"]
                          and (not named or c["county"] in named)] if p.get("modern") and via == "tale" else []
                if len(towns) == 1:
                    cands = towns + [c for c in cands if not c["town"]]
                elif len(modern) == 1:
                    cands, via, p["suggested"] = modern, "modern", p["modern"]
                else:
                    where = f"Co. {next(iter(named))}" if by_county and len(named) == 1 else "Ireland"
                    p["status"] = f"not pinned: {len(cands)} places in {where} are called '{p.get('suggested') or p['name']}', and the story gives nothing to choose by"
                    stats["ambiguous_refused"] += 1
                    p.pop("modern", None)
                    continue
            ref = centre or ({"lat": 52.1, "lon": -9.7} if home else cands[0])  # Kerry: where Curtin collected
            cands = sorted(cands, key=lambda c: km(c, ref))
            pick = cands[0]
            if via == "modern" and centre and km(pick, centre) > MAX_KM:
                p["status"] = f"refused: '{p['suggested']}' exists, but {round(km(pick, centre))} km from the tale's other places"
                stats["refused_far"] += 1
                continue
            # an exact-spelling match far from everything else is probably a different place with the
            # same name; big towns people travelled to (Cork city) are allowed to be far
            far = centre and km(pick, centre) > FAR_KM and pick["kind"] not in TRAVEL_KINDS
            if via == "tale" and (far or (not centre and home and pick["county"] not in home)):
                where = f"{round(km(pick, centre))} km from the tale's other places" if centre else "outside Kerry and Cork"
                p["status"] = f"refused: the only '{pick['name']}' found is in Co. {pick['county']}, {where}"
                stats["refused_far"] += 1
                continue
            if pick["id"] in seen:
                p["status"] = "duplicate"
                continue
            seen.add(pick["id"])
            note = None
            if len(cands) > 1:
                note = (f"{len(cands)} places share this name; chose the one nearest the tale's other places" if centre or home
                        else f"{len(cands)} places share this name; chose the only town")
            if by_county:
                note = f"the story names Co. {pick['county']}" + (f"; {note}" if note else "")
            p.update(
                status="pinned" if via == "tale" else f"pinned via modern spelling '{p['suggested']}' (suggested by Gemma)",
                # GeoNames sometimes leads with the Irish name (Cluain Meala); show the story's own spelling
                place_id=pick["id"], matched_name=p["name"] if via == "tale" else pick["name"], county=pick["county"],
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

        # a story that names one county and no place that could be pinned goes on the county itself
        if home is None and len(named) == 1 and not any(p.get("status", "").startswith("pinned") for p in places):
            county, said = next(iter(named.items()))
            item = next((p for p in places if is_county(p["name"]) and county.lower() in norm(p["name"])), None)
            if not item:
                item = {"name": said, "quote": said, "role": "setting"}
                places.append(item)
            places = [p for p in places if p is item or not (is_county(p["name"]) and county.lower() in norm(p["name"]))]
            pt = county_points[county]
            item.update(status="pinned to the county: the story names no smaller place that could be found",
                        place_id=f"county:{county}", matched_name=f"Co. {county}", county=county, kind="county",
                        lat=pt["lat"], lon=pt["lon"], note=None)
            stats["pinned_county"] += 1
            feat = features.setdefault(item["place_id"], {
                "type": "Feature", "geometry": {"type": "Point", "coordinates": [pt["lon"], pt["lat"]]},
                "properties": {"id": item["place_id"], "name": f"Co. {county}", "county": county, "kind": "county",
                               "lat": pt["lat"], "lon": pt["lon"], "tales": []},
            })
            feat["properties"]["tales"].append(t["id"])

        out_tales.append({
            "id": t["id"], "book": book, "title": t["title"], "title_by": t.get("title_by"),
            "chapter": t.get("chapter_title"), "pages": t["pages"], "teller": t["teller"],
            "beings": beings, "beings_quote": bq if beings_quote_ok else None,
            "summary": res.get("summary"), "places": tidy(places),
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
