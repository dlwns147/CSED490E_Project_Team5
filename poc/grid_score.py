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


def clue_texts(puzzle):
    """the numbered clues of a Puzzle Baron grid puzzle, in order (as run_zebra.gp_clues)"""
    t = puzzle.split("Clues:")[1].split("While answering")[0] if "Clues:" in puzzle else ""
    return re.findall(r"^\s*\d+\.\s*(.+)$", t, re.M)


def free_checks(code, r, grid=None):
    """PREREG_FREE: checks of a translated grid program against the puzzle's own text; no model call, and the program is only parsed, never run.
    LV (listed values): every value in `groups` names exactly one listed value of its category (match), no two values of a category name the same
    one, and every value a clue expression refers to names a listed value of some category (the harness resolves a value written under another
    category's name, so only a value that names nothing is flagged).
    EA (entity alignment): the translation prompt asks for one expression per clue, in order. When the program has as many expressions as the
    puzzle has clues, expression i must refer to every listed value outside the first category that clue i names (found in its text, longest value
    first). With a different number of expressions, EA does not apply.
    OR (both readings of "either A or B", only with the program's solution grid): in a clue "X is either A or B", where A and B each name one
    listed value of different categories, the solution must put A and B in different rows. A solution that puts them together satisfies the
    inclusive reading only; the puzzle promises one solution, so an answer that depends on how "or" is read is not checked by the count.
    Returns [(check, message)]; empty = passes, or the program cannot be parsed (then the solver's own errors apply)."""
    import ast
    out = or_check(grid, r) if isinstance(grid, dict) else []
    try:
        tree = ast.parse(code or "")
        lit = {t.id: ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) for t in n.targets
               if isinstance(t, ast.Name) and t.id in ("groups", "clues")}
    except (SyntaxError, ValueError, TypeError, MemoryError, RecursionError):
        return []
    groups, clues = lit.get("groups"), lit.get("clues")
    if not isinstance(groups, dict) or not isinstance(clues, list):
        return []
    ck = lambda a: re.sub(r"[^a-z0-9]", "", str(a).lower()).rstrip("s")
    cats = {ck(a): (j, a, v) for j, (a, v) in enumerate(r["cats"])}
    for c, vals in groups.items():
        if ck(c) not in cats or not isinstance(vals, list):
            continue
        j, a, lv = cats[ck(c)]
        hit = [match(x, lv) for x in vals]
        out += [("LV", f"'{x}' is not one of the listed {a}") for x, h in zip(vals, hit) if h is None]
        if len([h for h in hit if h is not None]) != len({h for h in hit if h is not None}):
            out.append(("LV", f"two values of {a} name the same listed value"))

    def name(c, x):   # (category index, value index) of the listed value that x names: in its own category first, else in exactly one other
        if ck(c) in cats:
            lv = cats[ck(c)][2]
            k = [k for k, y in enumerate(lv) if _norm(y) == _norm(x)]   # the value as listed ("7:30am"), before match's number rule
            k = k[0] if len(k) == 1 else match(x, lv)
            if k is not None:
                return (cats[ck(c)][0], k)
        h = [(j, k) for j, (a, v) in enumerate(r["cats"]) for k in [match(x, v)] if k is not None]
        return h[0] if len(h) == 1 else None
    E = []
    for e in clues:
        s = set()
        try:   # p['<category>:<value>'] subscripts, read from the expression's syntax tree (values may hold quotes: "perle d'or")
            keys = [n.slice.value for n in ast.walk(ast.parse(str(e), mode="eval")) if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name)
                    and n.value.id == "p" and isinstance(n.slice, ast.Constant) and isinstance(n.slice.value, str) and ":" in n.slice.value]
        except (SyntaxError, ValueError, MemoryError, RecursionError):
            keys = []
        for c, x in (k.split(":", 1) for k in keys):
            h = name(c, x)
            if h is None:
                out.append(("LV", f"'{x}' in a clue expression names no listed value"))
            elif h[0] > 0:
                s.add(h)
        E.append(s)
    T = clue_texts(r["puzzle"])
    if len(T) == len(E):
        # a bare number in a clue may be a value or an offset ("2 more"), so only values the text names unambiguously (not numbers) are required
        cand = sorted(((j, k, str(x)) for j, (a, v) in enumerate(r["cats"]) if j > 0 for k, x in enumerate(v)), key=lambda z: -len(z[2]))
        cand = [z for z in cand if _num(z[2], False) is None or re.sub(r"[\d\s.,$%]", "", z[2])]
        for i, t in enumerate(T):
            low, need, taken = t.lower(), set(), []
            for j, k, x in cand:
                for m in re.finditer(r"(?<![a-z0-9])" + re.escape(x.lower()) + r"(?![a-z0-9])", low):
                    if not any(m.start() < b and a < m.end() for a, b in taken):
                        taken.append((m.start(), m.end())); need.add((j, k))
            miss = need - E[i]
            if miss:
                out.append(("EA", f"clue {i + 1} names {', '.join(sorted(str(r['cats'][j][1][k]) for j, k in miss))}, which its expression does not use"))
    return out


def named(text, r, first=True):
    """(category index, value index) of each listed value that `text` names, longest value first so "Line D" is not also read as "D" """
    cand = sorted(((j, k, str(x)) for j, (a, v) in enumerate(r["cats"]) if first or j > 0 for k, x in enumerate(v)), key=lambda z: -len(z[2]))
    low, got, taken = text.lower(), [], []
    for j, k, x in cand:
        for m in re.finditer(r"(?<![a-z0-9])" + re.escape(x.lower()) + r"(?![a-z0-9])", low):
            if not any(m.start() < b and a < m.end() for a, b in taken):
                taken.append((m.start(), m.end())); got.append((j, k))
    return got


