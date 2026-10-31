"""Ask hosted Gemma (Google AI Studio) what each tale is about and where it happens.

Gemma only reads and quotes. It returns, per tale: the supernatural beings, a
one-line summary, and every place the tale names, each with the exact words
it came from. verify.py then decides what is kept.

Results are cached per tale in data/extract/, so a failed or rate-limited run
can be resumed. Needs GEMINI_API_KEY in .env.

Usage: python scripts/extract.py [--model gemma-4-31b-it] [--only 22]
"""
import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/extract"
PROMPT_VERSION = "v1"

PROMPT = """You are reading one Irish folk tale, collected in south-west Munster (mostly County Kerry) and printed in 1895. The text comes from an old scan and has some OCR errors.

Return ONLY a JSON object with these keys:

"beings": the supernatural beings in the tale, from this list only: ghost, fairy, banshee, pooka, mermaid_or_seal_woman, devil, dead_returning, changeling, fairy_doctor, saint, other. Empty list if none.
"beings_quote": the exact words from the tale (copied character for character, 3 to 25 words) that show the main being.
"summary": one plain English sentence, at most 30 words, saying what happens. Do not add anything the tale does not say.
"places": every real place the tale names (towns, villages, townlands, parishes, castles, bridges, rivers, mountains, lakes, islands, counties). For each:
  "name": the place exactly as spelled in the tale
  "quote": the exact words from the tale containing that name (copied character for character, 3 to 25 words)
  "modern_name": the usual modern English spelling if you are confident it differs (for example an 1890s spelling), else null
  "role": "setting" if events of the tale happen there, else "mentioned"

Rules: copy quotes exactly, do not fix OCR errors inside quotes, do not invent places, do not include people's names, and do not include places that are not in the text.

TALE TITLE: {title}

TALE TEXT:
{text}
"""


def load_key():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"')
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("Put GEMINI_API_KEY=... in .env first")
    return key


def call_gemma(model, key, prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 2048},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read())
    return data["candidates"][0]["content"]["parts"][0]["text"], data.get("usageMetadata", {})


def parse_json(raw):
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise ValueError("no JSON object in reply")
    return json.loads(m.group(0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemma-4-31b-it")
    ap.add_argument("--only", type=int, nargs="*")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    key = load_key()
    tales = json.loads((ROOT / "data/tales.json").read_text(encoding="utf-8"))
    CACHE.mkdir(parents=True, exist_ok=True)
    for t in tales:
        if args.only and t["id"] not in args.only:
            continue
        out = CACHE / f"{t['id']:02d}.json"
        if out.exists() and not args.force:
            continue
        prompt = PROMPT.format(title=t["title"], text=t["text"])
        for attempt in range(4):
            try:
                t0 = time.time()
                raw, usage = call_gemma(args.model, key, prompt)
                result = parse_json(raw)
                break
            except urllib.error.HTTPError as e:
                msg = e.read().decode(errors="replace")[:300]
                print(f"tale {t['id']}: HTTP {e.code} {msg}")
                if e.code in (400, 401, 403, 404):
                    raise SystemExit(1)
                time.sleep(20 * (attempt + 1))
            except (ValueError, json.JSONDecodeError, KeyError, TimeoutError) as e:
                print(f"tale {t['id']}: bad reply ({e}), retrying")
                time.sleep(5)
        else:
            print(f"tale {t['id']}: gave up")
            continue
        record = {
            "tale_id": t["id"],
            "model": args.model,
            "prompt_version": PROMPT_VERSION,
            "seconds": round(time.time() - t0, 1),
            "usage": usage,
            "raw": raw,
            "result": result,
        }
        out.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"tale {t['id']:2d} {t['title'][:40]:40s} places={len(result.get('places', []))} beings={result.get('beings')}")
        time.sleep(2)


if __name__ == "__main__":
    main()
