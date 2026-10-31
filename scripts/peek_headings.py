"""Print all-caps lines from the OCR text, to find where each tale starts."""
import re
import sys
from pathlib import Path

text = Path(__file__).resolve().parents[1].joinpath("data/raw/curtin_1895.txt").read_text(encoding="utf-8")
lines = text.splitlines()
start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
for n, line in enumerate(lines, 1):
    s = line.strip()
    if n >= start and len(s) >= 8 and re.fullmatch(r"[A-Z][A-Z .'’,\-]+", s):
        print(n, s)