def or_check(grid, r):
    """OR of free_checks: "either A or B" clues whose two sides each name one listed value, of different categories, must not share a row"""
    ck = lambda a: re.sub(r"[^a-z0-9]", "", str(a).lower()).rstrip("s")
    got = {ck(k): v for k, v in grid.items() if isinstance(v, list)}

    def row(h):
        j, k = h
        if j == 0:
            return k
        col = got.get(ck(r["cats"][j][0])) or []
        rows = [i for i, x in enumerate(col) if match(x, r["cats"][j][1]) == k]
        return rows[0] if len(rows) == 1 else None
    out = []
    for i, t in enumerate(clue_texts(r["puzzle"])):
        m = re.search(r"\beither\b(.+?)\bor\b(.+?)$", t, re.I)
        if not m:
            continue
        a, b = named(m.group(1), r), named(m.group(2), r)
        if len(a) == 1 and len(b) == 1 and a[0][0] != b[0][0]:
            ra, rb = row(a[0]), row(b[0])
            if ra is not None and ra == rb:
                out.append(("OR", f"clue {i + 1} says either {r['cats'][a[0][0]][1][a[0][1]]} or {r['cats'][b[0][0]][1][b[0][1]]}, and the solution makes them the same {r['cats'][0][0]}"))
    return out



def expr_eval(e, p):
    """value of a parsed clue expression (ast) with p = {key: house}, by a whitelisted interpreter (comparisons, + - *, abs / min / max, and / or /
    not, in): the model's expression is read, never executed. Raises ValueError on anything else and KeyError on an unknown key."""
    import ast
    import operator as O
    cmp = {ast.Eq: O.eq, ast.NotEq: O.ne, ast.Lt: O.lt, ast.Gt: O.gt, ast.LtE: O.le, ast.GtE: O.ge,
           ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b}
    binop = {ast.Add: O.add, ast.Sub: O.sub, ast.Mult: O.mul}
    n, ev = e, lambda x: expr_eval(x, p)
    if isinstance(n, ast.Expression):
        return ev(n.body)
    if isinstance(n, ast.Constant):
        return n.value
    if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant):
        return p[n.slice.value]
    if isinstance(n, ast.BinOp) and type(n.op) in binop:
        return binop[type(n.op)](ev(n.left), ev(n.right))
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.Not)):
        return -ev(n.operand) if isinstance(n.op, ast.USub) else not ev(n.operand)
    if isinstance(n, ast.BoolOp):
        v = [ev(x) for x in n.values]
        return all(v) if isinstance(n.op, ast.And) else any(v)
    if isinstance(n, (ast.Tuple, ast.List, ast.Set)):
        return [ev(x) for x in n.elts]
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("abs", "min", "max") and not n.keywords:
        return {"abs": abs, "min": min, "max": max}[n.func.id](*[ev(x) for x in n.args])
    if isinstance(n, ast.Compare) and all(type(o) in cmp for o in n.ops):
        a = ev(n.left)
        for o, c in zip(n.ops, n.comparators):
            b = ev(c)
            if not cmp[type(o)](a, b):
                return False
            a = b
        return True
    raise ValueError(type(n).__name__)


def disagree(a, b, n, tries=300, seed=0):
    """PREREG_CONV: do clue expressions a and b (strings) say different things? True if they name different values (keys compared after _norm) or
    differ on some assignment of houses 1..n to the values they name (every assignment when they name at most 3 values, else `tries` random ones);
    False if they agree on all tried; None if either cannot be read."""
    import ast
    import itertools
    import random
    try:
        ea, eb = ast.parse(a, mode="eval"), ast.parse(b, mode="eval")
    except (SyntaxError, ValueError, TypeError, MemoryError, RecursionError):
        return None
    key = lambda e: {s.slice.value for s in ast.walk(e) if isinstance(s, ast.Subscript) and isinstance(s.slice, ast.Constant)}
    ka, kb = key(ea), key(eb)
    if {_norm(k) for k in ka} != {_norm(k) for k in kb}:
        return True
    keys, nb = sorted(ka), {_norm(k): k for k in kb}
    rng = random.Random(seed)
    pts = itertools.product(range(1, n + 1), repeat=len(keys)) if len(keys) <= 3 else (tuple(rng.randint(1, n) for _ in keys) for _ in range(tries))
    for t in pts:
        pa = dict(zip(keys, t))
        try:
            if bool(expr_eval(ea, pa)) != bool(expr_eval(eb, {nb[_norm(k)]: v for k, v in pa.items()})):
                return True
        except (ValueError, KeyError, TypeError, ZeroDivisionError, RecursionError):
            return None
    return False


def clue_pairs(code_a, code_b, puzzle, n):
    """PREREG_CONV: [(clue text, b's expression)] for the clues that programs a and b (both with one expression per clue, in order) read differently"""
    import ast

    def clues(code):
        try:
            for nd in ast.parse(code or "").body:
                if isinstance(nd, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "clues" for t in nd.targets):
                    v = ast.literal_eval(nd.value)
                    return [str(x) for x in v] if isinstance(v, (list, tuple)) else []
        except (SyntaxError, ValueError, TypeError, MemoryError, RecursionError):
            pass
        return []
    tx, ca, cb = clue_texts(puzzle), clues(code_a), clues(code_b)
    if not tx or not (len(tx) == len(ca) == len(cb)):
        return []
    return [(t, y) for t, x, y in zip(tx, ca, cb) if disagree(x, y, n)]
