"""Send a tiny prompt to each Gemma model to see which one is answering right now."""
import sys
import urllib.error

from extract import call_gemma, load_key

key = load_key()
for model in sys.argv[1:] or ["gemma-4-31b-it", "gemma-4-26b-a4b-it"]:
    try:
        text, usage = call_gemma(model, key, 'Reply with the JSON {"ok": true} and nothing else.')
        print(model, "OK", text.strip()[:80], usage.get("totalTokenCount"))
    except urllib.error.HTTPError as e:
        print(model, "HTTP", e.code, e.read().decode(errors="replace")[:160].replace("\n", " "))
