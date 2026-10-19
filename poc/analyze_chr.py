"""CH-R (docs/prereg/PREREG_CH.md): gpt-oss-20b, retry at medium with the free check instead of high effort, on fresh seeds 4-8.
Policy R_k(s): attempts s, s+1, ..., s+k-1 (cyclic within the seed block), accept the first that passes the examples and the problem's
brute-force oracle (N5; charged once when a passing program must be checked), else keep the last attempt. Also R_k with the examples only.
usage: CC_SET=full python analyze_chr.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("CC_SET", "full")
import analyze_ch as A  # noqa: E402

m, med = "oss20", "oss20_medium"
ORC, OTOK = A.oracle(m)
R = {s: A.rows(med, s) for s in range(1, 9)}
AG = A.agreement([(med, s, n, R[s][n]["code"]) for s in R for n in R[s] if n in ORC and A.passes(R[s][n])], ORC)


def pol(block, k, oracle=True):
    acc = tok = c = 0
    for i, s in enumerate(block):
        for n in A.V:
            seq = [block[(i + j) % len(block)] for j in range(k)]; t = 0; charged = False; res = None
            for sd in seq:
                r = R[sd][n]; t += A.tok(r)
                if oracle and A.passes(r) and not charged and n in ORC:
                    t += OTOK.get(n, 0); charged = True
                if A.passes(r) and (not oracle or AG.get((med, sd, n), True)):
                    res = r["passed_all"]; break
            acc += res if res is not None else R[seq[-1]][n]["passed_all"]; tok += t; c += 1
    return 100 * acc / c, tok / c / 1000


for name, block in (("seeds 1-3 (where it was found)", [1, 2, 3]), ("fresh seeds 4-6", [4, 5, 6]), ("fresh seeds 4-8", [4, 5, 6, 7, 8])):
    print(name + ": medium alone %.1f%% @ %.1fk" % pol(block, 1, oracle=False)[:2])
    for k in sorted({1, 2, 3, len(block)}):
        a, t = pol(block, k); ae, te = pol(block, k, oracle=False)
        print(f"  up to {k} attempts: check = examples + oracle {a:.1f}% @ {t:.1f}k | examples only {ae:.1f}% @ {te:.1f}k")
