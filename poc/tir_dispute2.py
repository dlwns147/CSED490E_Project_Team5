"""DISPUTE-E with log-probabilities (tir_dispute2, 2026-11-26 18:5x UTC; tir_dispute.py is in use by running rows): the attempts are LPSessions, each attempt stores its confidence summary (poc/lp_session.py), and the arms add DeepConf-style selection (CONF-LOW: lowest group confidence, CONF-TAIL, CONF-MEAN; 2508.15260) on the same disagreements.
DISPUTE-E (PREREG_DIFF, 2026-11-26): DIFF's rule carried to native-tool attempts on Project Euler. Two attempts (tir_native's harness, unchanged);
where their answers differ, a referee session picks a smaller instance of the problem and computes it by brute force, each attempt's own session
is asked for that instance with its own method, and the attempt that matches the brute force is kept. The S*-style control on the same pairs (JUDGE:
a fresh session is shown both answers and picks one) is run on the same disagreements, so 'compute the disputed value' and 'choose between shown
values' are compared on the same samples. PROV2, ONE and the two-attempt oracle are read from the same two attempts.
usage: POC_BASE_URL=... python tir_dispute.py run <euler|eulert> <effort> <seedA> <seedB> -> results/x44/tirdis_<set>_<effort>_s<A>_<B>.jsonl
       python tir_dispute.py score <seedA> <seedB>
Temporary files: every session's Tool is closed in a finally block (removes its /tmp/sbx_tir_* sandbox)."""
import json, os, re, sys, zlib, itertools
from fractions import Fraction
from concurrent.futures import ThreadPoolExecutor, as_completed
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import tir_native as T
from lp_session import LPSession
R = T.R
CONT_CAP = 8000
REF = ("{p}\n\nDo not solve this problem. Instead choose a smaller instance of it: the same question with its numeric parameters reduced, as large as possible "
       "while a direct brute-force computation (plain enumeration of the definition, no formula, no clever method) finishes within about 20 seconds in the python tool, "
       "and different from every example whose value the statement already gives. Compute that instance's answer by brute force. "
       "In the final answer write one line 'INSTANCE: <the reduced parameters, e.g. N = 1000>' and then the brute-force value alone in \\boxed{{}}.")
CONT = ("Now apply your solution method to a smaller instance of the same problem: {inst}. Use the same program or formula that produced your answer above, "
        "with only the parameters changed; do not switch to a different method. Give the value for this instance alone in \\boxed{{}}.")
JUDGE = ("{p}\n\nTwo candidate final answers have been proposed: {x} and {y}. Determine which of them is correct; you may use the python tool. "
         "Put the one you judge correct, exactly as written, in \\boxed{{}}.")


def num(a):
    """value of an answer string as (Fraction, exact) or None (a give-up text is no answer): integers, decimals, a/b, \\frac{a}{b}, a\\times10^{k}, a e k (pilot 11-26: the referee and the sessions wrote one value three ways)"""
    if not a:
        return None
    s = re.sub(r"\\[,;! ]|\\left|\\right|\s|\{,\}|,", "", a); s = re.sub(r"\\[dt]?frac\{(-?\d+)\}\{(\d+)\}", r"\1/\2", s)
    s = s.replace("\\times", "*").replace("\\cdot", "*").replace("{", "").replace("}", "").rstrip(".")
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)(?:\*10\^(-?\d+)|[eE]\+?(-?\d+))?", s)
    if m:
        e = int(m.group(2) or m.group(3) or 0); return Fraction(m.group(1)) * Fraction(10) ** e, "." not in m.group(1) and e >= 0
    m = re.fullmatch(r"(-?\d+)/(\d+)", s)
    return (Fraction(int(m.group(1)), int(m.group(2))), True) if m and int(m.group(2)) else None


def eq(a, b):
    x, y = num(a), num(b)
    if x is None or y is None:
        return False
    if x[1] and y[1]:
        return x[0] == y[0]
    return abs(x[0] - y[0]) <= Fraction(1, 10 ** 9) * max(abs(x[0]), abs(y[0]), 1)


