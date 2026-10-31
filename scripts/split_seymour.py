"""Split True Irish Ghost Stories (Seymour & Neligan, 1914) into separate accounts.

The book runs its stories together inside each chapter with no headings, so Gemma is
shown each chapter with numbered paragraphs and asked only where each new account
starts, and for a short title. Code checks the numbers and cuts the text itself;
Gemma never rewrites the text. Paragraphs before the first account (each chapter's
opening essay) are left out.

Input: data/raw/seymour_1914.txt (Project Gutenberg #14099, public domain)
Output: appends to data/tales.json as ids 101+, book "seymour1914". Replies cached in data/split/.
"""
import json
import re
import string
import time
import urllib.error
from pathlib import Path

from extract import call_gemma, load_key

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/split"
FIRST_ID = 101

PROMPT = """Below is one chapter of "True Irish Ghost Stories" (1914), a collection of ghost accounts sent in from all over Ireland. The chapter runs many separate accounts together. Paragraphs are numbered [P1], [P2]...

List where each separate account begins: the number of its first paragraph (if an account is introduced by a sentence like "The following was sent by...", start at that introducing paragraph), and a short plain title of at most 7 words naming the place or the ghost (for example "The Grey Lady of Kilkenny Castle"). Paragraphs that are general discussion and not part of any account should not start an account.

Return ONLY a JSON object: {{"accounts": [{{"start": 3, "title": "..."}}]}}

CHAPTER {num}: {title}

{paras}
"""


def paragraphs(lines):
    out, cur = [], []
    for line in lines + [""]:
        if line.strip():
            cur.append(line.strip())
        elif cur:
            out.append(re.sub(r"_", "", " ".join(cur)))
            cur = []
    return out


def chapters(text):
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("*** START"))
    end = next(i for i, l in enumerate(lines) if l.startswith("*** END"))
    heads = [i for i in range(start, end) if re.match(r"^CHAPTER [IVX]+$", lines[i].strip())]
    for n, h in enumerate(heads):
        stop = heads[n + 1] if n + 1 < len(heads) else end
        title = string.capwords(lines[h + 2].strip())  # .title() would give "Conn'S"
        yield n + 1, title, paragraphs(lines[h + 3: stop])


def main():
    text = (ROOT / "data/raw/seymour_1914.txt").read_text(encoding="utf-8").replace("\r", "")
    CACHE.mkdir(parents=True, exist_ok=True)
    key = None
    tales = [t for t in json.loads((ROOT / "data/tales.json").read_text(encoding="utf-8")) if t["id"] < FIRST_ID]
    next_id = FIRST_ID
    for num, title, paras in chapters(text):
        cache = CACHE / f"ch{num:02d}.json"
        if cache.exists():
            reply = json.loads(cache.read_text(encoding="utf-8"))
        else:
            key = key or load_key()
            numbered = "\n\n".join(f"[P{i + 1}] {p}" for i, p in enumerate(paras))
            for attempt in range(5):
                try:
                    raw, usage = call_gemma("gemma-4-26b-a4b-it", key, PROMPT.format(num=num, title=title, paras=numbered),
                                            max_tokens=16000, timeout=400)
                    break
                except (urllib.error.HTTPError, TimeoutError) as e:
                    print(f"chapter {num}: {e}, waiting")
                    time.sleep(30 * (attempt + 1))
            else:
                raise SystemExit(f"chapter {num}: gave up")
            reply = {"raw": raw, "usage": usage, "result": json.loads(raw[raw.find("{"): raw.rfind("}") + 1])}
            cache.write_text(json.dumps(reply, ensure_ascii=False, indent=1), encoding="utf-8")
        # code decides: keep only start numbers that exist, in order, without repeats
        starts = sorted({(int(a["start"]), a.get("title") or "") for a in reply["result"]["accounts"]
                         if str(a.get("start", "")).isdigit() and 1 <= int(a["start"]) <= len(paras)})
        seen, cuts = set(), []
        for s, t in starts:
            if s not in seen:
                seen.add(s)
                cuts.append((s, t))
        for k, (s, t) in enumerate(cuts):
            stop = cuts[k + 1][0] if k + 1 < len(cuts) else len(paras) + 1
            body = "\n\n".join(paras[s - 1: stop - 1])
            tales.append({"id": next_id, "book": "seymour1914", "title": t.strip() or f"Chapter {num}, account {k + 1}",
                          "title_by": "gemma", "chapter": num, "chapter_title": title, "pages": None,
                          "teller": None, "text": body})
            next_id += 1
        print(f"chapter {num:2d} {title[:40]:40s} {len(paras):3d} paragraphs -> {len(cuts)} accounts")
    (ROOT / "data/tales.json").write_text(json.dumps(tales, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(tales), "tales in total")


if __name__ == "__main__":
    main()
