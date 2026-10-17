"""N18 (results/PREREG_N.md): token log-probs of Qwen3.6 contest programs (cc_full_q36_lp_s1-3). Among programs that pass the
statement's examples: AUROC of mean / min / 5%-quantile log-prob over the code tokens for correct vs wrong; selection among the 3
seeds' example-passers by the highest mean log-prob vs the first example-passer; what kind of token the 20 least confident code
tokens of each program are. usage: CC_SET=full python analyze_n18.py"""
import bisect, collections, itertools, json, os, statistics as st, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("CC_SET", "full")
from run_cc import PFILE, RES  # noqa: E402

P = {p["name"]: p for p in json.load(open(PFILE))}
NPUB = {n: sum(t["kind"] == "public" for t in p["tests"]) for n, p in P.items()}
passes = lambda r: bool(r["code"]) and r["passed"] >= NPUB[r["name"]]
KW = {"if", "elif", "else", "for", "while", "return", "break", "continue", "and", "or", "not", "in", "def", "import", "from", "range"}


def code_lps(r):
    toks, lps = r.get("lp_tok") or [], r.get("lp") or []
    if not toks or not r.get("code"):
        return [], []
    joined = "".join(toks); a = joined.rfind(r["code"][:120])
    if a < 0:
        return [], []
    b = a + len(r["code"]); st_ = list(itertools.accumulate([0] + [len(t) for t in toks]))
    idx = [i for i in range(len(toks)) if st_[i] >= a and st_[i + 1] <= b]
    com, pos = [], 0   # comment spans of the code (from '#' to the end of the line; '#' inside strings is rare here)
    for line in r["code"].split("\n"):
        j = line.find("#")
        if j >= 0:
            com.append((pos + j, pos + len(line)))
        pos += len(line) + 1
    inc = lambda o: any(x <= o < y for x, y in com)
    return [lps[i] for i in idx], [("#" if inc(st_[i] - a) else "") + toks[i] for i in idx]


def kind(t):
    if t.startswith("#"):
        return "comment"
    s = t.strip()
    if not s:
        return "whitespace"
    if any(c.isdigit() for c in s) and all(c.isdigit() or c in "._eE-+" for c in s):
        return "number"
    if s in KW:
        return "keyword"
    if all(c in "+-*/%<>=!&|^~()[]{}:,." for c in s):
        return "operator / bracket"
    return "identifier / other"


def auroc(neg, pos):   # P(neg < pos)
    if not neg or not pos:
        return float("nan")
    p = sorted(pos); n = 0.0
    for x in neg:
        lo, hi = bisect.bisect_left(p, x), bisect.bisect_right(p, x); n += (len(p) - hi) + 0.5 * (hi - lo)
    return n / (len(neg) * len(p))


S = {sd: {r["name"]: r for r in map(json.loads, open(f"{RES}/cc_full_q36_lp_s{sd}.jsonl"))} for sd in (1, 2, 3)}
feat = {}
for sd in S:
    for n, r in S[sd].items():
        l, t = code_lps(r)
        if l:
            ls = sorted(l)
            feat[(sd, n)] = {"mean": st.mean(l), "min": ls[0], "q5": ls[max(0, int(0.05 * len(ls)) - 1)], "n": len(l),
                             "low_kinds": collections.Counter(kind(t[i]) for i in sorted(range(len(l)), key=lambda i: l[i])[:20])}
rows = [r for sd in S for r in S[sd].values()]
print(f"Qwen3.6 contest with log-probs: {100 * sum(r['passed_all'] for r in rows) / len(rows):.1f}% correct, {len(feat)} / {len(rows)} programs "
      f"with code log-probs, tokens {st.mean(r['out_tokens'] or 0 for r in rows) / 1000:.1f}k, caps {sum(r.get('finish') == 'length' for r in rows)}")
ep = [(sd, n) for (sd, n) in feat if passes(S[sd][n])]
good = [k for k in ep if S[k[0]][k[1]]["passed_all"]]; bad = [k for k in ep if not S[k[0]][k[1]]["passed_all"]]
print(f"example-passers: {len(ep)} ({len(good)} correct, {len(bad)} wrong)")
for f in ("mean", "min", "q5"):
    print(f"  {f:4s} log-prob: median correct {st.median(feat[k][f] for k in good):.3f} / wrong {st.median(feat[k][f] for k in bad):.3f}; "
          f"AUROC (wrong lower) {auroc([feat[k][f] for k in bad], [feat[k][f] for k in good]):.3f}")
# also all programs (passing or not): does confidence predict passing the examples?
allk = list(feat); pe = [k for k in allk if passes(S[k[0]][k[1]])]; fe = [k for k in allk if not passes(S[k[0]][k[1]])]
print(f"  all programs, mean log-prob, fails-examples lower: AUROC {auroc([feat[k]['mean'] for k in fe], [feat[k]['mean'] for k in pe]):.3f}")
# selection among the 3 seeds
first = conf = orc = 0
for n in S[1]:
    cands = [(sd, n) for sd in (1, 2, 3) if (sd, n) in feat and passes(S[sd][n])]
    if not cands:
        first += S[1][n]["passed_all"]; conf += S[1][n]["passed_all"]; continue
    first += S[cands[0][0]][n]["passed_all"]
    best = max(cands, key=lambda k: feat[k]["mean"]); conf += S[best[0]][n]["passed_all"]
    orc += any(S[sd][n]["passed_all"] for sd, _ in cands)
N = len(S[1])
print(f"selection over 3 seeds: first example-passer {100 * first / N:.1f}% | highest mean log-prob example-passer {100 * conf / N:.1f}% | any correct example-passer {100 * orc / N:.1f}%")
kc, kb = collections.Counter(), collections.Counter()
for k in good:
    kc.update(feat[k]["low_kinds"])
for k in bad:
    kb.update(feat[k]["low_kinds"])
tc, tb = sum(kc.values()), sum(kb.values())
print("kinds of the 20 least confident code tokens (share): " + ", ".join(f"{x}: correct {100 * kc[x] / tc:.0f}% / wrong {100 * kb[x] / tb:.0f}%" for x in sorted(set(kc) | set(kb))))
