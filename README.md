# Samhain Map

Ghost and fairy tales told in Kerry in the 1890s, put back on the map.

Jeremiah Curtin's *Tales of the Fairies and of the Ghost World* (1895) records stories told to him by
firesides in south-west Munster. This project splits the book into its 30 tales, asks an open-weight
model (Gemma 4) what each tale is about and which places it names, and then checks every answer in
plain code before anything is pinned on the map.

**Gemma reads. Code decides.**

- Every place must come with an exact quote, and the quote must be in the tale.
- The name must be a real place: a Tailte Éireann townland or a GeoNames town, hill, lake or bridge in Munster.
- Curtin spelled names as he heard them (Lochlein, Rahonain). Gemma may suggest a modern spelling,
  but code accepts it only if that place exists and lies near the tale's other places.
- Counties and provinces are listed, not pinned. Everything refused is shown, with the reason.

## Run it

```bash
python -m venv .venv && .venv/Scripts/pip install pyproj shapely
# put GEMINI_API_KEY=... in .env (Google AI Studio key)
python scripts/split_tales.py        # book -> data/tales.json
python scripts/build_gazetteer.py    # townlands + GeoNames -> data/gazetteer.json, web/data/counties.geojson
python scripts/extract.py            # Gemma 4 26B -> data/extract/NN.json (cached, resumable)
python scripts/verify.py             # checks -> web/data/tales.json, web/data/places.geojson
python scripts/respell.py && python scripts/verify.py   # modern spellings for old names, then re-check
python scripts/eval.py               # against data/labels.json
python -m http.server 8765 --directory web
```

Raw inputs (not committed) go in `data/raw/`:
- `curtin_1895.txt`: https://archive.org/download/cu31924029910563/cu31924029910563_djvu.txt
- `townlands_20m.geojson`: Townland Boundaries Generalised 20m (Tailte Éireann, data.gov.ie)
- `geonames_IE/IE.txt`: https://download.geonames.org/export/dump/IE.zip

## Credits and licences

- Tales: Jeremiah Curtin (1895), public domain. Scan: Cornell University Library via archive.org.
- Townland boundaries: © Tailte Éireann, CC BY 4.0.
- Place names: GeoNames, CC BY 4.0.
- Map tiles: © OpenStreetMap contributors.
- Model: Gemma 4 (open weights), called through Google AI Studio.
- Code: MIT.
