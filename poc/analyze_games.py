"""Summaries for PoC A.  usage: analyze_games.py <tag> [<tag> ...]"""
import json
import math
import sys
from collections import defaultdict

import numpy as np

import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
RES = f"{ROOT}/results"
for tag in sys.argv[1:]:
    rows = [json.loads(l) for l in open(f"{RES}/games_{tag}.jsonl")]
    print(f"== {tag}")
    by = defaultdict(list)
    for r in rows:
        by[(r["game"], r["N"])].append(r)
    for (game, N), rs in sorted(by.items()):
        opt = math.ceil(math.log2(N + 1)) if game == "guess" else 5
        solved = [r for r in rs if r["solved"]]
        guesses = [g for r in rs for g in r["log"] if g.get("guess") is not None]
        cons = np.mean([g.get("consistent", False) for g in guesses]) if guesses else float("nan")
        fmt = np.mean([g.get("guess") is None for r in rs for g in r["log"]])
        line = (f"  {game:10s} N={N:<8d} solved {len(solved)}/{len(rs)}  turns(solved) mean {np.mean([r['turns'] for r in solved]) if solved else float('nan'):.1f}"
                f" / optimal-worst {opt}  consistent-guess rate {cons:.2f}  bad-format {fmt:.2f}")
        if game == "guess":
            md = [g["mid_dev"] for g in guesses if g.get("mid_dev") is not None]
            line += f"  |guess-mid|/width median {np.median(md):.2f}" if md else ""
        print(line)
