"""TABLE (PREREG_DIFF, 2026-11-26): turn a Project Euler problem into a sequence. One native-tool session writes a direct brute force for the
problem's general form f(n) in one parameter n and stores the values for consecutive small n in table.json inside its sandbox; it states the
target n and the modulus the problem asks for. The table is the input of an extrapolation stage (classical guessing: recurrences, polynomials,
rational generating functions; poc/euler_guess.py), whose own held-out terms are the free check. Model tokens are charged; the extrapolation is CPU.
usage: POC_BASE_URL=... python euler_table.py run <euler|eulert> <effort> <seed> -> results/x44/eultab_<set>_<effort>_s<seed>.jsonl
Temporary files: the sandbox (with table.json) is removed by Session.close() after the table is read."""
import json, os, re, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import tir_native as T
from tir_dispute import Session
R = T.R
PROMPT = ("{p}\n\nDo not solve this problem. Instead turn it into a sequence. Choose the one numeric parameter of the problem whose value makes it large "
          "(for example N, the bound or the size) and call it n; f(n) is the answer of the same problem with that parameter equal to n and everything else unchanged. "
          "If the problem asks for a value modulo some number, f(n) is the exact value WITHOUT the modulus. Write a direct brute-force program for f(n) "
          "(plain enumeration of the definition, no formula and no clever method) and check it against every example value the statement gives. "
          "Then compute f(n) for n = 1, 2, 3, ... (or from the smallest n where the problem makes sense), as many consecutive values as finish within about 40 seconds, "
          "and save them with json.dump as a list of [n, f(n)] pairs (integers, or exact fractions as strings 'p/q') to the file table.json in the current directory. "
          "If the problem has no such parameter, write no file. In the final answer write exactly three lines:\n"
          "PARAMETER: <what n is>\nTARGET: <the value of n the problem asks for, or NONE>\nMODULUS: <the modulus the problem asks for, or NONE>")


def solve(p, prompt, effort, seed):
    import llm
    tok = lambda s: llm.post_json("/tokenize", {"model": "local", "prompt": s, "add_special_tokens": False})["tokens"]
    s = Session(PROMPT.format(p=p["problem"]), effort, seed, tok)
    try:
        fin = s.gen(T.CAP); tab = None; f = os.path.join(s.tool.d.name, "table.json")
        if os.path.exists(f) and os.path.getsize(f) < (8 << 20):
            try:
                tab = json.load(open(f))
            except Exception as e:
                tab = "unreadable " + repr(e)[:100]
        g = lambda k: (re.search(k + r":\s*(.+)", fin or "") or [None, ""])[1].strip()[:200]
        return {"id": p["id"], "final": (fin or "")[-1500:], "param": g("PARAMETER"), "target": g("TARGET"), "modulus": g("MODULUS"), "table": tab,
                "out_tokens": s.used, "calls": s.calls, "finish": s.fin}
    finally:
        s.close()


def main(st, effort, seed):
    P, prompt, grade = T.task(st); path = f"{R}/eultab_{st}_{effort}_s{seed}.jsonl"
    done = {json.loads(l)["id"] for l in open(path)} if os.path.exists(path) else set()

    def one(p):
        try:
            return solve(p, prompt, effort, seed * 1000 + zlib.crc32(p["id"].encode()) % 997)
        except Exception as e:
            return {"id": p["id"], "error": repr(e)[:300], "out_tokens": 0}
    N = int(os.environ.get("TIR_N", 0)) or len(P)
    with ThreadPoolExecutor(int(os.environ.get("TIR_WORKERS", 32))) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, p) for p in P[:N] if p["id"] not in done]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    Z = [json.loads(l) for l in open(path)]
    print(f"TABLE {st} {effort} s{seed}: {len(Z)} rows, errors {sum('error' in z for z in Z)}, with table {sum(isinstance(z.get('table'), list) for z in Z)}, "
          f"median length {sorted(len(z['table']) for z in Z if isinstance(z.get('table'), list))[len([1 for z in Z if isinstance(z.get('table'), list)])//2] if any(isinstance(z.get('table'), list) for z in Z) else 0}, "
          f"target given {sum(bool(z.get('target')) and z.get('target', '').upper() != 'NONE' for z in Z)}, tokens {sum(z['out_tokens'] for z in Z)/max(1,len(Z))/1000:.2f}k", flush=True)


if __name__ == "__main__":
    main(sys.argv[2], sys.argv[3], int(sys.argv[4]))
