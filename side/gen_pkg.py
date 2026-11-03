"""SIDE-ENV (docs/prereg/PREREG_SIDE.md): scenario generator for side/envs/package_manager.py, in BFCL v4's multi-turn item format
(the fields run_mt.py and grade_mt.py read: id, cat, system, turns, initial_config, involved_classes, ground_truth).

A registry is a random layered DAG of packages with 2-4 versions each; a version depends on packages of lower layers, each through a
window of allowed versions (newer versions tend to need newer dependencies). The initial state installs 2-3 top packages by the
policy. Each scenario has 3 turns drawn from four requests; the ground truth of a turn is the policy's plan computed by the resolver
below (mutating calls only: every result depends only on the call and the state, so BFCL's unordered result check and its end-state
check accept any order that reaches the policy's state). A request whose plan is empty or impossible is redrawn.
Version 2 (SIDE-ENV-2): every request states its dependency, version and clean-up rule; no as_dependency flag, no record of what
the user asked for (version 1, commit 301ac98, left both to the function docs).
usage: python side/gen_pkg.py <out.jsonl> [n=40] [seed=0]   (the BFCL system-prompt header is copied from $POC_DATA/bfcl/mt_items.jsonl)"""
import inspect, json, os, random, re, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from side.envs.package_manager import PackageManagerAPI, vkey  # noqa: E402

CLS = "PackageManagerAPI"
POLICY = ("A package can be installed only after all its dependencies are installed at allowed versions; a package can be removed "
          "only when no installed package depends on it.")
SYL = ["bram", "cor", "dex", "fen", "gal", "hol", "jun", "kel", "lum", "mor", "nax", "ost", "pim", "quor", "riv", "sol", "tav",
       "ulm", "vex", "wyn", "zor", "ard", "bel", "cyn"]
SUF = ["", "kit", "lib", "core", "io", "net", "db", "ui", "fmt", "x"]


