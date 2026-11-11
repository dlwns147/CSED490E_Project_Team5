"""Grid scoring v2 (FINDINGS 2026-11-11 03:xx): an answer cell is right when it names the gold value among the category's listed values, and names
no other. Reading the shared misses showed `run_zebra.gp_score` failing right answers on format alone, for thinking runs more than for programs:
"blu-ray" for "blu-ray player", "Diane" for "Diane DeNiro", 5.5 for "$5.50", 78000000 for "78 million"; and passing "B-" for "B+".

A value names listed value v when, after lowercasing (with + and a trailing - kept as words):
  1. numbers: both are numbers and equal ("$5.50" = 5.5; "78 million" = 78000000 = 78 when every listed value is in millions), else
  2. text: equal letters and digits, ignoring a plural s, else
  3. the value is a whole-word part of exactly one listed value ("raft" for "raft spider", "D" for "Line D").
Each rule counts only if exactly one listed value matches. No model call, no labels beyond the gold grid.
"""
import re

_MUL = {"thousand": 1e3, "million": 1e6, "billion": 1e9}


def _norm(s):
    s = str(s).lower().strip().replace("+", " plus ")
    s = re.sub(r"-\s*$", " minus", s)
    return re.sub(r"[^a-z0-9]", "", s)


def _num(x, scale=True):
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return float(x)
    m = re.search(r"-?\d[\d,]*(?:\.\d+)?", str(x))
    if not m:
        return None
    v = float(m.group().replace(",", ""))
    if scale:
        for w, f in _MUL.items():
            if w in str(x).lower():
                v *= f
    return v


def match(x, vals):
    """index into vals of the one listed value that x names, or None"""
    if x is None:
        return None
    if all(_num(v) is not None for v in vals) and _num(x) is not None:
        for scale in (True, False):   # "78 million" listed: 78000000 and 78 both name it
            h = [k for k, v in enumerate(vals) if abs(_num(v, scale) - _num(x)) < 1e-6]
            if len(h) == 1:
                return h[0]
        return None
    nx = _norm(x)
    h = [k for k, v in enumerate(vals) if _norm(v) == nx or _norm(v).rstrip("s") == nx.rstrip("s")]
    if len(h) == 1:
        return h[0]
    if not nx:
        return None
    w = r"(?<![a-z0-9])" + re.escape(str(x).lower().strip()) + r"(?![a-z0-9])"
    h = [k for k, v in enumerate(vals) if re.search(w, str(v).lower())]
    return h[0] if len(h) == 1 else None


def score(g, r):
    """(exact, cell accuracy) of answer grid g ({category: [value per first-category value]}) against puzzle r (fields cats, gold)"""
    if not isinstance(g, dict):
        return False, 0.0
    ck = lambda a: re.sub(r"[^a-z0-9]", "", str(a).lower()).rstrip("s")
    cats = {ck(a): v for a, v in r["cats"][1:]}
    got = {ck(k): v for k, v in g.items() if isinstance(v, list)}
    n = c = 0
    for a, gold in r["gold"].items():
        vals, v = cats[ck(a)], got.get(ck(a)) or []
        for k, y in enumerate(gold):
            n += 1
            m = match(v[k], vals) if k < len(v) else None
            c += m is not None and m == match(y, vals)
    return c == n, c / n
