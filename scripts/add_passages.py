"""Add the hand-picked passages in data/sites.json to data/tales.json (ids 301+).

Each passage is cut from its public-domain book between an exact start and end line;
code refuses a passage whose start or end isn't found exactly once. Run after
split_tales.py and split_seymour.py (which rewrite data/tales.json).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    cfg = json.loads((ROOT / "data/sites.json").read_text(encoding="utf-8"))
    tales = [t for t in json.loads((ROOT / "data/tales.json").read_text(encoding="utf-8")) if t["id"] < 300]
    for p in cfg["passages"]:
        text = (ROOT / "data/raw" / p["file"]).read_text(encoding="utf-8").replace("\r", "")
        if text.count(p["start"]) != 1 or text.count(p["end"]) != 1:
            raise SystemExit(f"passage {p['id']}: start or end not found exactly once in {p['file']}")
        a = text.index(p["start"])
        body = text[a: text.index(p["end"], a) + len(p["end"])]
        paras = [" ".join(line.strip() for line in para.splitlines()) for para in body.split("\n\n") if para.strip()]
        tales.append({"id": p["id"], "book": p["book"], "title": p["title"], "pages": None, "teller": None,
                      "text": "\n\n".join(paras).replace("_", "")})
        print(p["id"], p["title"], len(paras), "paragraphs")
    (ROOT / "data/tales.json").write_text(json.dumps(tales, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
