"""PREREG_DIFF addendum OEIS-E (2026-11-23): DIFF v2, and where the referee's term matches no candidate class, the thinking program
(gpt-oss-120b medium, think mode, seed 2) replaces DIFF's answer; its tokens are paid only there. usage: python oeis_escalate.py [orig|fresh]"""
import json, os, random, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = f"{ROOT}/results/x44"


def main(kind):
    pfx = "oeisf" if kind == "fresh" else "oeis"
    D = {json.loads(l)["id"]: json.loads(l) for l in open(f"{R}/{pfx}_diff_cheap_split.jsonl")}
    T = {json.loads(l)["id"]: json.loads(l) for l in open(f"{R}/{pfx}_oss120M_think_s2.jsonl")}
    U = lambda ok, t: 100 * ok - 0.5 * t / 1000
    base, new, flag = {}, {}, 0
    for i, d in D.items():
        t = d["pool_tok"] + d["oracle_tok"]; base[i] = U(d["right"], t)
        if any(x["kept"] == 0 and x["oracle"] is not None for x in d["rounds"]) and i in T:
            flag += 1; r = T[i]
            new[i] = U(str(r.get("correct")) == "True", t + int(r.get("out_tokens") or 0))
        else:
            new[i] = base[i]
    ids = sorted(D); d = {i: new[i] - base[i] for i in ids}; rng = random.Random(1); B = 4000
    bs = sorted(sum(d[rng.choice(ids)] for _ in ids) / len(ids) for _ in range(B))
    th = [T[i] for i in ids if i in T]
    print(f"{kind}: thinking program alone {100*sum(str(r.get('correct'))=='True' for r in th)/max(1,len(th)):.1f}% ({len(th)} rows); "
          f"flagged {flag}; DIFF U {sum(base.values())/len(ids):.2f} -> +E U {sum(new.values())/len(ids):.2f}, "
          f"diff {sum(d.values())/len(ids):+.2f} [{bs[100]:+.2f}, {bs[3899]:+.2f}] p={(sum(x <= 0 for x in bs)+1)/(B+1):.4f}")


def think_vs_diff(kind, seed):
    """addendum OEIS-T: one thinking program (gpt-oss-120b medium, seed) alone vs DIFF v2, utility, paired"""
    pfx = "oeisf" if kind == "fresh" else "oeis"
    D = {json.loads(l)["id"]: json.loads(l) for l in open(f"{R}/{pfx}_diff_cheap_split.jsonl")}
    T = {json.loads(l)["id"]: json.loads(l) for l in open(f"{R}/{pfx}_oss120M_think_s{seed}.jsonl")}
    U = lambda ok, t: 100 * ok - 0.5 * t / 1000
    ids = sorted(i for i in D if i in T)
    d = {i: U(str(T[i].get("correct")) == "True", int(T[i].get("out_tokens") or 0)) - U(D[i]["right"], D[i]["pool_tok"] + D[i]["oracle_tok"]) for i in ids}
    rng = random.Random(1); B = 4000
    bs = sorted(sum(d[rng.choice(ids)] for _ in ids) / len(ids) for _ in range(B))
    acc = sum(str(T[i].get("correct")) == "True" for i in ids) / len(ids)
    print(f"{kind} seed {seed}: think alone {100*acc:.1f}% ({sum(int(T[i].get('out_tokens') or 0) for i in ids)/len(ids):.0f} tok) vs DIFF "
          f"{100*sum(D[i]['right'] for i in ids)/len(ids):.1f}%; think - DIFF {sum(d.values())/len(ids):+.2f} [{bs[100]:+.2f}, {bs[3899]:+.2f}] n={len(ids)}")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "think":
        think_vs_diff(sys.argv[2], int(sys.argv[3]))
    else:
        main(sys.argv[1] if len(sys.argv) > 1 else "fresh")
