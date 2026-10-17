"""S6 k-curve: MR-select accuracy over the first k tool-free samples (k = 1..5), per model."""
import itertools, json, os, random, subprocess, sys
RES = "/NAS/SJ/POSTECH/nlp/results"
for m in ["1_7b", "8b", "14b", "32b"]:
    seeds = [s for s in range(1, 6) if os.path.exists(f"{RES}/geocross_geox{m}_base_t07s{s}.jsonl")]
    out = []
    for k in range(1, len(seeds) + 1):
        arms = ",".join(f"base@{s}" for s in seeds[:k])
        r = subprocess.run([sys.executable, "/NAS/SJ/POSTECH/nlp/poc/mr_select.py", m, str(seeds[0]), arms], capture_output=True, text=True)
        line = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:]
        sel = line.split("MR-select ")[1].split("/")[0] if "MR-select" in line else "?"
        single = line.split("per-arm ")[1].split(" |")[0] if "per-arm" in line else "?"
        out.append(f"k={k}: {sel}")
    print(m, "singles", single, "|", " ".join(out))
