"""M2 (results/PREREG_M2_M4.md): harness-side metamorphic probing of offered helpers (no model involved).
Each helper with a scalar (number / bool / str) result is run on random integer inputs and on transformed copies: translation, rotation by 90
degrees, mirroring (x -> -x), reversed vertex order (polygon arguments) and swapped 2nd/3rd point arguments (>= 3 point parameters).
A relation is recorded only if it holds on all probes: "unchanged" or "negated". Helpers with an orientation-reversing relation that is not
"unchanged" get a verified behaviour sentence, inserted as a comment line in their source (run_geo_cross.py --auto_contract).
usage: python contract_probe.py   -> results/contracts.json"""
import inspect, json, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo_distractors import NEW, RELATED, with_deps  # noqa: E402
import run_geo as G  # noqa: E402

RES = "/NAS/SJ/POSTECH/nlp/results"
POINT_ARGS = {"a", "b", "c", "d", "p", "q", "o"}


def load(name):
    ns = {}
    src = {**RELATED, **NEW}
    for dep in reversed(with_deps([name])):
        exec(src[dep], ns)
    return ns[name]


def rand_point(rng):
    return (rng.randint(-50, 50), rng.randint(-50, 50))


def rand_args(params, rng):
    out = []
    for p in params:
        if p in POINT_ARGS:
            out.append(rand_point(rng))
        elif p == "poly":
            while True:
                H = G.hull_pts([rand_point(rng) for _ in range(8)])
                if len(H) >= 3:
                    break
            out.append(H)
        elif p == "points":
            out.append([rand_point(rng) for _ in range(8)])
        else:
            return None
    return out


def tmap(args, params, f):
    return [f(x) if p in POINT_ARGS else ([f(y) for y in x] if p in ("poly", "points") else x) for x, p in zip(args, params)]


def transforms(params):
    T = {"translation": lambda a: tmap(a, params, lambda p: (p[0] + 7, p[1] - 11)),
         "rotation": lambda a: tmap(a, params, lambda p: (-p[1], p[0])),
         "mirroring the input (x -> -x)": lambda a: tmap(a, params, lambda p: (-p[0], p[1]))}
    if "poly" in params:
        T["reversing the vertex order"] = lambda a: [x[::-1] if p == "poly" else x for x, p in zip(a, params)]
    pts = [i for i, p in enumerate(params) if p in POINT_ARGS]
    if len(pts) >= 3:
        i, j = pts[1], pts[2]
        def sw(a, i=i, j=j):
            a = list(a); a[i], a[j] = a[j], a[i]; return a
        T[f"swapping {params[i]} and {params[j]}"] = sw
    return T


def probe(name, n=200, seed=0):
    f = load(name)
    params = list(inspect.signature(f).parameters)
    rng = random.Random(seed)
    rel = {}
    for tname, T in transforms(params).items():
        kinds = set()
        for _ in range(n):
            args = rand_args(params, rng)
            if args is None:
                return None
            y, y2 = f(*args), f(*T(args))
            if not isinstance(y, (int, float, bool, str)):
                return None
            if y2 == y:
                kinds.add("unchanged")
            elif isinstance(y, (int, float)) and not isinstance(y, bool) and y2 == -y:
                kinds.add("negated")
            else:
                kinds.add("other")
        rel[tname] = "unchanged" if kinds == {"unchanged"} else ("negated" if kinds <= {"negated", "unchanged"} and "negated" in kinds else "changes")
    return rel


def statement(rel):
    flips = [t for t, r in rel.items() if r != "unchanged"]
    if not flips:
        return None
    same = [t for t, r in rel.items() if r == "unchanged"]
    parts = [f"{t} {'negates' if rel[t] == 'negated' else 'changes'} the result" for t in flips]
    s = "probe-verified: " + "; ".join(parts)
    return s + ("; " + " and ".join(same) + " leave it unchanged" if same else "")


if __name__ == "__main__":
    out = {}
    for name in list(RELATED) + list(NEW):
        rel = probe(name)
        if rel is None:
            print(f"{name:20s} (not probed: non-scalar result or unknown argument type)")
            continue
        st = statement(rel)
        out[name] = {"relations": rel, "statement": st}
        print(f"{name:20s} {rel}\n{'':20s} -> {st}")
    json.dump(out, open(f"{RES}/contracts.json", "w"), indent=1)
