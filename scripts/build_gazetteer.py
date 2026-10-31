"""Build the place-name list the matcher checks against, plus the base map layer.

Inputs (data/raw/, not committed):
  townlands_20m.geojson  Tailte Éireann townland boundaries, generalised 20 m, EPSG:2157 (CC BY 4.0)
  geonames_IE/IE.txt     GeoNames Ireland dump (CC BY 4.0), for towns, bridges, hills, lakes

Outputs:
  data/gazetteer.json        every candidate place in Munster: name, county, kind, lat, lon
  data/townland_shapes.json  townland id -> simplified WGS84 polygon (only used for tales' places)
  web/data/counties.geojson  Munster county outlines for the map
"""
import csv
import json
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import mapping, shape, Point
from shapely.ops import transform, unary_union

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
MUNSTER = {"KERRY", "CORK", "LIMERICK", "CLARE", "TIPPERARY", "WATERFORD"}

to_wgs84 = Transformer.from_crs("EPSG:2157", "EPSG:4326", always_xy=True).transform


def main():
    gj = json.loads((RAW / "townlands_20m.geojson").read_text(encoding="utf-8"))
    places, shapes_out = [], {}
    by_county = {c: [] for c in MUNSTER}
    for f in gj["features"]:
        p = f["properties"]
        county = (p["COUNTY"] or "").strip().upper()
        if county not in MUNSTER:
            continue
        geom = transform(to_wgs84, shape(f["geometry"]))
        by_county[county].append(geom)
        c = geom.representative_point()
        td = str(p["TD_ID"])
        places.append(
            {
                "name": p["TD_ENGLISH"].strip().title(),
                "irish": (p.get("TD_GAEILGE") or "").strip() or None,
                "county": county.title(),
                "kind": "townland",
                "id": f"td:{td}",
                "lat": round(c.y, 5),
                "lon": round(c.x, 5),
            }
        )
        shapes_out[f"td:{td}"] = mapping(geom.simplify(0.0002, preserve_topology=True))

    counties = []
    county_shapes = {}
    for county, geoms in by_county.items():
        merged = unary_union(geoms).simplify(0.003, preserve_topology=True)
        county_shapes[county.title()] = merged
        counties.append({"type": "Feature", "properties": {"county": county.title()}, "geometry": mapping(merged)})

    # GeoNames: towns, villages, bridges, hills, lakes, castles... inside Munster
    keep_classes = {"P", "S", "T", "H", "L", "V"}
    with open(RAW / "geonames_IE/IE.txt", encoding="utf-8") as fh:
        for row in csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE):
            if row[6] not in keep_classes:
                continue
            lat, lon = float(row[4]), float(row[5])
            pt = Point(lon, lat)
            county = next((c for c, g in county_shapes.items() if g.contains(pt)), None)
            if not county:
                # city centres (Cork, Limerick) have no townlands, so they sit in holes in the outline
                near = min(county_shapes.items(), key=lambda cg: cg[1].distance(pt))
                if near[1].distance(pt) < 0.05:
                    county = near[0]
            if not county:
                continue
            places.append(
                {
                    "name": row[1],
                    "irish": None,
                    "alt": [a for a in row[3].split(",") if a][:8],
                    "county": county,
                    "kind": f"geonames:{row[7]}",
                    "id": f"gn:{row[0]}",
                    "lat": round(lat, 5),
                    "lon": round(lon, 5),
                }
            )

    (ROOT / "data/gazetteer.json").write_text(json.dumps(places, ensure_ascii=False), encoding="utf-8")
    (ROOT / "data/townland_shapes.json").write_text(json.dumps(shapes_out), encoding="utf-8")
    (ROOT / "web/data").mkdir(parents=True, exist_ok=True)
    (ROOT / "web/data/counties.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": counties}), encoding="utf-8"
    )
    kinds = {}
    for p in places:
        kinds[p["kind"].split(":")[0]] = kinds.get(p["kind"].split(":")[0], 0) + 1
    print(len(places), "places", kinds)


if __name__ == "__main__":
    main()
