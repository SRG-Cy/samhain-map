"""Find a freely licensed photo for each haunted site on Wikimedia Commons.

Takes the lead image of the site's Wikipedia article and keeps it only if its
Commons licence is public domain, CC0, CC BY or CC BY-SA. Photographer, licence
and file page are stored with it, because those licences require the credit.

Writes data/site_images.json; scripts/sites.py adds them to web/data/sites.json.
"""
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = {
    "Leap Castle": "Leap Castle", "Loftus Hall": "Loftus Hall", "Charles Fort": "Charles Fort (Ireland)",
    "Kilkea Castle": "Kilkea Castle", "Dunluce Castle": "Dunluce Castle", "Dunseverick Castle": "Dunseverick Castle",
    "Clare Abbey": "Clare Abbey", "Lough Leane": "Lough Leane",
}
FREE = re.compile(r"^(public domain|pd|cc0|cc by(-sa)? [0-9.]+)", re.I)


def api(host, **params):
    params.update(format="json", formatversion=2)
    req = urllib.request.Request(f"https://{host}/w/api.php?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": "samhain-map/1.0 (https://github.com/SRG-Cy/samhain-map)"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()


def main():
    out = {}
    for site, article in ARTICLES.items():
        page = api("en.wikipedia.org", action="query", prop="pageimages", piprop="name", titles=article, redirects=1)["query"]["pages"][0]
        name = page.get("pageimage")
        if not name:
            print(f"{site:20} no lead image")
            continue
        info = api("commons.wikimedia.org", action="query", prop="imageinfo", iiprop="url|extmetadata",
                   iiurlwidth=900, titles=f"File:{name}")["query"]["pages"][0]
        if "imageinfo" not in info:
            print(f"{site:20} {name}: not on Commons (probably non-free), skipped")
            continue
        ii = info["imageinfo"][0]
        meta = ii["extmetadata"]
        licence = text(meta.get("LicenseShortName", {}).get("value"))
        author = text(meta.get("Artist", {}).get("value")) or "unknown"
        if not FREE.match(licence):
            print(f"{site:20} {name}: licence {licence!r} not accepted")
            continue
        if re.search(r"BY-NC|NonCommercial|ND\b", author, re.I):
            # e.g. a Commons file tagged CC BY-SA whose own credit line says CC BY-NC: when they disagree, leave it out
            print(f"{site:20} {name}: credit line names a non-free licence, skipped")
            continue
        out[site] = {
            "src": ii["thumburl"].split("?")[0], "page": ii["descriptionurl"],
            "author": author,
            "licence": licence, "licence_url": meta.get("LicenseUrl", {}).get("value"),
        }
        print(f"{site:20} {licence:14} {out[site]['author'][:40]}")
    (ROOT / "data/site_images.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
