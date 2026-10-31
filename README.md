# Samhain Map

Irish ghost and fairy stories from two public-domain books, put back on the map.

- Jeremiah Curtin's *Tales of the Fairies and of the Ghost World* (1895): 30 tales told to him by
  firesides in south-west Munster.
- St John D. Seymour and Harry L. Neligan's *True Irish Ghost Stories* (1914): ghost accounts sent in
  from all over Ireland.

An open-weight model (Gemma 4) reads each story: what haunts it, a one-line summary, and which places it
names. Plain code then checks every answer before anything is pinned on the map.

**Gemma reads. Code decides.**

- Every place must come with an exact quote, and the quote must be in the story.
- The name must be a real place on the island of Ireland: a Tailte Éireann or OSNI townland, or a GeoNames
  town, hill, lake or bridge.
- Curtin spelled names as he heard them (Lochlein, Rahonain). Gemma may suggest a modern spelling,
  but code accepts it only if that place exists and lies near the tale's other places.
- When several real places share a name, code picks the one nearest the story's other places, or in the
  county the story names. If nothing in the story can decide, the place is not pinned.
- Counties and provinces are listed, not pinned. Everything refused is shown, with the reason.
- The 1914 book runs its stories together with no headings. Gemma says which paragraph each account
  starts at; code checks the numbers and cuts the text. Gemma never rewrites the text.

## Run it

```bash
python -m venv .venv && .venv/Scripts/pip install pyproj shapely
# put GEMINI_API_KEY=... in .env (Google AI Studio key)
python scripts/split_tales.py        # Curtin -> data/tales.json (ids 1-30)
python scripts/split_seymour.py      # Seymour & Neligan -> data/tales.json (ids 101+), Gemma marks story starts
python scripts/build_gazetteer.py    # townlands + GeoNames -> data/gazetteer.json, web/data/counties.geojson
python scripts/extract.py            # Gemma 4 26B -> data/extract/NN.json (cached, resumable)
python scripts/verify.py             # checks -> web/data/tales.json, web/data/places.geojson
python scripts/respell.py && python scripts/verify.py   # modern spellings for old names, then re-check
python scripts/eval.py               # against data/labels.json
python -m http.server 8765 --directory web
```

Raw inputs (not committed) go in `data/raw/`:
- `curtin_1895.txt`: https://archive.org/download/cu31924029910563/cu31924029910563_djvu.txt
- `seymour_1914.txt`: https://www.gutenberg.org/cache/epub/14099/pg14099.txt
- `townlands_20m.geojson`: Townland Boundaries Generalised 20m (Tailte Éireann, data.gov.ie)
- `osni_townlands.geojson`, `osni_counties.geojson`: OSNI Open Data townland and county boundaries (ArcGIS Hub), as WGS84 GeoJSON
- `geonames_IE/IE.txt`: https://download.geonames.org/export/dump/IE.zip
- `geonames_GB/GB.txt`: https://download.geonames.org/export/dump/GB.zip (only Northern Ireland rows are used)

## Credits and licences

- Tales: Jeremiah Curtin (1895), public domain. Scan: Cornell University Library via archive.org.
- Stories: St John D. Seymour and Harry L. Neligan (1914), public domain. Text: Project Gutenberg #14099.
- Townland boundaries: © Tailte Éireann, CC BY 4.0. Northern Ireland: OSNI Open Data, Open Government Licence v3.
- Place names: GeoNames, CC BY 4.0.
- Map tiles: © OpenStreetMap contributors.
- Model: Gemma 4 (open weights), called through Google AI Studio.
- Code: MIT.
