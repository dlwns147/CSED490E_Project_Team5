"""EUL-S scorer (PREREG_DIFF, 2026-11-28): S0 (answer submitted as a session value) vs the native tool (tir_euler(t)_mediumNE), Project Euler 170
problems (euler 120 dev + eulert 50 fresh), seeds 1-2 averaged per problem, corrected reader (ma_effort.ans + RC.norm) on every final, clustered
bootstrap by problem. Also: literal-constant submissions (submit(<number>) typed, never computed) and their precision, unsubmitted attempts,
tokens, calls; dev / fresh apart. usage: python eul_s_score.py"""
import ast, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tir_score as S
import ma_effort as M
import run_compute as RC
R = S.R; U = S.U; SEEDS = tuple(int(x) for x in os.environ.get("ESEEDS", "1,2").split(","))   # EUL-SC: ESEEDS=3,4; COMP-S: ESETS=comp ESEEDS=2,3
SETS = os.environ.get("ESETS", "euler,eulert").split(",")


def load(path, gold):
    out = {}
    for l in open(path):
        z = json.loads(l)
        if z["id"] in out:
            continue
        a = M.ans(z.get("final") or "") or ""; z["correct"] = bool(a) and RC.norm(a) == RC.norm(gold[z["id"]]); out[z["id"]] = z
    return out


def literal(z):
    """True if the code cell that called submit passed a numeric literal (or a string of digits) rather than a computed name / expression"""
    for c in reversed(z.get("codes") or []):
        if "submit(" not in c:
            continue
        try:
            t = ast.parse(c)
        except SyntaxError:
            m = re.search(r"submit\(\s*['\"]?\s*-?[\d_,]+\s*['\"]?\s*\)", c); return bool(m)
        for n in ast.walk(t):
            if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "submit" and n.args:
                a = n.args[0]
                if isinstance(a, ast.Constant):
                    return True
                if isinstance(a, ast.Call) and getattr(a.func, "id", None) == "str" and a.args and isinstance(a.args[0], ast.Constant):
                    return True
                return False
    return None


arms = {"NE": {}, "S0": {}}; rows = {"NE": {}, "S0": {}}
for st in SETS:
    gold = {p["id"]: p["gold"].strip() for p in M.PROBS} if st == "comp" else {p["id"]: p["answer"] for p in RC.problems(st)}
    for s in SEEDS:
        for arm, f in (("NE", f"{R}/tir_{st}_mediumNE_s{s}.jsonl"), ("S0", f"{R}/tirsub3_S0_{st}_medium_s{s}.jsonl")):
            if os.path.exists(f):
                for k, z in load(f, gold).items():
                    rows[arm].setdefault((st, k), []).append(z)
for arm in arms:
    for k, zs in rows[arm].items():
        if len(zs) == len(SEEDS):
            arms[arm][k] = (sum(z["correct"] for z in zs) / len(zs), sum(int(z.get("out_tokens") or 0) for z in zs) / len(zs))
ks = sorted(set(arms["NE"]) & set(arms["S0"]))
print(f"EUL-S {SETS} seeds {SEEDS}: {len(ks)} problems with both seeds in both arms")
for sub, kk in (("all", ks), ("dev (euler)", [k for k in ks if k[0] == "euler"]), ("fresh (eulert)", [k for k in ks if k[0] == "eulert"])) if SETS != ["comp"] else (("comp", ks),):
    if not kk:
        continue
    key = [k[1] for k in kk]
    for a in arms:
        print(f"  {sub:15s} {a:3s} {100*sum(arms[a][k][0] for k in kk)/len(kk):5.1f}% @ {sum(arms[a][k][1] for k in kk)/len(kk)/1000:5.2f}k utility {sum(U(*arms[a][k]) for k in kk)/len(kk):6.2f}")
    print(f"  {sub:15s} S0 − NE utility {S.ci([U(*arms['S0'][k]) - U(*arms['NE'][k]) for k in kk], key)} accuracy {S.ci([100*(arms['S0'][k][0]-arms['NE'][k][0]) for k in kk], key)}")
Z = [z for k in ks for z in rows["S0"][k]]
lit = [z for z in Z if literal(z) is True]; comp = [z for z in Z if literal(z) is False]; uns = [z for z in Z if literal(z) is None]
print(f"S0 submissions: literal constant {len(lit)} (right {sum(z['correct'] for z in lit)}), computed {len(comp)} (right {sum(z['correct'] for z in comp)}), no submit call {len(uns)} (right {sum(z['correct'] for z in uns)}); finish {dict((f, sum(z.get('finish') == f for z in Z)) for f in set(z.get('finish') for z in Z))}")
N = [z for k in ks for z in rows["NE"][k]]
print(f"NE: no boxed answer {sum(not M.ans(z.get('final') or '') for z in N)} of {len(N)}; S0: {sum(not M.ans(z.get('final') or '') for z in Z)} of {len(Z)}; calls NE {sum(z.get('calls', 0) for z in N)/len(N):.1f} S0 {sum(z.get('calls', 0) for z in Z)/len(Z):.1f}")
