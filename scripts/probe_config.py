"""Try a few generation settings on one tale to find one that answers cleanly."""
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from extract import PROMPT, load_key, parse_json

ROOT = Path(__file__).resolve().parents[1]
MODEL = "gemma-4-26b-a4b-it"
tale = next(t for t in json.loads((ROOT / "data/tales.json").read_text(encoding="utf-8")) if t["id"] == 22)
prompt = PROMPT.format(title=tale["title"], text=tale["text"])
key = load_key()

CONFIGS = {
    "json_mode_t0.3": {"temperature": 0.3, "maxOutputTokens": 8192, "responseMimeType": "application/json"},
    "json_mode_no_thinking": {"temperature": 0.3, "maxOutputTokens": 8192, "responseMimeType": "application/json",
                              "thinkingConfig": {"thinkingBudget": 0}},
    "json_mode_low_thinking": {"temperature": 0.3, "maxOutputTokens": 8192, "responseMimeType": "application/json",
                               "thinkingConfig": {"thinkingLevel": "low"}},
}

for name, cfg in CONFIGS.items():
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": cfg}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": key})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            data = json.loads(r.read())
        parts = data["candidates"][0]["content"]["parts"]
        ans = [p["text"] for p in parts if "text" in p and not p.get("thought")]
        raw = ans[-1] if ans else ""
        try:
            res = parse_json(raw)
            print(name, "OK", round(time.time() - t0, 1), "s", [p["name"] for p in res["places"]], res.get("beings"))
        except ValueError as e:
            print(name, "PARSE FAIL", len(raw), raw[:200].replace("\n", " "))
        print("   usage", data.get("usageMetadata"))
    except urllib.error.HTTPError as e:
        print(name, "HTTP", e.code, e.read().decode(errors="replace")[:200].replace("\n", " "))