def _final(text):
    return text.split("<|channel|>final<|message|>")[-1].split("<|return|>")[0] if "<|channel|>final<|message|>" in text else ""


class Session:
    """one native-tool conversation that can be continued with a user turn after its final answer"""
    def __init__(self, q, effort, seed, tok):
        self.tok = tok; self.ids = tok(T.SYS.format(e=effort, q=q)); self.seed = seed; self.tool = T.Tool()
        self.used = self.calls = self.prefill = self.tooltok = 0; self.codes = []; self.outs = []; self.g = []; self.fin = "stop"; self.text = ""; self.turn = 0

    def gen(self, budget):
        import llm
        start = self.used
        while True:
            room = min(budget - (self.used - start), int(os.environ.get("TIR_CTX", 64000)) - len(self.ids) - 8)
            if room < 16:
                self.fin = "length"; return ""
            r = llm.client.completions.create(model="local", prompt=self.ids, temperature=1.0, top_p=0.95, max_tokens=room, seed=self.seed + self.calls + 7919 * self.turn,
                                              extra_body={"return_token_ids": True, "skip_special_tokens": False, "stop_token_ids": [T.CALL, T.RET]})
            self.prefill += len(self.ids); c = r.choices[0]; g = list(c.token_ids); self.used += r.usage.completion_tokens; self.text = c.text or ""; self.fin = c.finish_reason
            if self.fin == "length":
                return ""
            if T.CALL in (g[-1] if g else None, c.stop_reason):
                if g[-1] != T.CALL:
                    g.append(T.CALL)
                m = self.text.split("<|call|>")[0].split("<|message|>"); head, code = m[-2].split("<|start|>")[-1] if len(m) > 1 else "", m[-1]
                self.calls += 1
                if self.calls > T.MAXCALLS:
                    self.fin = "calls"; return ""
                o = self.tool.run(code) if "python" in head else "Unknown tool. Only python is available."
                self.codes.append(code); self.outs.append(o)
                oi = self.tok(o); self.tooltok += len(oi); self.ids = self.ids + g + self.tok("<|start|>python to=assistant<|channel|>analysis<|message|>") + oi + self.tok("<|end|><|start|>assistant")
                continue
            self.g = g
            return _final(self.text)

    def ask(self, msg, budget):
        g = self.g[:-1] if self.g and self.g[-1] == T.RET else self.g
        self.ids = self.ids + g + self.tok("<|end|><|start|>user<|message|>" + msg + "<|end|><|start|>assistant"); self.turn += 1
        return self.gen(budget)

    def close(self):
        self.tool.close()


def solve(p, prompt, grade, effort, sa, sb):
    import llm
    import ma_effort as M
    import run_compute as RC
    tok = lambda s: llm.post_json("/tokenize", {"model": "local", "prompt": s, "add_special_tokens": False})["tokens"]
    nm = lambda t: (lambda a: a if num(a) is not None else "")(RC.norm(M.ans(t) or "")) if t else ""
    h = zlib.crc32(p["id"].encode()) % 997; q = prompt(p)
    S = {"A": LPSession(q, effort, sa * 1000 + h, tok), "B": LPSession(q, effort, sb * 1000 + h, tok)}; out = {"id": p["id"]}
    try:
        with ThreadPoolExecutor(2) as ex:
            F = {k: ex.submit(s.gen, T.CAP) for k, s in S.items()}; fin = {k: f.result() for k, f in F.items()}
        for k, s in S.items():
            z = {"final": fin[k], "outs": s.outs}; pv = T.provenance(z) if fin[k] else None
            out[k] = {"final": fin[k][-2000:], "ans": nm(fin[k]), "out_tokens": s.used, "calls": s.calls, "finish": s.fin, "flag": (not pv) or s.fin != "stop", "lp": s.summary(), **grade(p, fin[k])}
        a, b = out["A"]["ans"], out["B"]["ans"]
        out["disputed"] = bool(a and b and not eq(a, b))
        if out["disputed"]:
            ref = Session(REF.format(p=p["problem"]), effort, 10 * 1000 + h, tok); jud = Session(JUDGE.format(p=p["problem"], x=a, y=b), effort, 11 * 1000 + h, tok)
            try:
                with ThreadPoolExecutor(2) as ex:
                    fr, fj = ex.submit(ref.gen, T.CAP), ex.submit(jud.gen, T.CAP); rf, jf = fr.result(), fj.result()
                inst = next((l.split("INSTANCE:", 1)[1].strip() for l in rf.splitlines() if "INSTANCE:" in l), "")[:300]; inst = re.sub(r"\\[()]", "", inst).strip(" *")
                out["ref"] = {"final": rf[-1500:], "inst": inst, "ans": nm(rf), "out_tokens": ref.used, "calls": ref.calls, "finish": ref.fin}
                out["judge"] = {"final": jf[-1500:], "ans": nm(jf), "out_tokens": jud.used, "calls": jud.calls, "finish": jud.fin}
                if inst and out["ref"]["ans"]:
                    with ThreadPoolExecutor(2) as ex:
                        F = {k: ex.submit(s.ask, CONT.format(inst=inst), CONT_CAP) for k, s in S.items()}
                        for k, f in F.items():
                            r = f.result()
                            out[k]["small"] = {"final": r[-1500:], "ans": nm(r), "out_tokens": S[k].used - out[k]["out_tokens"], "finish": S[k].fin}
            finally:
                ref.close(); jud.close()
    finally:
        for s in S.values():
            s.close()
    return out


