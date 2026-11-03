"""SIDE-ENV-3 (docs/prereg/PREREG_SIDE.md): the registered analysis of a family's model runs, for any environment class.
  per arm: right, output ktokens per conversation; T - N paired 95% interval over scenarios (normal, n-1 sd, as SIDE-ENV-2);
  silent share of N's failures, registered whole-conversation definition (no error result, no repeated step, no force-quit);
  first diverging turn (each trajectory replayed turn by turn against the ground truth; public state compared): its kind, the
  attributes that differ, and whether that turn was silent (no error result, no repeated step).
Reads results/tc/mt_<tag>_<arm>_s1.jsonl (run_mt.py) and mt_grades_<tag>_<arm>_s1.json (grade_mt.py).
usage: python side/analyze_env.py <Class=side.envs.module> <items.jsonl> <tag> [arms NTE]"""
import collections, importlib, json, math, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
cls, mod = sys.argv[1].split("=")
C = getattr(importlib.import_module(mod), cls)
P = {p["id"]: p for p in map(json.loads, open(sys.argv[2]))}
tag, arms = sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "NTE"
RES = os.path.join(ROOT, "results", "tc")


def pub(env):
    return {k: v for k, v in vars(env).items() if not k.startswith("_")}


def run(env, calls):
    out = []
    for c in calls:
        try:
            out.append(eval("env." + c, {"env": env}))
        except Exception as e:
            out.append({"error": f"{type(e).__name__}"})
    return out


def rows(a):
    R = {}
    for l in open(f"{RES}/mt_{tag}_{a}_s1.jsonl", errors="replace"):
        try:
            r = json.loads(l)
        except json.JSONDecodeError:
            continue
        R[r["id"]] = r
    return R


R = {a: rows(a) for a in arms}
G = {a: json.load(open(f"{RES}/mt_grades_{tag}_{a}_s1.json")) for a in arms}
ids = sorted(i for i in P if all(i in G[a] for a in arms))
ok = {a: [int(G[a][i]["ok"]) for i in ids] for a in arms}
kt = {a: [R[a][i]["tok"] / 1000 for i in ids] for a in arms}
n = len(ids)
for a in arms:
    print(f"{tag} {a}: {sum(ok[a])} / {n} right ({100 * sum(ok[a]) / n:.1f}%) @ {sum(kt[a]) / n:.2f}k; utility "
          f"{sum(100 * o - 0.5 * k for o, k in zip(ok[a], kt[a])) / n:+.2f}")


def ci(d):
    m = sum(d) / len(d); sd = math.sqrt(sum((x - m) ** 2 for x in d) / (len(d) - 1)) if len(d) > 1 else 0
    return m, m - 1.96 * sd / math.sqrt(len(d)), m + 1.96 * sd / math.sqrt(len(d))


if "N" in arms and "T" in arms:
    m, lo, hi = ci([100 * (t - b) for t, b in zip(ok["T"], ok["N"])])
    print(f"T - N right: {m:+.1f} [{lo:+.1f}, {hi:+.1f}] points")
    m, lo, hi = ci([100 * (t - b) - 0.5 * (x - y) for t, b, x, y in zip(ok["T"], ok["N"], kt["T"], kt["N"])])
    print(f"T - N utility: {m:+.2f} [{lo:+.2f}, {hi:+.2f}]")
for a in arms:
    fail = [i for i in ids if not G[a][i]["ok"]]
    vis = lambda r: r["force_quit"] or any(any(z.get("err") or []) or z.get("loop") for t in r["turns"] for z in t)
    silent = [i for i in fail if not vis(R[a][i])]
    first, diff, fsil, turnok = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
    for i in fail:
        p, r = P[i], R[a][i]
        x, g = C(), C(); x._load_scenario(p["initial_config"][cls]); g._load_scenario(p["initial_config"][cls])
        for ti, gt in enumerate(p["ground_truth"]):
            t = r["turns"][ti] if ti < len(r["turns"]) else []
            run(x, [c for z in t for c in z["calls"]]); run(g, gt)
            same = pub(x) == pub(g)
            turnok[(p["kinds"][ti], same)] += 1
            if not same:
                k = p["kinds"][ti]; first[k] += 1
                diff[(k, ",".join(sorted(kk for kk in pub(x) if pub(x)[kk] != pub(g)[kk])))] += 1
                fsil[(k, not any(any(z.get("err") or []) or z.get("loop") for z in t))] += 1
                break
        else:
            first["(state equal; results or force-quit)"] += 1
    sf = sum(v for (k, s), v in fsil.items() if s); nd = sum(fsil.values())
    print(f"{a}: failures {len(fail)}; silent (whole conversation) {len(silent)} = {100 * len(silent) / max(1, len(fail)):.1f}%; "
          f"first diverging turn silent {sf} / {nd} = {100 * sf / max(1, nd):.1f}%")
    print("   first diverging turn by kind", dict(first))
    print("   attributes that differ there", dict(diff))
    print("   silent there, by kind", dict(fsil))
    print("   turns matched / not until the divergence", dict(sorted(turnok.items())))
