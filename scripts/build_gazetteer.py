"""Build the place-name list the matcher checks against, plus the base map layer.

Inputs (data/raw/, not committed):
  townlands_20m.geojson   Tailte Éireann townland boundaries, generalised 20 m, EPSG:2157 (CC BY 4.0)
  osni_townlands.geojson  OSNI Open Data townland boundaries for Northern Ireland, WGS84 (OGL v3)
  osni_counties.geojson   OSNI county boundaries, WGS84 (OGL v3)
  geonames_IE/IE.txt      GeoNames Ireland dump (CC BY 4.0), for towns, bridges, hills, lakes
  geonames_GB/GB.txt      GeoNames UK dump (CC BY 4.0), only the Northern Ireland rows are used

Outputs:
  data/gazetteer.json        every candidate place in Ireland: name, county, kind, lat, lon
  data/townland_shapes.json  townland id -> simplified WGS84 polygon (only used for tales' places)
  web/data/counties.geojson  the 32 county outlines for the map
"""
import csv
import json
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import mapping, shape, Point
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"

to_wgs84 = Transformer.from_crs("EPSG:2157", "EPSG:4326", always_xy=True).transform


def townland(geom, name, irish, county, td):
    c = geom.representative_point()
    return {"name": name.strip().title(), "irish": irish, "county": county.title(), "kind": "townland",
            "id": td, "lat": round(c.y, 5), "lon": round(c.x, 5)}


def main():
    places, shapes_out, by_county = [], {}, {}

    gj = json.loads((RAW / "townlands_20m.geojson").read_text(encoding="utf-8"))
    for f in gj["features"]:
        p = f["properties"]
        county = (p["COUNTY"] or "").strip().upper()
        geom = transform(to_wgs84, shape(f["geometry"]))
        by_county.setdefault(county, []).append(geom)
        td = f"td:{p['TD_ID']}"
        places.append(townland(geom, p["TD_ENGLISH"], (p.get("TD_GAEILGE") or "").strip() or None, county, td))
        shapes_out[td] = mapping(geom.simplify(0.0002, preserve_topology=True))

    # Northern Ireland: OSNI has no county on each townland, so place it by its county outline
    ni = json.loads((RAW / "osni_counties.geojson").read_text(encoding="utf-8"))
    ni_counties = {f["properties"]["CountyName"].strip().upper(): shape(f["geometry"]) for f in ni["features"]}
    for f in json.loads((RAW / "osni_townlands.geojson").read_text(encoding="utf-8"))["features"]:
        if not f["geometry"]:
            continue
        geom = shape(f["geometry"])
        pt = geom.representative_point()
        county = next((c for c, g in ni_counties.items() if g.contains(pt)), None)
        if not county:
            continue
        td = f"ni:{f['properties']['TOWNLAND_I']}"
        places.append(townland(geom, f["properties"]["TownlandNa"], None, county, td))
        shapes_out[td] = mapping(geom.simplify(0.0002, preserve_topology=True))

    counties, county_shapes = [], {}
    for county, geoms in by_county.items():
        county_shapes[county.title()] = unary_union(geoms).simplify(0.003, preserve_topology=True)
    for county, g in ni_counties.items():
        county_shapes[county.title()] = g.simplify(0.003, preserve_topology=True)
    for county, g in county_shapes.items():
        counties.append({"type": "Feature", "properties": {"county": county}, "geometry": mapping(g)})
    names = list(county_shapes)
    tree = STRtree([county_shapes[c] for c in names])

    def county_of(pt):
        for i in tree.query(pt):
            if county_shapes[names[i]].contains(pt):
                return names[i]
        # city centres (Cork, Limerick) have no townlands, so they sit in holes in the outline
        i = tree.nearest(pt)
        return names[i] if county_shapes[names[i]].distance(pt) < 0.05 else None

    # GeoNames: towns, villages, bridges, hills, lakes, castles... on the island of Ireland
    keep_classes = {"P", "S", "T", "H", "L", "V"}
    for src, only_ni in [("geonames_IE/IE.txt", False), ("geonames_GB/GB.txt", True)]:
        with open(RAW / src, encoding="utf-8") as fh:
            for row in csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE):
                if row[6] not in keep_classes or (only_ni and row[10] != "NIR"):
                    continue
                lat, lon = float(row[4]), float(row[5])
                county = county_of(Point(lon, lat))
                if not county:
                    continue
                places.append({
                    "name": row[1], "irish": None, "alt": [a for a in row[3].split(",") if a][:8],
                    "county": county, "kind": f"geonames:{row[7]}", "id": f"gn:{row[0]}",
                    "lat": round(lat, 5), "lon": round(lon, 5),
                })

    (ROOT / "data/gazetteer.json").write_text(json.dumps(places, ensure_ascii=False), encoding="utf-8")
    (ROOT / "data/townland_shapes.json").write_text(json.dumps(shapes_out), encoding="utf-8")
    (ROOT / "web/data").mkdir(parents=True, exist_ok=True)
    (ROOT / "web/data/counties.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": counties}), encoding="utf-8"
    )
    kinds = {}
    for p in places:
        kinds[p["kind"].split(":")[0]] = kinds.get(p["kind"].split(":")[0], 0) + 1
    print(len(places), "places", kinds, len(county_shapes), "counties")


if __name__ == "__main__":
    main()