def main(st, effort, sa, sb):
    P, prompt, grade = T.task(st); path = f"{R}/tirdis2_{st}_{effort}_s{sa}_{sb}.jsonl"
    done = {json.loads(l)["id"] for l in open(path)} if os.path.exists(path) else set()

    def one(p):
        try:
            return solve(p, prompt, grade, effort, sa, sb)
        except Exception as e:
            return {"id": p["id"], "error": repr(e)[:300]}
    N = int(os.environ.get("TIR_N", 0)) or len(P)
    with ThreadPoolExecutor(int(os.environ.get("TIR_WORKERS", 16))) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, p) for p in P[:N] if p["id"] not in done]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    Z = [json.loads(l) for l in open(path)]; ok = [z for z in Z if "error" not in z]
    print(f"DISPUTE {st} {effort} s{sa}/{sb}: {len(Z)} rows, errors {len(Z)-len(ok)}, disputed {sum(z['disputed'] for z in ok)}, "
          f"referee with instance+answer {sum(bool(z.get('ref', {}).get('inst') and z['ref'].get('ans')) for z in ok)}", flush=True)


def arms(z):
    """-> {arm: [(correct, tokens) for each order of the two attempts]}; the order decides the fallback (first attempt) and which one PROV2 buys second"""
    c = lambda r: float(bool(r.get("correct"))); t = lambda r: r["out_tokens"]; res = {k: [] for k in ("ONE", "PROV2", "ORACLE2", "JUDGE", "DISPUTE", "DISPUTE-P", "CONF-LOW", "CONF-TAIL", "CONF-MEAN")}
    for x, y in (("A", "B"), ("B", "A")):
        X, Y = z[x], z[y]; both = t(X) + t(Y)
        res["ONE"].append((c(X), t(X)))
        res["PROV2"].append(((c(Y) if not Y["flag"] else c(X)) if X["flag"] else c(X), both if X["flag"] else t(X)))
        res["ORACLE2"].append((max(c(X), c(Y)), both))
        if not z["disputed"]:
            pick = X if X["ans"] else Y
            for k in ("JUDGE", "DISPUTE"):
                res[k].append((c(pick), both))
            res["DISPUTE-P"].append(((c(pick) if X["flag"] else c(X)), both if X["flag"] else t(X)))
            for k in ("CONF-LOW", "CONF-TAIL", "CONF-MEAN"):
                res[k].append((c(pick), both))
            continue
        for k, f in (("CONF-LOW", "lowest_group_conf"), ("CONF-TAIL", "tail_conf"), ("CONF-MEAN", "mean_conf")):
            cx, cy = (X.get("lp") or {}).get(f), (Y.get("lp") or {}).get(f)
            res[k].append((c(Y) if (cx is not None and cy is not None and cy > cx) else c(X), both))
        j = z.get("judge", {}); jt = j.get("out_tokens", 0)
        res["JUDGE"].append((c(Y) if eq(j.get("ans"), Y["ans"]) and not eq(j.get("ans"), X["ans"]) else c(X), both + jt))
        rf = z.get("ref", {}); r = rf.get("ans"); dt = rf.get("out_tokens", 0) + sum(z[k].get("small", {}).get("out_tokens", 0) for k in ("A", "B"))
        mx, my = eq(X.get("small", {}).get("ans"), r), eq(Y.get("small", {}).get("ans"), r)
        d = c(Y) if (my and not mx) else c(X)
        res["DISPUTE"].append((d, both + dt))
        res["DISPUTE-P"].append(((d, both + dt) if X["flag"] else (c(X), t(X))))
    return res


