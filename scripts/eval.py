"""Score Gemma alone, and Gemma + the checker, against data/labels.json.

"Gemma alone" = every place Gemma reported, as if we pinned them all.
"Pinned" = only places verify.py accepted.
Writes data/eval.json and prints a table for the post.
"""
import json
from pathlib import Path

from verify import norm

ROOT = Path(__file__).resolve().parents[1]


def main():
    labels = json.loads((ROOT / "data/labels.json").read_text(encoding="utf-8"))
    tales = {t["id"]: t for t in json.loads((ROOT / "web/data/tales.json").read_text(encoding="utf-8"))}
    rows, tot = [], {"gold": 0, "g_tp": 0, "g_fp": 0, "p_tp": 0, "p_fp": 0, "invented": 0}
    for tid, gold in labels.items():
        if tid.startswith("_") or int(tid) not in tales:
            continue
        t = tales[int(tid)]
        gold_n = {norm(g) for g in gold}
        reported = {norm(p["name"]) for p in t["places"]}
        pinned = {norm(p["name"]) for p in t["places"] if p.get("status", "").startswith("pinned")}
        invented = {norm(p["name"]) for p in t["places"] if p.get("status", "").startswith("refused: quote")}
        # a reported name counts as correct if it matches, contains or is contained in a gold name
        hit = lambda n: any(n == g or n in g or g in n for g in gold_n)
        g_tp = sum(1 for g in gold_n if any(n == g or n in g or g in n for n in reported))
        p_tp = sum(1 for g in gold_n if any(n == g or n in g or g in n for n in pinned))
        row = {
            "tale": int(tid), "title": t["title"], "gold": len(gold_n),
            "gemma_found": g_tp, "gemma_wrong": sum(1 for n in reported if not hit(n)),
            "pinned_found": p_tp, "pinned_wrong": sum(1 for n in pinned if not hit(n)),
            "rejected_as_not_in_text": len(invented),
            "missed_by_pins": sorted(g for g in gold_n if not any(n == g or n in g or g in n for n in pinned)),
            "wrong_reported": sorted(n for n in reported if not hit(n)),
        }
        rows.append(row)
        tot["gold"] += row["gold"]; tot["g_tp"] += g_tp; tot["g_fp"] += row["gemma_wrong"]
        tot["p_tp"] += p_tp; tot["p_fp"] += row["pinned_wrong"]; tot["invented"] += len(invented)

    (ROOT / "data/eval.json").write_text(json.dumps({"rows": rows, "totals": tot}, indent=1), encoding="utf-8")
    print(f"{'tale':<45} gold  gemma(found/wrong)  pinned(found/wrong)  missed by pins")
    for r in rows:
        print(f"{r['title'][:44]:<45} {r['gold']:>4}  {r['gemma_found']:>5}/{r['gemma_wrong']:<5}        {r['pinned_found']:>5}/{r['pinned_wrong']:<5}       {', '.join(r['missed_by_pins'])}   wrong: {', '.join(r['wrong_reported'])}")
    print("TOTAL", tot)


if __name__ == "__main__":
    main()
