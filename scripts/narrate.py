"""Narrate chosen stories with an ElevenLabs voice, once, into web/audio/.

The voice reads only the book's own words (plus the story's title), the same text
the map shows. Audio is generated here and served as static files, so the API key
never reaches the page. Each story is cached as web/audio/<id>.mp3; a rerun skips
stories already narrated, so credits are spent once.

Needs ELEVENLABS_API_KEY=... in .env.
Usage: python scripts/narrate.py [--voice <voice id>] [--list-voices] [--only 22 137]
"""
import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web/audio"
MODEL = "eleven_multilingual_v2"
FORMAT = "mp3_22050_32"  # speech only: small files for a static site (about 0.25 MB a minute)
VOICE = "JBFqnCBsd6RMkjVDRZzb"  # "George", a warm older storyteller; --list-voices to choose another
# slow, dark and a little unsteady: lower stability lets the voice drop and linger
SETTINGS = {"stability": 0.35, "similarity_boost": 0.75, "style": 0.45, "use_speaker_boost": True, "speed": 0.9}
CHUNK = 4000  # characters per request, cut at paragraph ends
# the haunted sites' stories, plus a few of the best short ones
PICKS = ["The Ghost of Sneem", "The Dead Mother", "The Midwife of Listowel",
         "Tim Sheehy Sent Back", "The White Lady of Drogheda", "The Ghostly Policeman"]


def load_key():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("ELEVENLABS_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"')
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise SystemExit("Put ELEVENLABS_API_KEY=... on its own line in .env first")
    return key


def call(key, path, body=None):
    req = urllib.request.Request(
        "https://api.elevenlabs.io" + path,
        data=json.dumps(body).encode() if body else None,
        headers={"xi-api-key": key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def chunks(text):
    out, cur = [], ""
    for para in text.split("\n\n"):
        if cur and len(cur) + len(para) > CHUNK:
            out.append(cur)
            cur = ""
        cur = f"{cur}\n\n{para}" if cur else para
    return out + [cur] if cur else out


def narrate(key, voice, text):
    parts = chunks(text)
    audio = b""
    for i, part in enumerate(parts):
        body = {"text": part, "model_id": MODEL, "voice_settings": SETTINGS,
                # neighbouring text keeps the voice's tone continuous across requests
                "previous_text": parts[i - 1][-300:] if i else None,
                "next_text": parts[i + 1][:300] if i + 1 < len(parts) else None}
        for attempt in range(4):
            try:
                audio += call(key, f"/v1/text-to-speech/{voice}?output_format={FORMAT}", body)
                break
            except urllib.error.HTTPError as e:
                msg = e.read().decode(errors="replace")[:300]
                if e.code in (400, 401, 402, 403, 404, 422):
                    raise SystemExit(f"HTTP {e.code}: {msg}")
                print(f"  HTTP {e.code}, retrying")
                time.sleep(15 * (attempt + 1))
        else:
            raise SystemExit("gave up")
    return audio  # MP3 frames from consecutive requests play back as one file


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default=VOICE)
    ap.add_argument("--list-voices", action="store_true")
    ap.add_argument("--only", type=int, nargs="*")
    args = ap.parse_args()
    key = load_key()
    if args.list_voices:
        try:
            voices = json.loads(call(key, "/v1/voices"))["voices"]
        except urllib.error.HTTPError as e:
            raise SystemExit(f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}")
        for v in voices:
            labels = ", ".join(f"{k}: {val}" for k, val in (v.get("labels") or {}).items())
            print(f"{v['voice_id']}  {v['name']:24} {labels}")
        return

    tales = json.loads((ROOT / "web/data/tales.json").read_text(encoding="utf-8"))
    sites = json.loads((ROOT / "web/data/sites.json").read_text(encoding="utf-8"))
    wanted = {s["tale"] for s in sites} | {t["id"] for t in tales if any(t["title"].startswith(p) for p in PICKS)}
    if args.only:
        wanted &= set(args.only)
    OUT.mkdir(parents=True, exist_ok=True)
    index_file = ROOT / "web/data/narration.json"
    index = json.loads(index_file.read_text(encoding="utf-8")) if index_file.exists() else {}
    for t in tales:
        if t["id"] not in wanted:
            continue
        f = OUT / f"{t['id']}.mp3"
        if not f.exists():
            text = f"{t['title']}.\n\n{t['text']}"
            t0 = time.time()
            f.write_bytes(narrate(key, args.voice, text))
            index[str(t["id"])] = {"file": f"audio/{t['id']}.mp3", "voice": args.voice, "model": MODEL, "chars": len(text)}
            index_file.write_text(json.dumps(index, indent=1), encoding="utf-8")
            print(f"{t['id']:4} {t['title'][:45]:45} {len(text):6} chars {f.stat().st_size // 1024:5} KB {time.time() - t0:5.0f}s")
    print(len(index), "stories narrated,", sum(v["chars"] for v in index.values()), "characters in total")


if __name__ == "__main__":
    main()
