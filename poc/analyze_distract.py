"""S4d dose-response summary: all-variants-correct /100 and distractor-call rate by model x K (related) + unrelated control."""
import json, os, sys
import numpy as np
RES = "/NAS/SJ/POSTECH/nlp/results"
import re


def called(r):
    """a distractor counts as used if it is called outside its own definition, comments stripped (fixes 'fib(0)' in a comment)"""
    code = re.sub(r"#[^\n]*", "", r.get("code") or "")
    for d in r.get("distractors", []):
        body = re.sub(rf"def {d}\(.*?(?=\ndef |\Z)", "", code, flags=re.S)   # drop its own definition
        if re.search(rf"\b{d}\s*\(", body):
            return True
    return False
def main():
  for m in sys.argv[1:] or ["8b", "14b", "32b"]:
      row = []
      for k in ["dis0", "dis2", "dis4", "dis8", "disU8"]:
          acc, calls, nd = [], [], []
          for sd in (1, 2):
              f = f"{RES}/geocross_geox{m}_{k}_t07s{sd}.jsonl"
              if not os.path.exists(f):
                  continue
              rs = [json.loads(l) for l in open(f)]
              acc.append(sum(r["class"] == "correct_all" for r in rs))
              calls.append(np.mean([called(r) for r in rs if r.get("distractors")]) if any(r.get("distractors") for r in rs) else 0)
              nd.append(np.mean([len(r.get("distractors", [])) for r in rs]))
          if acc:
              row.append(f"{k}: {np.mean(acc):.1f} (seeds {acc}, called {np.mean(calls):.2f}, n_dis {np.mean(nd):.1f})")
      print(m, " | ".join(row))


if __name__ == "__main__":
    main()