def registry(rng, n_pkg=16, layers=3):
    names = set()
    while len(names) < n_pkg:
        names.add(rng.choice(SYL) + rng.choice(SYL[::3]) + rng.choice(SUF))
    names = sorted(names); rng.shuffle(names)
    layer = {p: min(layers - 1, i * layers // n_pkg) for i, p in enumerate(names)}
    vers = {}
    for p in names:
        k = rng.randint(2, 4)
        vs, major, minor = [], rng.randint(1, 3), 0
        for _ in range(k):
            vs.append(f"{major}.{minor}")
            if rng.random() < 0.4:
                major, minor = major + 1, 0
            else:
                minor += 1
        vers[p] = vs
    R = {}
    for p in names:
        lower = [q for q in names if layer[q] < layer[p]]
        base = rng.sample(lower, min(len(lower), rng.randint(1, 3))) if lower else []
        R[p] = {}
        for j, v in enumerate(vers[p]):
            deps = {}
            for q in base:
                if rng.random() < 0.15:   # a version that drops a dependency
                    continue
                qv = vers[q]
                lo = min(len(qv) - 1, int(round(j / max(1, len(vers[p]) - 1) * (len(qv) - 1) + rng.choice([-1, 0, 0, 1]))))
                lo = max(0, lo)
                hi = min(len(qv), lo + rng.randint(1, 3))
                deps[q] = qv[lo:hi]
            R[p][v] = {"depends": deps, "size_mb": rng.randint(2, 300)}
    return R, layer


def plan_install(st, R, x, v):
    """the policy's plan for installing x v: [(name, version, as_dependency)] in dependency order, or None (a conflict with an
    installed package, an empty intersection, no fixpoint, or not enough disk)"""
    if x in st["installed"]:
        return None
    chosen = {x: v}
    for _ in range(50):
        allow, seen, stack = {}, {x}, [x]
        while stack:
            p = stack.pop()
            for d, a in R[p][chosen[p]]["depends"].items():
                if d in st["installed"]:
                    if st["installed"][d] not in a:
                        return None
                    continue
                allow[d] = set(a) if d not in allow else allow[d] & set(a)
                if d not in seen:
                    seen.add(d)
                    if d not in chosen:
                        chosen[d] = max(a, key=vkey)
                    stack.append(d)
        new = {x: v}
        for d, a in allow.items():
            if not a:
                return None
            new[d] = max(a, key=vkey)
        if new == chosen:
            break
        chosen = new
    else:
        return None
    depth = {}

    def dep(p):
        if p not in depth:
            depth[p] = 1 + max([dep(d) for d in R[p][chosen[p]]["depends"] if d in chosen] or [0])
        return depth[p]
    order = sorted(chosen, key=lambda p: (dep(p), p))
    if sum(R[p][chosen[p]]["size_mb"] for p in chosen) > st["disk_free_mb"]:
        return None
    return [(p, chosen[p], p != x) for p in order]


def newest_installable(st, R, x):
    for v in sorted(R[x], key=vkey, reverse=True):
        pl = plan_install(st, R, x, v)
        if pl:
            return v, pl
    return None, None


def plan_remove(st, R, x):
    """remove x (nothing depends on it), then, repeatedly, every package of x's dependency closure (installed versions, taken before
    the removal) that no remaining installed package needs -- the clean-up the request states"""
    inst = dict(st["installed"])
    if x not in inst or any(x in R[p][v]["depends"] for p, v in inst.items() if p != x):
        return None
    clo, stack = set(), [x]
    while stack:
        for d in R[stack[-1]][inst[stack.pop()]]["depends"]:
            if d in inst and d not in clo:
                clo.add(d); stack.append(d)
    out = [x]; inst.pop(x)
    while True:
        orphan = sorted(p for p in inst if p in clo and not any(p in R[q][w]["depends"] for q, w in inst.items() if q != p))
        if not orphan:
            return out
        out.append(orphan[0]); inst.pop(orphan[0])


def plan_upgrade(st, R, y):
    """the newest version of y that every installed dependent allows, with its missing dependencies installed first by the policy"""
    if y not in st["installed"]:
        return None
    cur = st["installed"][y]
    dependents = {p: R[p][v]["depends"][y] for p, v in st["installed"].items() if p != y and y in R[p][v]["depends"]}
    for w in sorted(R[y], key=vkey, reverse=True):
        if all(w in a for a in dependents.values()):
            if vkey(w) <= vkey(cur):
                return None
            fake = {**st, "installed": {p: v for p, v in st["installed"].items() if p != y}}
            pre = []
            ok = True
            for d, a in R[y][w]["depends"].items():
                if d in st["installed"]:
                    if st["installed"][d] not in a:
                        ok = False; break
                    continue
                pl = plan_install(fake, R, d, max(a, key=vkey))
                if pl is None:
                    ok = False; break
                for p, v, _ in pl:
                    if p not in [q for q, _, _ in pre]:
                        pre.append((p, v, True))
                fake = {**fake, "installed": {**fake["installed"], **{p: v for p, v, _ in pl}}}
            if not ok:
                return None
            return pre, w
    return None


def apply(env, calls):
    res = []
    for c in calls:
        res.append(eval("env." + c))
    return res


def fdocs():
    """BFCL-format function docs from the class's docstrings, each prefixed with the class description and the policy"""
    tmap = {"str": "string", "int": "integer", "bool": "boolean", "dict": "dict", "list": "array"}
    out = []
    for name, m in inspect.getmembers(PackageManagerAPI, predicate=inspect.isfunction):
        if name.startswith("_"):
            continue
        doc = inspect.getdoc(m)
        head = doc.split("\n\n")[0].replace("\n", " ")
        args = re.findall(r"^\s*(\w+) \((\w+)\): (.*)$", doc.split("Returns:")[0], re.M)
        rets = re.findall(r"^\s*(\w+) \((\w+)\): (.*)$", doc.split("Returns:")[1], re.M) if "Returns:" in doc else []
        sig = inspect.signature(m)
        req = [a for a, p in sig.parameters.items() if a != "self" and p.default is inspect.Parameter.empty]
        out.append({"name": name,
                    "description": f"{PackageManagerAPI()._api_description} {POLICY} Tool description: {head}",
                    "parameters": {"type": "dict", "properties": {a: {"type": tmap.get(t, t), "description": d} for a, t, d in args},
                                   "required": req},
                    "response": {"type": "dict", "properties": {a: {"type": tmap.get(t, t), "description": d} for a, t, d in rets}}})
    return out


def call_str(fn, **kw):
    return f"{fn}(" + ",".join(f"{k}={v!r}" for k, v in kw.items()) + ")"


def scenario(rng, k):
    R, layer = registry(rng)
    top = [p for p in R if layer[p] == max(layer.values())]
    st = {"registry": R, "installed": {}, "disk_free_mb": rng.randint(2000, 4000)}
    env = PackageManagerAPI(); env._load_scenario(st)
    for x in rng.sample(top, min(len(top), rng.randint(2, 3))):
        v, pl = newest_installable(st, R, x) if rng.random() < 0.5 else (lambda w: (w, plan_install(st, R, x, w)))(rng.choice(list(R[x])))
        if pl:
            apply(env, [call_str("install_package", name=p, version=w) for p, w, d in pl])
            st = {"registry": R, "installed": dict(env.installed), "disk_free_mb": env.disk_free_mb}
    init = {"registry": R, "installed": dict(env.installed), "disk_free_mb": env.disk_free_mb}
    turns, gts, kinds = [], [], []
    for _ in range(40):
        if len(turns) == 3:
            break
        kind = rng.choice(["install_v", "install", "remove", "upgrade"])
        st = {"registry": R, "installed": dict(env.installed), "disk_free_mb": env.disk_free_mb}
        if kind in ("install_v", "install"):
            cand = [p for p in R if p not in env.installed and layer[p] >= 1]
            if not cand:
                continue
            x = rng.choice(cand)
            dep = rng.choice([" Install its missing dependencies first, each at the newest version that every package needing it allows.",
                              " Any dependency that is not installed yet goes in first, at the newest version allowed by all the packages that need it.",
                              " Missing dependencies (and theirs) must be installed first; for each, pick the newest version that everything needing it accepts."])
            if kind == "install_v":
                v = rng.choice(list(R[x])); pl = plan_install(st, R, x, v)
                msg = rng.choice([f"Please install {x} version {v}.", f"I need {x} {v} on this machine.", f"Set up {x}, version {v}."]) + dep
            else:
                v, pl = newest_installable(st, R, x)
                msg = rng.choice([f"Install the newest version of {x} that can be installed without changing any installed package.",
                                  f"Get {x} installed: the latest version that works with what is already installed, without changing anything installed.",
                                  f"I'd like {x}, in the newest version possible without upgrading or removing anything installed."]) + dep
            if not pl or len(pl) < 2:
                continue
            calls = [call_str("install_package", name=p, version=w) for p, w, d in pl]
        elif kind == "remove":
            cand = [p for p in env.installed if plan_remove(st, R, p)]
            if not cand:
                continue
            x = rng.choice(cand); rm = plan_remove(st, R, x)
            if len(rm) < 2:
                continue
            calls = [call_str("remove_package", name=p) for p in rm]
            msg = rng.choice([f"Remove {x}, then remove every package it depended on, directly or indirectly, that no remaining installed package needs.",
                              f"Uninstall {x} and clean up: also uninstall each of its direct or indirect dependencies once nothing installed needs it.",
                              f"Get rid of {x} together with whichever of its (direct or transitive) dependencies nothing else installed still uses."])
        else:
            cand = [p for p in env.installed if plan_upgrade(st, R, p)]
            if not cand:
                continue
            y = rng.choice(cand); pre, w = plan_upgrade(st, R, y)
            calls = [call_str("install_package", name=p, version=v) for p, v, _ in pre] + [call_str("upgrade_package", name=y, version=w)]
            msg = rng.choice([f"Upgrade {y} to the newest version that every installed package depending on it allows.",
                              f"Bring {y} up to the newest version that still works with everything installed that depends on it.",
                              f"Update {y} as far as the packages that depend on it allow."]) + (
                " If that version needs a dependency that is not installed, install it first at the newest allowed version." if pre else "")
        res = apply(env, calls)
        assert not any("error" in r for r in res), (kind, calls, res)
        turns.append([{"role": "user", "content": msg}]); gts.append(calls); kinds.append(kind)
    if len(turns) < 3:
        return None
    return {"id": f"side_pkg_base_{k}", "cat": "side_pkg_base", "initial_config": {CLS: init}, "involved_classes": [CLS],
            "turns": turns, "ground_truth": gts, "kinds": kinds}


def main():
    out, n, seed = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 40, int(sys.argv[3]) if len(sys.argv) > 3 else 0
    PD = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")
    s = json.loads(open(f"{PD}/bfcl/mt_items.jsonl").readline())["system"]
    head = s[:s.index("Here is a list of functions in json format that you can invoke.")]
    system = head + "Here is a list of functions in json format that you can invoke.\n" + json.dumps(fdocs(), indent=4) + "\n"
    rng, items, k = random.Random(seed), [], 0
    while len(items) < n:
        try:
            sc = scenario(rng, len(items))
        except AssertionError:   # a plan the environment rejects (an edge case of the resolver): redrawn, counted
            sc = None
        k += 1
        if sc:
            sc["system"] = system
            items.append(sc)
    with open(out, "w") as f:
        for it in items:
            f.write(json.dumps(it) + "\n")
    from collections import Counter
    print(f"{len(items)} scenarios ({k} drawn) -> {out}; turn kinds {Counter(x for it in items for x in it['kinds'])}; ground-truth calls "
          f"per turn {sum(len(g) for it in items for g in it['ground_truth']) / (3 * len(items)):.2f}; system prompt {len(system)} characters")


if __name__ == "__main__":
    main()
