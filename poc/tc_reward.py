"""TC-RL (docs/prereg/PREREG_TCRL.md): the training reward for tool calls, pure Python (the training container has no bfcl_eval).
decode(text): BFCL prompt-mode answers "[f(a=1, b='x'), g.h(c=[1, 2])]" (a ```-fenced block allowed) -> [[name, {arg: value}], ...];
a bare "f(...)" is read as "[f(...)]" (as BFCL's decoder); [] if the text makes no call; None if it starts like calls but does not decode (keyword
arguments; literal values, where a bare name is read as BFCL's decoder does: true / false / null as booleans and None, any other
name as its string). right(text, gold, functions): 1 if the calls equal the gold calls as a
multiset — names equal; each gold argument present with an equal value, unless it equals the parameter's documented default; no
extra argument unless equal to its default; numbers compare by value, strings after strip — or if both make no call."""
import ast, json, re


def _name(f):
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        b = _name(f.value)
        return None if b is None else f"{b}.{f.attr}"
    return None


def _lit(n):
    if isinstance(n, ast.Name):
        return {"true": True, "True": True, "false": False, "False": False, "null": None, "None": None}.get(n.id, n.id)
    if isinstance(n, ast.List):
        return [_lit(x) for x in n.elts]
    if isinstance(n, ast.Tuple):
        return tuple(_lit(x) for x in n.elts)
    if isinstance(n, ast.Dict):
        return {_lit(k): _lit(v) for k, v in zip(n.keys, n.values)}
    if isinstance(n, ast.Attribute):
        return _name(n)
    return ast.literal_eval(n)


def decode(text):
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        t = t.rsplit("```", 1)[0].strip()
    if not t.startswith("[") and re.match(r"^[A-Za-z_][A-Za-z0-9_.]*\(", t):
        t = "[" + t + "]"
    if not t.startswith("["):
        return []
    try:
        body = ast.parse(t, mode="eval").body
    except (SyntaxError, ValueError, MemoryError, RecursionError):
        return None
    if not isinstance(body, ast.List):
        return None
    out = []
    for c in body.elts:
        if not isinstance(c, ast.Call) or c.args or _name(c.func) is None:
            return None
        try:
            out.append([_name(c.func), {k.arg: _lit(k.value) for k in c.keywords if k.arg}])
        except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
            return None
    return out


def _canon(v):
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, (list, tuple)):
        return [_canon(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _canon(x) for k, x in v.items()}
    return repr(v)


def _key(name, args, defaults):
    d = defaults.get(name, {})
    kept = {k: _canon(v) for k, v in args.items() if not (k in d and _canon(v) == _canon(d[k]))}
    return json.dumps([name, kept], sort_keys=True)


def right(text, gold, functions):
    calls = decode(text)
    if calls is None:
        return 0.0
    if not gold or not calls:
        return float(not gold and not calls)
    defaults = {f["name"]: {k: p["default"] for k, p in f.get("parameters", {}).get("properties", {}).items()
                            if isinstance(p, dict) and "default" in p} for f in functions}
    return float(sorted(_key(n, a, defaults) for n, a in calls) == sorted(_key(n, a, defaults) for n, a in gold))