def score(sa, sb):
    import tir_score as S
    U = S.U; A = {}
    for st in ("euler", "eulert"):
        p = f"{R}/{os.environ.get('DIS_PREFIX', 'tirdis2')}_{st}_medium_s{sa}_{sb}.jsonl"
        if not os.path.exists(p):
            continue
        seen = set()
        for l in open(p):
            z = json.loads(l)
            if "error" in z or z["id"] in seen:
                continue
            seen.add(z["id"])
            for k, v in arms(z).items():
                A.setdefault(k, {})[(st, z["id"])] = (sum(a for a, _ in v) / len(v), sum(t for _, t in v) / len(v))
            A.setdefault("_d", {})[(st, z["id"])] = z
    D = A.pop("_d")
    for lab, sts in (("euler", ("euler",)), ("eulert", ("eulert",)), ("pooled", ("euler", "eulert"))):
        ks = [k for k in A["ONE"] if k[0] in sts]
        if not ks:
            continue
        dz = [D[k] for k in ks if D[k]["disputed"]]
        print(f"== {lab}: {len(ks)} problems, disputed {len(dz)}; referee gave instance + value on {sum(bool(z.get('ref', {}).get('inst') and z['ref'].get('ans')) for z in dz)}; "
              f"exactly one attempt matches it on {sum(eq(z['A'].get('small', {}).get('ans'), z.get('ref', {}).get('ans')) != eq(z['B'].get('small', {}).get('ans'), z.get('ref', {}).get('ans')) for z in dz)}")
        for a in A:
            print(f"   {a:9s} {100*sum(A[a][k][0] for k in ks)/len(ks):.1f}% @ {sum(A[a][k][1] for k in ks)/len(ks)/1000:.2f}k utility {sum(U(*A[a][k]) for k in ks)/len(ks):.2f}")
        one = sum(A['ONE'][k][0] for k in ks); orc = sum(A['ORACLE2'][k][0] for k in ks)
        for a in ("PROV2", "JUDGE", "DISPUTE", "DISPUTE-P", "CONF-LOW", "CONF-TAIL", "CONF-MEAN"):
            print(f"   share of the two-attempt room captured by {a}: {(sum(A[a][k][0] for k in ks)-one)/max(1e-9, orc-one):.2f}")
        for a, b in (("DISPUTE", "JUDGE"), ("DISPUTE", "ONE"), ("DISPUTE", "PROV2"), ("JUDGE", "ONE"), ("DISPUTE-P", "PROV2"), ("DISPUTE-P", "ONE"), ("DISPUTE", "CONF-LOW"), ("DISPUTE", "CONF-TAIL")):
            print(f"   {a} − {b}: accuracy {S.ci([100*(A[a][k][0]-A[b][k][0]) for k in ks])} ktok {S.ci([(A[a][k][1]-A[b][k][1])/1000 for k in ks])} utility {S.ci([U(*A[a][k])-U(*A[b][k]) for k in ks])}")


if __name__ == "__main__":
    if sys.argv[1] == "score":
        score(int(sys.argv[2]), int(sys.argv[3]))
    else:
        main(sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]))
