"""Split the archive.org OCR text of Curtin (1895) into one record per tale.

Tale start lines were found by hand with peek_headings.py, because the OCR
mangles some headings. Output: data/tales.json
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/curtin_1895.txt"
OUT = ROOT / "data/tales.json"

# (first line of the heading, 1-based, as in the raw file), title
TALES = [
    (558, "John Connors and the Fairies"),
    (1000, "Fitzgerald and Daniel O'Donohue"),
    (1201, "The Fairies of Rahonain and Elizabeth Shea"),
    (1409, "The Knights of Kerry: Rahonain Castle"),
    (1664, "The Cattle Jobber of Awnascawil"),
    (1900, "The Midwife of Listowel"),
    (2025, "Daniel Crowley and the Ghosts"),
    (2361, "Tom Daly and the Nut-eating Ghost"),
    (2491, "Tom Connors and the Dead Girl"),
    (2595, "The Farmer of Tralee and the Fairy Cows"),
    (2813, "The Two Gamblers and the Fairies"),
    (3051, "The Girl and the Robber"),
    (3371, "Maurice Griffin the Fairy Doctor"),
    (3692, "The Three Sisters and their Husbands' Three Brothers"),
    (4163, "John Shea and the Treasure"),
    (4489, "St. Martin's Eve"),
    (4782, "James Murray and Saint Martin"),
    (4907, "Fairy Cows"),
    (5118, "John Reardon and the Sister Ghosts"),
    (5304, "Maggie Doyle and the Dead Man"),
    (5467, "Pat Doyle and the Ghost"),
    (5614, "The Ghost of Sneem"),
    (5746, "The Dead Mother"),
    (5870, "Tim Sheehy Sent Back to this World to Prove his Innocence"),
    (5981, "Tom Moore and the Seal Woman"),
    (6139, "The Four-leafed Shamrock"),
    (6200, "John Cokeley and the Fairy"),
    (6547, "Tom Foley's Ghost"),
    (7133, "The Blood-drawing Ghost"),
    (7601, "Murderous Ghosts"),
]
END_LINE = 7848  # publisher's adverts start here

RUNNING_HEAD = re.compile(r"^(\d{1,3}\s+.{3,60}|.{3,60}\s+\d{1,3})$")  # "The Knights of Kerry 31"
PAGE_NUM = re.compile(r"\b(\d{1,3})\b")


def clean(lines):
    """Drop running heads and page numbers, rejoin hyphenated words, rebuild paragraphs."""
    pages = []
    kept = []
    for raw in lines:
        s = raw.strip()
        if not s:
            kept.append("")
            continue
        if re.fullmatch(r"\d{1,3}", s):
            pages.append(int(s))
            continue
        if RUNNING_HEAD.fullmatch(s) and len(s) < 45 and not s.endswith((".", ",", ";")):
            m = PAGE_NUM.search(s)
            if m:
                pages.append(int(m.group(1)))
            continue
        kept.append(s)

    paragraphs, cur = [], ""
    for s in kept:
        if not s:
            if cur:
                paragraphs.append(cur)
                cur = ""
            continue
        if cur.endswith("-"):
            cur = cur[:-1] + s
        else:
            cur = f"{cur} {s}" if cur else s
    if cur:
        paragraphs.append(cur)
    text = "\n\n".join(re.sub(r"\s+", " ", p) for p in paragraphs)
    return text, pages


def main():
    lines = RAW.read_text(encoding="utf-8").splitlines()
    starts = [s for s, _ in TALES] + [END_LINE]
    tales = []
    prev_page = 1
    for i, (start, title) in enumerate(TALES):
        body = lines[start - 1 : starts[i + 1] - 1]
        # skip the heading lines themselves (upper-case, at the top)
        while body and (not body[0].strip() or body[0].strip().upper() == body[0].strip()):
            body = body[1:]
        text, pages = clean(body)
        # OCR noise produces stray small numbers; keep pages that move forward
        pages = [p for p in pages if prev_page <= p <= prev_page + 25]
        if pages:
            prev_page = max(pages)
        teller = None
        m = re.search(r"TOLD BY ([A-Z ]+)", "\n".join(lines[start - 1 : start + 5]))
        if m:
            teller = m.group(1).title().strip()
        tales.append(
            {
                "id": i + 1,
                "title": title,
                "source_line": start,
                "pages": [min(pages), max(pages)] if pages else None,
                "teller": teller,
                "text": text,
            }
        )
    OUT.write_text(json.dumps(tales, ensure_ascii=False, indent=1), encoding="utf-8")
    for t in tales:
        print(t["id"], t["title"], t["pages"], t["teller"], len(t["text"]), "chars")


if __name__ == "__main__":
    main()
