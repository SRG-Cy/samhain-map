"""List the Gemma models this AI Studio key can call."""
import json
import urllib.request

from extract import load_key

req = urllib.request.Request(
    "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200",
    headers={"x-goog-api-key": load_key()},
)
with urllib.request.urlopen(req, timeout=60) as r:
    models = json.loads(r.read())["models"]
for m in models:
    if "gemma" in m["name"]:
        print(m["name"], m.get("inputTokenLimit"), m.get("supportedGenerationMethods"))
