"""PROOF phase 3a (docs/prereg/PREREG_PROOF.md): an LLM proposes one auxiliary construction for an olympiad geometry problem written in
AlphaGeometry's language; AlphaGeometry's symbolic engine (DD+AR) then tries to prove the goal (checked by poc/geoproof_ddar_aux.py; AlphaGeometry in $POC_DATA/ag).
usage: POC_BASE_URL=... python geoproof_gen.py <tag> <k> [--think] [--max_tokens N] [--defs]  -> results/geoproof/aux_<tag>.jsonl
Only problems DD+AR cannot prove alone (results/geoproof/ddar_imo30.log) are attempted."""
import json, os, re, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat  # noqa: E402
_DATA = os.environ.get("POC_DATA", "/NAS/SJ/POSTECH/nlp_data")   # Slurm server (2026-10-22): external data; old server: /SSD/lean_postech

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AG = _DATA + "/ag/alphageometry"
OUT = f"{ROOT}/results/geoproof"
DEFS = [blk.split("\n")[0].strip() for blk in open(f"{AG}/defs.txt").read().split("\n\n") if blk.strip()]
CONSTR = [d for d in DEFS if d.split()[1:2] == ["x"]]   # constructions that create one new point x
# --defs (phase 3b, the "fact"): what each construction requires and what it gives, from the engine's own defs.txt
_BLK = {blk.split("\n")[0].strip(): blk.split("\n") for blk in open(f"{AG}/defs.txt").read().split("\n\n") if blk.strip()}
DEFS_TXT = ("Meaning of each construction (requires = conditions on the given points; gives = facts about x). Predicates: coll = collinear, "
            "perp a b c d = ab ⊥ cd, para = parallel, cong a b c d = |ab| = |cd|, cyclic = concyclic, eqangle = equal angles, "
            "ncoll / npara / diff = not collinear / not parallel / distinct.\n" +
            "\n".join(f"{c}: requires [{_BLK[c][2].split('=', 1)[1].strip() if '=' in _BLK[c][2] else ''}]; gives [{_BLK[c][3].split(':', 1)[1].strip()}]"
                      for c in CONSTR if c in _BLK and len(_BLK[c]) > 3))
PROMPT = """This is an olympiad geometry problem written in AlphaGeometry's construction language. Each clause `p = c p args` builds point p
with construction c from earlier points; several constructions for the same point are separated by commas; the goal follows `?`.

Problem: {prob}

A symbolic prover (deduction + algebraic reasoning) could not prove the goal from these points alone. Propose ONE auxiliary point that
would make the proof possible (for example a midpoint, a foot of a perpendicular, a circle centre or an intersection that the human proof
uses). Write it as a single clause with a new point name that is not used yet, using only these constructions (x is the new point):
{constr}

Answer with the clause only, on the last line, for example: `x = midpoint x a b`"""


SET = os.environ.get("GEO_SET", "imo30")   # imo30 = IMO-AG-30; jgex = JGEX-AG-231 (2026-10-18)


def problems():
    src, log = {"imo30": ("imo_ag_30.txt", "ddar_imo30.log"), "jgex": ("jgex_ag_231.txt", "ddar_jgex231.log")}[SET]
    txt = open(f"{AG}/{src}").read().strip().split("\n")
    P = dict(zip(txt[0::2], txt[1::2]))
    solved = {l.split()[0] for l in open(f"{OUT}/{log}") if " solved " in f" {l} " and "not solved" not in l}
    return {n: p for n, p in P.items() if n not in solved}


def clause(text):
    lines = [l.strip().strip("`").strip() for l in (text or "").strip().splitlines() if "=" in l]
    return lines[-1] if lines else None


if __name__ == "__main__":
    tag, k = sys.argv[1], int(sys.argv[2])
    mt = int(sys.argv[sys.argv.index("--max_tokens") + 1]) if "--max_tokens" in sys.argv else 8192
    P = problems()
    os.makedirs(OUT, exist_ok=True)
    path = f"{OUT}/aux_{tag}.jsonl"
    done = set()
    for l in (open(path, errors="replace") if os.path.exists(path) else []):
        try:
            r = json.loads(l); done.add((r["name"], r["sample"]))
        except ValueError:
            pass
    jobs = [(n, s) for n in P for s in range(1, k + 1) if (n, s) not in done]

    def one(j):
        n, s = j
        constr = DEFS_TXT if "--defs" in sys.argv else "\n".join(CONSTR)
        o = chat(PROMPT.format(prob=P[n], constr=constr), think="--think" in sys.argv, max_tokens=mt, temperature=0.7,
                 seed=s * 1000 + zlib.crc32(n.encode()) % 997)
        return {"name": n, "sample": s, "problem": P[n], "aux": clause(o["text"]), "text": (o["text"] or "")[-1500:],
                "out_tokens": o.get("out_tokens"), "finish": o.get("finish")}
    with ThreadPoolExecutor(32) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, j) for j in jobs]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    print(tag, "proposals", sum(1 for _ in open(path)), "for", len(P), "problems", flush=True)
