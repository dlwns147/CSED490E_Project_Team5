"""E1 failure taxonomy over the stored programs (CPU only, re-runnable).

What it does
  1. Writes results/e1_manifest.json: the tags used, each mapped to (domain, model, condition, seed) and the run flags that matter for
     re-execution, taken from the queue scripts that launched them (field `source`). Lists the result files that were skipped.
  2. Geometry: every failing program (not correct on all 8 variants) gets ONE class, from its stored per-variant pattern plus a re-run of
     the stored code on the identity instance under a small exception-recording wrapper (exception type, message, traceback frames).
  3. Optimization: every non-optimal final program gets ONE class from its stored status plus a re-run on its instance (exception info,
     stdout), a lenient re-parse of stdout (output format), and for VRPTW the input-format counterfactual (service field removed).
  4. Fix transitions: for paired designs already stored (same instances, condition A -> condition B), the share of each A-failure class
     that is correct in B; label-free selection over 3 seeds (geometry: metamorphic check as poc/mr_select.py; CO: feasible + best
     objective) is evaluated the same way (before = seed-1 sample).
  5. Writes results/e1_taxonomy.json and prints every table. With --samples DIR it also writes 8 random programs per class (seed 0) for
     the manual validation.

usage: python poc/analyze_e1_taxonomy.py [--workers 16] [--co_workers 6] [--cache FILE] [--samples DIR]
Re-execution results are cached in --cache (default: <tmp>/e1_rerun_cache.jsonl); delete it to re-run everything (~15-25 min CPU).
"""
import argparse
import glob
import hashlib
import json
import os
import random
import re
import sys
import tempfile
import threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

POC = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(POC)
RES = os.path.join(ROOT, "results")
sys.path.insert(0, POC)
from geo_distractors import NEED as GNEED, toolbox  # noqa: E402
from run_co import describe, gen, objective  # noqa: E402
from run_geo import answer, base_instance, render, variants  # noqa: E402
from sandbox import run_python  # noqa: E402

# ----------------------------------------------------------------------------------------------------------------------------------
# 1. manifest
# ----------------------------------------------------------------------------------------------------------------------------------
QW = {"1_7b": "Qwen3-1.7B", "8b": "Qwen3-8B", "14b": "Qwen3-14B", "32b": "Qwen3-32B", "q8b": "Qwen3-8B", "q32b": "Qwen3-32B",
      "llama8": "Llama-3.1-8B", "l8": "Llama-3.1-8B", "llama70": "Llama-3.3-70B", "l70": "Llama-3.3-70B", "r1l70": "R1-Distill-Llama-70B"}
OSS = {"oss20low": ("gpt-oss-20b", "low"), "oss20med": ("gpt-oss-20b", "medium"), "oss20hig": ("gpt-oss-20b", "high"),
       "oss120low": ("gpt-oss-120b", "low"), "oss120med": ("gpt-oss-120b", "medium"), "oss120hig": ("gpt-oss-120b", "high")}
FAMILY = {"Qwen3": "Qwen3 (no think)", "Llama": "Llama", "R1-Distill": "reasoning (R1 / gpt-oss)", "gpt-oss": "reasoning (R1 / gpt-oss)"}
TASKSETS = {"main5": "hull,area2,pip,segs,close", "hard": "lattice,rectunion", "lattice": "lattice", "hull": "hull", "clip": "clip"}
CORE4, HELD2 = "knapsack,tsp,color,sched", "binpack,vcover"


def model_of(key):
    if key in OSS:
        return OSS[key]
    return QW[key], None


def build_manifest():
    M = []

    def g(tag, mk, tasks, toolbox_, seed, src, think=False, max_tokens=4096, temp=0.7, head="should", extra="", note=""):
        model, eff = model_of(mk)
        cond = f"{tasks}: {toolbox_}" + (f" {extra}" if extra else "") + (" +think" if think else "")
        M.append(dict(tag=tag, file=f"geocross_{tag}.jsonl", domain="geometry", model=model, effort=eff, tasks=tasks,
                      toolbox=toolbox_, head=head, extra=extra, think=think, seed=seed, temperature=temp, max_tokens=max_tokens,
                      condition=cond, source=src, note=note))

    def c(tag, mk, probs, doc, seed, src, think=False, max_tokens=4096, temp=0.7, extra="", note=""):
        model, eff = model_of(mk)
        cond = f"{probs}: {doc}" + (f" {extra}" if extra else "") + (" +think" if think else "")
        M.append(dict(tag=tag, file=f"co_{tag}.jsonl", domain="co", model=model, effort=eff, probs=probs, doc=doc, extra=extra,
                      think=think, seed=seed, temperature=temp, max_tokens=max_tokens, condition=cond, source=src, note=note))

    # ---- geometry, 5 core tasks, n = 300 per run (60 per task); "should use" header unless noted
    for m in ("8b", "14b", "32b"):
        g(f"F_geox{m}_dis0_t07s1", m, "main5", "K0", 1, "queue_prelude.sh")
        for s in (1, 2, 3):
            g(f"F_geox{m}_dis8_t07s{s}", m, "main5", "K8", s, "queue_final_geo.sh" if s == 1 else "queue_dis8mr.sh")
            g(f"F_geox{m}_base_t07s{s}", m, "main5", "none", s, "queue_final_geo.sh")
        g(f"F_geox{m}_dis0pre_t07s1", m, "main5", "K0", 1, "queue_prelude.sh", head="prelude", extra="prelude")
        g(f"F_geox{m}_dis8pre_t07s1", m, "main5", "K8", 1, "queue_prelude.sh", head="prelude", extra="prelude")
    g("F_geox14b_dis0use_t07s1", "14b", "main5", "K0", 1, "queue_usage.sh", extra="+API contract")
    g("F_geox14b_dis8use_t07s1", "14b", "main5", "K8", 1, "queue_usage.sh", extra="+API contract")
    for k in (0, 8):   # thinking, n = 100 (n_inst 10)
        g(f"T_geox8b_dis{k}_s1", "8b", "main5", f"K{k}", 1, "queue_thinkdis2.sh", think=True, max_tokens=20000)
        g(f"T_geox8b_dis{k}_s2", "8b", "main5", f"K{k}", 2, "queue_thinkdis2.sh", think=True, max_tokens=20000)
        for m in ("14b", "32b"):
            g(f"T_geox{m}_dis{k}", m, "main5", f"K{k}", 1, "queue_thinkdis.sh", think=True, max_tokens=20000)
            g(f"T_geox{m}_dis{k}_s2", m, "main5", f"K{k}", 2, "queue_thinkdis2.sh", think=True, max_tokens=20000)
        g(f"X_geox1_7b_dis{k}_t07s1", "1_7b", "main5", f"K{k}", 1, "queue_q17dis.sh")
        for s in (1, 2, 3):
            g(f"T_geox1_7b_dis{k}_s{s}", "1_7b", "main5", f"K{k}", s, "queue_q17dis.sh" if s == 1 else "queue_q17think.sh",
              think=True, max_tokens=20000)
        for s in (1, 2):
            g(f"X_geoxllama8_dis{k}_t07s{s}", "llama8", "main5", f"K{k}", s, "queue_l8dis.sh")
        for s in (1, 2, 3):
            g(f"X_geoxllama70_dis{k}_t07s{s}", "llama70", "main5", f"K{k}", s, "queue_xfam2.sh" if s == 1 else "queue_l70dis.sh")
        g(f"X_geoxllama70_dis{k}pre_t07s1", "llama70", "main5", f"K{k}", 1, "queue_l70dis.sh", head="prelude", extra="prelude")
        g(f"X_geoxr1l70_dis{k}_t06s1", "r1l70", "main5", f"K{k}", 1, "queue_r1.sh", temp=0.6, max_tokens=16000)
        for t in ("oss20low", "oss20med"):
            g(f"O5_geox{t}_k{k}", t, "main5", f"K{k}", 1, "queue_oss.sh", max_tokens=16000)
            g(f"O5_geox{t}_k{k}_s2", t, "main5", f"K{k}", 2, "queue_oss20s2.sh", max_tokens=16000)
        g(f"O5_geoxoss20hig_k{k}", "oss20hig", "main5", f"K{k}", 1, "queue_osshigh.sh", max_tokens=24000)
        for t in ("oss120low", "oss120med"):
            if k == 0:
                g(f"O5_geox{t}_k0", t, "main5", "K0", 1, "queue_oss.sh", max_tokens=16000)
            else:
                g(f"O5_geox{t}_k8fix2", t, "main5", "K8", 1, "queue_ossfix2.sh", max_tokens=16000,
                  note="re-run after the 2nd extractor fix; supersedes O5_geox*_k8 and *_k8fix")
        g(f"O5_geoxoss120hig_k{k}", "oss120hig", "main5", f"K{k}", 1, "queue_ossfix.sh", max_tokens=24000,
          note="produced after the 1st, before the 2nd extractor fix (doubled opening fence may still show as no_code)")
    for s in (1, 2, 3):
        g(f"X_geoxllama70_base_t07s{s}", "llama70", "main5", "none", s, "queue_xfam2.sh")
    g("X_geoxr1l70_base_t06s1", "r1l70", "main5", "none", 1, "queue_r1.sh", temp=0.6, max_tokens=16000)
    # ---- hard tasks (lattice + rectunion), n = 120 per run
    for m in ("8b", "14b", "32b"):
        for s in (1, 2, 3):
            g(f"R_geox{m}_base_t07s{s}", m, "hard", "none", s, "queue_real.sh")
        for k in (0, 8):
            g(f"R_geox{m}_dis{k}_t07s1", m, "hard", f"K{k}", 1, "queue_real.sh")
        g(f"R_geox{m}_base_think_t07s1", m, "hard", "none", 1, "queue_real.sh", think=True, max_tokens=20000)
        g(f"R_geox{m}_dis8think_t07s1", m, "hard", "K8", 1, "queue_real.sh", think=True, max_tokens=20000)
    for m in ("l70", "l8"):
        for s in (1, 2, 3):
            g(f"L_geox{m}_base_t07s{s}", m, "hard", "none", s, "queue_t7llama.sh")
        g(f"L_geox{m}_dis0_t07s1", m, "hard", "K0", 1, "queue_t7llama.sh")
        g(f"L_geox{m}_dis0abs_t07s1", m, "hard", "K0", 1, "queue_t7llama.sh", extra="abs-helper")
        g(f"L_geox{m}_dis8_t07s1", m, "hard", "K8", 1, "queue_t7llama.sh")
        g(f"L_geox{m}_dis8pre_t07s1", m, "hard", "K8", 1, "queue_t7llama.sh", head="prelude", extra="prelude")
    for m in ("8b", "32b", "l70"):
        for s in (2, 3):
            g(f"H_geox{m}_hard_t07s{s}", m, "hard", "none", s, "queue_repl.sh")
        for s in (1, 2, 3):
            g(f"H_geox{m}_hard_hint_t07s{s}", m, "hard", "none", s, "queue_rag.sh" if s == 1 else "queue_repl.sh", extra="+hint")
            g(f"H_geox{m}_hullhi_t07s{s}", m, "hull", "K0+polar_sort,collinear", s, "queue_rag.sh" if s == 1 else "queue_repl.sh")
            g(f"H_geox{m}_hullhi_hint_t07s{s}", m, "hull", "K0+polar_sort,collinear", s, "queue_rag.sh" if s == 1 else "queue_repl.sh",
              extra="+hint")
    g("R_geoxr1l70_base_t06s1", "r1l70", "hard", "none", 1, "queue_t7bud.sh", temp=0.6, max_tokens=16000)
    g("R_geoxr1l70_dis8_t06s1", "r1l70", "hard", "K8", 1, "queue_t7bud.sh", temp=0.6, max_tokens=16000)
    for t in ("oss20low", "oss20med", "oss120low", "oss120med"):
        g(f"O5_geox{t}_hard", t, "hard", "none", 1, "queue_oss.sh", max_tokens=16000)
    g("O5_geoxoss20hig_hard", "oss20hig", "hard", "none", 1, "queue_osshigh.sh", max_tokens=24000)
    # ---- lattice only: the signed-area helper (K0 = only polygon_area2)
    for m in ("8b", "14b", "32b"):
        for ah in ("abs", "signed_doc"):
            for s in (1, 2):
                g(f"S_geox{m}_dis0_{ah}_t07s{s}", m, "lattice", "K0", s, "queue_t7sign.sh", extra=f"{ah.replace('_', '-')}-helper")
        g(f"S_geox{m}_dis0_signed_t07s2", m, "lattice", "K0", 2, "queue_t7sign.sh")
    for m in ("8b", "32b"):
        for ah in ("signed", "abs"):
            g(f"S_geox{m}_dis0_{ah}_think_t07s1", m, "lattice", "K0", 1, "queue_signthink.sh", think=True, max_tokens=20000,
              extra="" if ah == "signed" else "abs-helper")
    # ---- polygon clipping, n = 60 per run
    for m in ("q8b", "q32b", "l70", "oss20low"):
        for s in (1, 2, 3):
            g(f"C2_geox{m}_base_t07s{s}", m, "clip", "none", s, "queue_clip.sh", max_tokens=16000)
        for k in (0, 8):
            g(f"C2_geox{m}_dis{k}_t07s1", m, "clip", f"K{k}", 1, "queue_clip.sh", max_tokens=16000)
        g(f"C2_geox{m}_hint_t07s1", m, "clip", "none", 1, "queue_clip.sh", max_tokens=16000, extra="+hint")
    for m in ("q8b", "q32b"):
        g(f"C2_geox{m}_think_t07s1", m, "clip", "none", 1, "queue_clip.sh", think=True, max_tokens=20000)
    for s in (2, 3):
        g(f"C2_geoxoss20low_hint_t07s{s}", "oss20low", "clip", "none", s, "queue_clip2.sh", max_tokens=16000, extra="+hint")
    for t in ("oss20med", "oss120low", "oss120med"):
        for s in (1, 2, 3):
            g(f"C2_geox{t}_base_t07s{s}", t, "clip", "none", s, "queue_clip2.sh", max_tokens=16000)
            g(f"C2_geox{t}_hint_t07s{s}", t, "clip", "none", s, "queue_clip2.sh", max_tokens=16000, extra="+hint")

    DOC = {"nodoc": "no doc", "doc": "full sheet", "doctask": "exact snippet", "cvrpdoc": "near-miss snippet"}
    # ---- optimization, 6 problems (4 core: 252 instances per run; 2 held-out: 108 per run), solver arm + 2 repair rounds
    for m in ("8b", "14b", "32b"):
        for s in (1, 2, 3):
            for d in ("nodoc", "doc", "doctask"):
                c(f"F_co{m}_{d}_s{s}", m, "core4", DOC[d], s, "queue_final_co.sh")
                if s < 3 or d != "nodoc":
                    c(f"H_co{m}_{d}_s{s}", m, "held2", DOC[d], s, "queue_coheld.sh" if s < 3 else "queue_usage.sh")
        c(f"T_co{m}_doctask", m, "core4", DOC["doctask"], 1, "queue_think.sh", think=True, max_tokens=20000, note="n_inst 6 (84 inst)")
    for m in ("8b", "14b"):
        for d in ("doctask", "doc"):
            c(f"HT_co{m}_{d}_s1", m, "held2", DOC[d], 1, "queue_heldthink.sh", think=True, max_tokens=20000)
    for d in ("nodoc", "doc", "doctask"):
        c(f"X_collama70_{d}", "llama70", "core4", DOC[d], 1, "queue_xfam2.sh", note="n_inst 6 (84 inst)")
        c(f"H_collama70_{d}_s1", "llama70", "held2", DOC[d], 1, "queue_l70held.sh")
        c(f"X_cor1l70_{d}", "r1l70", "core4", DOC[d], 1, "queue_r1.sh", temp=0.6, max_tokens=16000, note="n_inst 6 (84 inst)")
    c("G_col70_doctask", "l70", "core4+held2", DOC["doctask"], 1, "queue_rag.sh")
    for t in ("oss20low", "oss20med", "oss120low", "oss120med"):
        for d in ("nodoc", "doctask"):
            c(f"O5_co{t}_{d}", t, "core4+held2", DOC[d], 1, "queue_oss.sh", max_tokens=16000, note="n_inst 6 (120 inst)")
            c(f"O5_coV{t}_{d}", t, "cvrp", DOC[d], 1, "queue_oss.sh", max_tokens=16000)
            if t.startswith("oss20"):
                c(f"O5_co{t}_{d}_s2", t, "core4+held2", DOC[d], 2, "queue_oss20s2.sh", max_tokens=16000)
                c(f"O5_coV{t}_{d}_s2", t, "cvrp", DOC[d], 2, "queue_oss20s2.sh", max_tokens=16000)
    c("O5_cooss20low_doc", "oss20low", "core4+held2", DOC["doc"], 1, "queue_ossrag.sh", max_tokens=16000)
    c("O5_coVoss20low_doc", "oss20low", "cvrp", DOC["doc"], 1, "queue_ossrag.sh", max_tokens=16000)
    # ---- CVRP (30 instances)
    for m in ("8b", "14b", "32b"):
        c(f"V_co{m}_nodoc_s1", m, "cvrp", DOC["nodoc"], 1, "queue_cvrp.sh")
        c(f"V_co{m}_doc_s1", m, "cvrp", DOC["doc"], 1, "queue_cvrp.sh")
        for s in (1, 2, 3):
            c(f"V_co{m}_doctask_s{s}", m, "cvrp", DOC["doctask"], s, "queue_cvrp.sh")
        c(f"V_co{m}_doctask_think", m, "cvrp", DOC["doctask"], 1, "queue_cvrp.sh", think=True, max_tokens=20000)
        c(f"V_co{m}_nodoc_think", m, "cvrp", DOC["nodoc"], 1, "queue_cvrp.sh", think=True, max_tokens=20000)
    c("V_col70_nodoc_s1", "l70", "cvrp", DOC["nodoc"], 1, "queue_cvrp_llama.sh")
    c("V_col70_doc_s1", "l70", "cvrp", DOC["doc"], 1, "queue_cvrp_llama.sh")
    for s in (1, 2, 3):
        c(f"V_col70_doctask_s{s}", "l70", "cvrp", DOC["doctask"], s, "queue_cvrp_llama.sh")
    c("V_cor1l70_doctask_s1", "r1l70", "cvrp", DOC["doctask"], 1, "queue_cvrp_llama.sh", temp=0.6, max_tokens=16000)
    c("V_cor1l70_nodoc_s1", "r1l70", "cvrp", DOC["nodoc"], 1, "queue_cvrp_llama.sh", temp=0.6, max_tokens=16000)
    # ---- VRPTW (30 instances), max_tokens 16000
    for m in ("q8b", "q32b", "l70", "oss20low"):
        for d in ("nodoc", "doc", "cvrpdoc"):
            c(f"W_co{m}_{d}", m, "vrptw", DOC[d], 1, "queue_vrptw.sh", max_tokens=16000)
        for s in (1, 2, 3):
            c(f"W_co{m}_doctask_s{s}", m, "vrptw", DOC["doctask"], s, "queue_vrptw.sh", max_tokens=16000)
    for m in ("q8b", "q32b"):
        c(f"W_co{m}_doctask_think", m, "vrptw", DOC["doctask"], 1, "queue_vrptw.sh", think=True, max_tokens=20000)
    for t in ("oss20med", "oss120low", "oss120med"):
        c(f"W_co{t}_nodoc", t, "vrptw", DOC["nodoc"], 1, "queue_vrptw2.sh", max_tokens=16000)
        for s in (1, 2, 3):
            c(f"W_co{t}_doctask_s{s}", t, "vrptw", DOC["doctask"], s, "queue_vrptw2.sh", max_tokens=16000)
    c("W_cooss20low_nodoc_ex", "oss20low", "vrptw", DOC["nodoc"], 1, "queue_vrptw3.sh", max_tokens=16000, extra="+literal input")
    c("W_cooss120low_nodoc_ex", "oss120low", "vrptw", DOC["nodoc"], 1, "queue_vrptw3.sh", max_tokens=16000, extra="+literal input")
    for s in (1, 2, 3):
        c(f"W_cooss20low_doctask_ex_s{s}", "oss20low", "vrptw", DOC["doctask"], s, "queue_vrptw3.sh", max_tokens=16000,
          extra="+literal input")
    return M


def fix_pairs():
    """(fix name, domain, before tag, after tag, row filter or None). Paired by instance key."""
    P = []
    lat = lambda r: r["task"] == "lattice"   # noqa: E731
    for m in ("8b", "14b", "32b"):
        P += [("pre-define offered helpers (prelude)", "geometry", f"F_geox{m}_dis{k}_t07s1", f"F_geox{m}_dis{k}pre_t07s1", None) for k in (0, 8)]
        P += [("remove the 8 extra helpers (K8 -> K0)", "geometry", f"F_geox{m}_dis8_t07s1", f"F_geox{m}_dis0_t07s1", None)]
        tt = "T_geox8b_dis{k}_s1" if m == "8b" else f"T_geox{m}_dis{{k}}"
        P += [("thinking", "geometry", f"F_geox{m}_dis{k}_t07s1", tt.format(k=k), None) for k in (0, 8)]
        P += [("thinking", "geometry", f"R_geox{m}_base_t07s1", f"R_geox{m}_base_think_t07s1", None),
              ("thinking", "geometry", f"R_geox{m}_dis8_t07s1", f"R_geox{m}_dis8think_t07s1", None),
              ("remove the 8 extra helpers (K8 -> K0)", "geometry", f"R_geox{m}_dis8_t07s1", f"R_geox{m}_dis0_t07s1", None),
              ("unsigned (abs) area helper", "geometry", f"R_geox{m}_dis0_t07s1", f"S_geox{m}_dis0_abs_t07s1", lat),
              ("unsigned (abs) area helper", "geometry", f"S_geox{m}_dis0_signed_t07s2", f"S_geox{m}_dis0_abs_t07s2", None)]
    for m in ("8b", "32b"):
        P += [("thinking", "geometry", f"R_geox{m}_dis0_t07s1", f"S_geox{m}_dis0_signed_think_t07s1", lat),
              ("unsigned (abs) area helper", "geometry", f"S_geox{m}_dis0_signed_think_t07s1", f"S_geox{m}_dis0_abs_think_t07s1", None)]
    P += [("API contract sentence", "geometry", f"F_geox14b_dis{k}_t07s1", f"F_geox14b_dis{k}use_t07s1", None) for k in (0, 8)]
    P += [("thinking", "geometry", f"X_geox1_7b_dis{k}_t07s1", f"T_geox1_7b_dis{k}_s1", None) for k in (0, 8)]
    P += [("remove the 8 extra helpers (K8 -> K0)", "geometry", "X_geox1_7b_dis8_t07s1", "X_geox1_7b_dis0_t07s1", None)]
    P += [("remove the 8 extra helpers (K8 -> K0)", "geometry", f"X_geoxllama8_dis8_t07s{s}", f"X_geoxllama8_dis0_t07s{s}", None) for s in (1, 2)]
    P += [("remove the 8 extra helpers (K8 -> K0)", "geometry", f"X_geoxllama70_dis8_t07s{s}", f"X_geoxllama70_dis0_t07s{s}", None) for s in (1, 2, 3)]
    P += [("pre-define offered helpers (prelude)", "geometry", f"X_geoxllama70_dis{k}_t07s1", f"X_geoxllama70_dis{k}pre_t07s1", None) for k in (0, 8)]
    for m in ("l70", "l8"):
        P += [("pre-define offered helpers (prelude)", "geometry", f"L_geox{m}_dis8_t07s1", f"L_geox{m}_dis8pre_t07s1", None),
              ("unsigned (abs) area helper", "geometry", f"L_geox{m}_dis0_t07s1", f"L_geox{m}_dis0abs_t07s1", lat),
              ("remove the 8 extra helpers (K8 -> K0)", "geometry", f"L_geox{m}_dis8_t07s1", f"L_geox{m}_dis0_t07s1", None)]
    for m in ("8b", "32b", "l70"):
        P += [("one-sentence algorithm hint", "geometry", f"H_geox{m}_hullhi_t07s{s}", f"H_geox{m}_hullhi_hint_t07s{s}", None) for s in (1, 2, 3)]
        b1 = "L_geoxl70_base_t07s1" if m == "l70" else f"R_geox{m}_base_t07s1"
        P += [("one-sentence algorithm hint", "geometry", b1, f"H_geox{m}_hard_hint_t07s1", None)]
        P += [("one-sentence algorithm hint", "geometry", f"H_geox{m}_hard_t07s{s}", f"H_geox{m}_hard_hint_t07s{s}", None) for s in (2, 3)]
    for m in ("q8b", "q32b", "l70", "oss20low"):
        P += [("one-sentence algorithm hint", "geometry", f"C2_geox{m}_base_t07s1", f"C2_geox{m}_hint_t07s1", None),
              ("remove the 8 extra helpers (K8 -> K0)", "geometry", f"C2_geox{m}_dis8_t07s1", f"C2_geox{m}_dis0_t07s1", None)]
    for m in ("q8b", "q32b"):
        P += [("thinking", "geometry", f"C2_geox{m}_base_t07s1", f"C2_geox{m}_think_t07s1", None)]
    P += [("one-sentence algorithm hint", "geometry", f"C2_geoxoss20low_base_t07s{s}", f"C2_geoxoss20low_hint_t07s{s}", None) for s in (2, 3)]
    for t in ("oss20med", "oss120low", "oss120med"):
        P += [("one-sentence algorithm hint", "geometry", f"C2_geox{t}_base_t07s{s}", f"C2_geox{t}_hint_t07s{s}", None) for s in (1, 2, 3)]
    for k in (0, 8):
        P += [("more reasoning effort (low -> medium)", "geometry", f"O5_geoxoss20low_k{k}", f"O5_geoxoss20med_k{k}", None),
              ("more reasoning effort (low -> medium)", "geometry", f"O5_geoxoss20low_k{k}_s2", f"O5_geoxoss20med_k{k}_s2", None)]
    P += [("more reasoning effort (low -> medium)", "geometry", "O5_geoxoss120low_k0", "O5_geoxoss120med_k0", None),
          ("more reasoning effort (low -> medium)", "geometry", "O5_geoxoss120low_k8fix2", "O5_geoxoss120med_k8fix2", None),
          ("more reasoning effort (low -> medium)", "geometry", "O5_geoxoss20low_hard", "O5_geoxoss20med_hard", None),
          ("more reasoning effort (low -> medium)", "geometry", "O5_geoxoss120low_hard", "O5_geoxoss120med_hard", None)]
    P += [("more reasoning effort (low -> medium)", "geometry", f"C2_geox{a}_base_t07s{s}", f"C2_geox{b}_base_t07s{s}", None)
          for a, b in (("oss20low", "oss20med"), ("oss120low", "oss120med")) for s in (1, 2, 3)]
    # ---- control: the same condition re-sampled (seed 1 -> seed 2); a fix only "addresses" a class if it beats this
    CTRL = "control: re-sample the same condition (seed 1 -> 2)"
    for m in ("8b", "14b", "32b"):
        P += [(CTRL, "geometry", f"F_geox{m}_{c}_t07s1", f"F_geox{m}_{c}_t07s2", None) for c in ("dis8", "base")]
        P += [(CTRL, "geometry", f"R_geox{m}_base_t07s1", f"R_geox{m}_base_t07s2", None)]
        P += [(CTRL, "co", f"F_co{m}_{d}_s1", f"F_co{m}_{d}_s2", None) for d in ("nodoc", "doc", "doctask")]
        P += [(CTRL, "co", f"H_co{m}_{d}_s1", f"H_co{m}_{d}_s2", None) for d in ("nodoc", "doc", "doctask")]
        P += [(CTRL, "co", f"V_co{m}_doctask_s1", f"V_co{m}_doctask_s2", None)]
    P += [(CTRL, "geometry", f"X_geoxllama70_dis{k}_t07s1", f"X_geoxllama70_dis{k}_t07s2", None) for k in (0, 8)]
    P += [(CTRL, "geometry", f"X_geoxllama8_dis{k}_t07s1", f"X_geoxllama8_dis{k}_t07s2", None) for k in (0, 8)]
    P += [(CTRL, "geometry", f"T_geox1_7b_dis{k}_s1", f"T_geox1_7b_dis{k}_s2", None) for k in (0, 8)]
    P += [(CTRL, "geometry", f"L_geox{m}_base_t07s1", f"L_geox{m}_base_t07s2", None) for m in ("l70", "l8")]
    for m in ("8b", "32b", "l70"):
        P += [(CTRL, "geometry", f"H_geox{m}_hullhi_t07s1", f"H_geox{m}_hullhi_t07s2", None),
              (CTRL, "geometry", f"H_geox{m}_hard_hint_t07s1", f"H_geox{m}_hard_hint_t07s2", None)]
    for m in ("q8b", "q32b", "l70", "oss20low", "oss20med", "oss120low", "oss120med"):
        P += [(CTRL, "geometry", f"C2_geox{m}_base_t07s1", f"C2_geox{m}_base_t07s2", None)]
        P += [(CTRL, "co", f"W_co{m}_doctask_s1", f"W_co{m}_doctask_s2", None)]
    P += [(CTRL, "geometry", f"O5_geoxoss20{e}_k{k}", f"O5_geoxoss20{e}_k{k}_s2", None) for e in ("low", "med") for k in (0, 8)]
    P += [(CTRL, "co", f"O5_co{p}oss20{e}_{d}", f"O5_co{p}oss20{e}_{d}_s2", None) for p in ("", "V") for e in ("low", "med") for d in ("nodoc", "doctask")]
    P += [(CTRL, "co", "W_cooss20low_doctask_ex_s1", "W_cooss20low_doctask_ex_s2", None)]
    # ---- optimization
    for m in ("8b", "14b", "32b"):
        for s in (1, 2, 3):
            P += [("exact snippet (no doc -> snippet)", "co", f"F_co{m}_nodoc_s{s}", f"F_co{m}_doctask_s{s}", None),
                  ("exact snippet (full sheet -> snippet)", "co", f"F_co{m}_doc_s{s}", f"F_co{m}_doctask_s{s}", None),
                  ("exact snippet (full sheet -> snippet)", "co", f"H_co{m}_doc_s{s}", f"H_co{m}_doctask_s{s}", None)]
            if s < 3:
                P += [("exact snippet (no doc -> snippet)", "co", f"H_co{m}_nodoc_s{s}", f"H_co{m}_doctask_s{s}", None)]
        P += [("thinking", "co", f"F_co{m}_doctask_s1", f"T_co{m}_doctask", None),
              ("exact snippet (no doc -> snippet)", "co", f"V_co{m}_nodoc_s1", f"V_co{m}_doctask_s1", None),
              ("exact snippet (full sheet -> snippet)", "co", f"V_co{m}_doc_s1", f"V_co{m}_doctask_s1", None),
              ("thinking", "co", f"V_co{m}_doctask_s1", f"V_co{m}_doctask_think", None),
              ("thinking", "co", f"V_co{m}_nodoc_s1", f"V_co{m}_nodoc_think", None)]
    for m in ("8b", "14b"):
        P += [("thinking", "co", f"H_co{m}_{d}_s1", f"HT_co{m}_{d}_s1", None) for d in ("doctask", "doc")]
    for a, b in (("X_collama70", "X_collama70"), ("X_cor1l70", "X_cor1l70")):
        P += [("exact snippet (no doc -> snippet)", "co", f"{a}_nodoc", f"{b}_doctask", None),
              ("exact snippet (full sheet -> snippet)", "co", f"{a}_doc", f"{b}_doctask", None)]
    P += [("exact snippet (no doc -> snippet)", "co", "H_collama70_nodoc_s1", "H_collama70_doctask_s1", None),
          ("exact snippet (full sheet -> snippet)", "co", "H_collama70_doc_s1", "H_collama70_doctask_s1", None),
          ("exact snippet (no doc -> snippet)", "co", "V_col70_nodoc_s1", "V_col70_doctask_s1", None),
          ("exact snippet (full sheet -> snippet)", "co", "V_col70_doc_s1", "V_col70_doctask_s1", None),
          ("exact snippet (no doc -> snippet)", "co", "V_cor1l70_nodoc_s1", "V_cor1l70_doctask_s1", None),
          ("exact snippet (full sheet -> snippet)", "co", "O5_cooss20low_doc", "O5_cooss20low_doctask", None),
          ("exact snippet (full sheet -> snippet)", "co", "O5_coVoss20low_doc", "O5_coVoss20low_doctask", None)]
    for t in ("oss20low", "oss20med", "oss120low", "oss120med"):
        P += [("exact snippet (no doc -> snippet)", "co", f"O5_co{t}_nodoc", f"O5_co{t}_doctask", None),
              ("exact snippet (no doc -> snippet)", "co", f"O5_coV{t}_nodoc", f"O5_coV{t}_doctask", None)]
        if t.startswith("oss20"):
            P += [("exact snippet (no doc -> snippet)", "co", f"O5_co{t}_nodoc_s2", f"O5_co{t}_doctask_s2", None),
                  ("exact snippet (no doc -> snippet)", "co", f"O5_coV{t}_nodoc_s2", f"O5_coV{t}_doctask_s2", None)]
    for m in ("q8b", "q32b", "l70", "oss20low", "oss20med", "oss120low", "oss120med"):
        P += [("exact snippet (no doc -> snippet)", "co", f"W_co{m}_nodoc", f"W_co{m}_doctask_s1", None)]
        if m in ("q8b", "q32b", "l70", "oss20low"):
            P += [("exact snippet (full sheet -> snippet)", "co", f"W_co{m}_doc", f"W_co{m}_doctask_s1", None),
                  ("exact snippet (near-miss -> exact)", "co", f"W_co{m}_cvrpdoc", f"W_co{m}_doctask_s1", None)]
    for m in ("q8b", "q32b"):
        P += [("thinking", "co", f"W_co{m}_doctask_s1", f"W_co{m}_doctask_think", None)]
    P += [("show the literal input (--show_stdin)", "co", f"W_cooss20low_doctask_s{s}", f"W_cooss20low_doctask_ex_s{s}", None) for s in (1, 2, 3)]
    P += [("show the literal input (--show_stdin)", "co", f"W_coo{x}_nodoc", f"W_coo{x}_nodoc_ex", None) for x in ("ss20low", "ss120low")]
    P += [("more reasoning effort (low -> medium)", "co", f"W_co{a}_doctask_s{s}", f"W_co{b}_doctask_s{s}", None)
          for a, b in (("oss20low", "oss20med"), ("oss120low", "oss120med")) for s in (1, 2, 3)]
    P += [("more reasoning effort (low -> medium)", "co", f"W_co{a}_nodoc", f"W_co{b}_nodoc", None)
          for a, b in (("oss20low", "oss20med"), ("oss120low", "oss120med"))]
    P += [("more reasoning effort (low -> medium)", "co", f"O5_co{p}oss{z}low_{d}", f"O5_co{p}oss{z}med_{d}", None)
          for p in ("", "V") for z in ("20", "120") for d in ("nodoc", "doctask")]
    return P


def select_groups():
    """3-seed groups for label-free selection (before = first tag = seed-1 single sample)."""
    G = []
    for m in ("8b", "14b", "32b"):
        G += [("geometry", [f"F_geox{m}_dis8_t07s{s}" for s in (1, 2, 3)]), ("geometry", [f"F_geox{m}_base_t07s{s}" for s in (1, 2, 3)]),
              ("geometry", [f"R_geox{m}_base_t07s{s}" for s in (1, 2, 3)])]
        for d in ("nodoc", "doc", "doctask"):
            G += [("co", [f"F_co{m}_{d}_s{s}" for s in (1, 2, 3)])]
        G += [("co", [f"H_co{m}_{d}_s{s}" for s in (1, 2, 3)]) for d in ("doc", "doctask")]
        G += [("co", [f"V_co{m}_doctask_s{s}" for s in (1, 2, 3)])]
    for k in (0, 8):
        G += [("geometry", [f"X_geoxllama70_dis{k}_t07s{s}" for s in (1, 2, 3)])]
    G += [("geometry", [f"X_geoxllama70_base_t07s{s}" for s in (1, 2, 3)])]
    for m in ("l70", "l8"):
        G += [("geometry", [f"L_geox{m}_base_t07s{s}" for s in (1, 2, 3)])]
    for m in ("8b", "32b", "l70"):
        G += [("geometry", [f"H_geox{m}_hullhi_t07s{s}" for s in (1, 2, 3)]), ("geometry", [f"H_geox{m}_hullhi_hint_t07s{s}" for s in (1, 2, 3)]),
              ("geometry", [f"H_geox{m}_hard_hint_t07s{s}" for s in (1, 2, 3)])]
    for m in ("q8b", "q32b", "l70", "oss20low", "oss20med", "oss120low", "oss120med"):
        G += [("geometry", [f"C2_geox{m}_base_t07s{s}" for s in (1, 2, 3)])]
    for m in ("oss20low", "oss20med", "oss120low", "oss120med"):
        G += [("geometry", [f"C2_geox{m}_hint_t07s{s}" for s in (1, 2, 3)])]
    G += [("co", ["V_col70_doctask_s1", "V_col70_doctask_s2", "V_col70_doctask_s3"])]
    for m in ("q8b", "q32b", "l70", "oss20low", "oss20med", "oss120low", "oss120med"):
        G += [("co", [f"W_co{m}_doctask_s{s}" for s in (1, 2, 3)])]
    G += [("co", [f"W_cooss20low_doctask_ex_s{s}" for s in (1, 2, 3)])]
    return G


# ----------------------------------------------------------------------------------------------------------------------------------
# 2. sandboxed re-execution with a small exception-recording wrapper (behaviour unchanged otherwise)
# ----------------------------------------------------------------------------------------------------------------------------------
DRIVER = r'''
import sys as _s, json as _j, traceback as _t, linecache as _lc
_SRC = %s
_g = {"__name__": "__main__", "__builtins__": __builtins__}
_lc.cache["main.py"] = (len(_SRC), None, _SRC.splitlines(True), "main.py")   # traceback lines from the program, not this wrapper
try:
    exec(compile(_SRC, "main.py", "exec"), _g)
except SystemExit:
    raise
except BaseException as _e:
    _tb = _t.extract_tb(_e.__traceback__)[1:]
    _o = getattr(_e, "obj", None) if isinstance(_e, AttributeError) else None
    _info = {"type": type(_e).__name__, "msg": str(_e)[:300],
             "name": getattr(_e, "name", None) if isinstance(_e, (NameError, AttributeError, ImportError)) else None,
             "obj_module": ((_o.__name__ if isinstance(_o, type(_s)) else type(_o).__module__) if isinstance(_e, AttributeError) else None),
             "obj_type": (type(_o).__name__ if isinstance(_e, AttributeError) else None),
             "ortools_frame": any("/ortools/" in f.filename for f in _tb),
             "fnames": sorted({f.name for f in _tb if f.filename == "main.py"})[:40],
             "frames": [[f.filename.split("site-packages/")[-1][-60:], f.name, f.lineno, (f.line or "")[:100]] for f in _tb[-6:]]}
    _x = _j.dumps(_info)
    while len(_x) > 1800 and _info["frames"]:
        _info["frames"].pop(0); _x = _j.dumps(_info)
    try:
        _s.stdout.flush()
    except Exception:
        pass
    _s.stderr.write("\n#E1EXC " + _x[:1900] + "\n")
    _s.exit(1)
'''

_CACHE, _LOCK, _CACHE_FILE = {}, threading.Lock(), None


def _key(*parts):
    return hashlib.sha1("\x00".join(map(str, parts)).encode()).hexdigest()


def cached_run(src, stdin, timeout, mem=1 << 30, wrap=True):
    k = _key(src, stdin, timeout, wrap)
    if k in _CACHE:
        return _CACHE[k]
    r = run_python(DRIVER % repr(src) if wrap else src, stdin, timeout=timeout, mem_bytes=mem)
    exc = None
    m = re.search(r"#E1EXC (\{.*\})\s*$", r.stderr or "")
    if m:
        try:
            exc = json.loads(m.group(1))
        except json.JSONDecodeError:
            exc = None
    if exc is None and r.status in ("re", "mle"):   # crash before / outside the wrapper (e.g. interpreter-level), keep the stderr tail
        last = [l for l in (r.stderr or "").strip().splitlines() if l.strip()]
        exc = {"type": (last[-1].split(":")[0] if last else "?"), "msg": (last[-1] if last else "")[:300], "name": None,
               "obj_module": None, "obj_type": None, "ortools_frame": "/ortools/" in (r.stderr or ""), "fnames": [], "frames": []}
    out = {"status": r.status, "stdout": (r.stdout or "")[-2000:], "exc": exc}
    with _LOCK:
        _CACHE[k] = out
        if _CACHE_FILE:
            with open(_CACHE_FILE, "a") as f:
                f.write(json.dumps({"k": k, "v": out}) + "\n")
    return out


def load_cache(path):
    global _CACHE_FILE
    _CACHE_FILE = path
    if os.path.exists(path):
        for line in open(path):
            try:
                d = json.loads(line)
                _CACHE[d["k"]] = d["v"]
            except json.JSONDecodeError:
                pass


# ----------------------------------------------------------------------------------------------------------------------------------
# 3. geometry classification
# ----------------------------------------------------------------------------------------------------------------------------------
GEO_CLASSES = ["no_code", "runaway", "syntax", "environment", "packaging", "interface", "input_format", "crash_other", "timeout",
               "no_output", "crash_nonrepro", "output_format", "logic", "orientation", "degenerate", "precision", "variant_other"]
GEO_SUPER = {"no_code": "generation", "runaway": "generation", "syntax": "generation",
             "environment": "API/environment", "packaging": "packaging/interface", "interface": "packaging/interface",
             "input_format": "input format",
             "crash_other": "other runtime", "timeout": "other runtime", "no_output": "other runtime", "crash_nonrepro": "other runtime",
             "output_format": "output format", "logic": "algorithmic", "orientation": "algorithmic", "degenerate": "algorithmic",
             "precision": "algorithmic", "variant_other": "algorithmic"}
YESNO = {"true": "yes", "false": "no", "inside": "yes", "outside": "no", "y": "yes", "n": "no"}


def canon(tok):
    if tok is None:
        return None
    t = tok.strip().strip("'\"`.,;:()[]").lower()
    t = YESNO.get(t, t)
    try:
        return ("num", Fraction(t))
    except (ValueError, ZeroDivisionError):
        return ("str", t)


def inst_key(r):
    return (r["task"], r["n"], r["inst"])


_VCACHE = {}


def geo_variants(task, n, i, prefix=""):
    k = (prefix, task, n, i)
    if k not in _VCACHE:
        rng = random.Random(f"{prefix}{task}-{n}-{i}")
        _VCACHE[k] = variants(task, base_instance(task, n, rng), rng)
    return _VCACHE[k]


def _signed2(P):
    return sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1] for i in range(len(P)))


def orientation_variants(task, V):
    """variants that reverse the orientation of the input: mirror always (a reflection flips every orientation test); permute when it
    reversed the vertex order of a polygon (poly / A / B) or applied an odd permutation to the triangle T (run_geo.variants)."""
    O = {"mirror"}
    idn, per = V["identity"], V["permute"]
    for key in ("poly", "A", "B"):
        if key in per:
            P = [tuple(p) for p in per[key]]
            src = next((idn[k2] for k2 in ("poly", "A", "B") if k2 in idn and set(map(tuple, idn[k2])) == set(P)), None)
            if src is not None and (_signed2(P) > 0) != (_signed2([tuple(p) for p in src]) > 0):
                O.add("permute")
    if "T" in per:
        o = lambda T: (T[1][0] - T[0][0]) * (T[2][1] - T[0][1]) - (T[1][1] - T[0][1]) * (T[2][0] - T[0][0])   # noqa: E731
        if (o(per["T"]) > 0) != (o(idn["T"]) > 0):
            O.add("permute")
    return O


def offered_helpers(meta, row):
    if meta["toolbox"] == "none":
        return set()
    return set(GNEED[row["task"]]) | set(row.get("distractors") or [])


def prelude_src(meta, row):
    if meta["head"] != "prelude":
        return ""
    fixed = ["polar_sort", "collinear"] if "polar_sort" in meta["toolbox"] else None
    k = int(meta["toolbox"][1]) if meta["toolbox"][0] == "K" and meta["toolbox"][1].isdigit() else 0
    tb, _ = toolbox(row["task"], k, "related", random.Random(f"{row['task']}-{row['n']}-{row['inst']}-tb"), "prelude", fixed=fixed)
    return "\n".join(re.findall(r"```python\n(.*?)```", tb, re.S)) + "\n"


def toolbox_src(meta, row):
    """the offered helper definitions (as in poc/rescore_prelude.py), whatever the header"""
    if meta["toolbox"] == "none":
        return ""
    fixed = ["polar_sort", "collinear"] if "polar_sort" in meta["toolbox"] else None
    k = int(meta["toolbox"][1]) if meta["toolbox"][1].isdigit() else 0
    tb, _ = toolbox(row["task"], k, "related", random.Random(f"{row['task']}-{row['n']}-{row['inst']}-tb"), "prelude", fixed=fixed)
    return "\n".join(re.findall(r"```python\n(.*?)```", tb, re.S)) + "\n"


def geo_packaging_cf(meta, row):
    """same-program counterfactual for a packaging failure: pre-define the offered helpers (the program's own definitions come later
    and override) and re-run on all 8 versions. True = packaging was the only problem."""
    V = geo_variants(row["task"], row["n"], row["inst"])
    src = toolbox_src(meta, row) + row["code"]
    for x in V.values():
        o = cached_run(src, render(row["task"], x)[1], timeout=10, wrap=False)
        toks = o["stdout"].strip().split() if o["status"] == "ok" else []
        if not toks or toks[-1].lower() != answer(row["task"], x):
            return False
    return True


def capped(meta, row):
    return row.get("finish") == "length" or (row.get("out_tokens") or 0) >= meta["max_tokens"]


def geo_needs_rerun(row):
    return bool(row["class"] != "correct_all" and row.get("code") and row["per_variant"].get("identity") is not True)


def geo_rerun(meta, row):
    V = geo_variants(row["task"], row["n"], row["inst"])
    _, stdin, _ = render(row["task"], V["identity"])
    return cached_run(prelude_src(meta, row) + row["code"], stdin, timeout=10)


GEO_LAYOUTS = {"count lines dropped": lambda s: "\n".join(l for l in s.split("\n") if len(l.split()) != 1) + "\n",
               "all on one line": lambda s: " ".join(s.split()) + "\n"}


def geo_format_cf(meta, row):
    """input-format counterfactual (as the VRPTW one): the same instance serialized in another plain layout (the single-number count
    lines removed, or every number on one line). Returns the layout under which the program is correct on all 7 non-degenerate
    variants (so a lucky yes/no answer does not count), else None."""
    task, V = row["task"], geo_variants(row["task"], row["n"], row["inst"])
    src = prelude_src(meta, row) + row["code"]
    for name, f in GEO_LAYOUTS.items():
        ok = True
        for vn in ["identity", "translate", "rot90", "mirror", "permute", "scale", "big", "degen"]:
            x = V[vn]
            stdin = render(task, x)[1]
            if f(stdin) == stdin:
                ok = False; break
            o = cached_run(src, f(stdin), timeout=10, wrap=False)
            toks = o["stdout"].strip().split() if o["status"] == "ok" else []
            good = bool(toks) and toks[-1].lower() == answer(task, x)
            if vn == "degen":
                return name + ("" if good else " (degenerate variant still wrong)")
            if not good:
                ok = False; break
    return None


def classify_geo(meta, row, rr, fmt=None):
    """returns (class, detail) for a failing program; None for a correct one."""
    if row["class"] == "correct_all":
        return None
    pv, task = row["per_variant"], row["task"]
    cap = capped(meta, row)
    if not row.get("code"):
        return ("runaway" if cap else "no_code"), ""
    if fmt:
        return "input_format", f"correct with the input {fmt}"
    idn = pv.get("identity")
    if idn is None:   # crashed / printed nothing on the identity instance
        st, exc = rr["status"], rr["exc"]
        if st == "tle":
            return "timeout", ""
        if exc:
            t, offered = exc["type"], offered_helpers(meta, row)
            if t in ("SyntaxError", "IndentationError", "TabError"):
                return ("runaway" if cap else "syntax"), f"{t}: {exc['msg'][:80]}"
            if t == "NameError" and exc.get("name") in offered:
                return "packaging", f"NameError {exc['name']}"
            if t in ("ModuleNotFoundError", "ImportError"):
                return "environment", f"{t} {exc.get('name')}"
            inner = [f[1] for f in (exc.get("frames") or []) if f[0] == "main.py"][-1:]   # innermost frame of the program itself
            hit = (set(inner) & offered) | {h for h in offered if re.search(rf"\b{h}\(\)", exc["msg"])}
            if hit:
                return "interface", f"{t} in/at {sorted(hit)[0]}: {exc['msg'][:80]}"
            return "crash_other", f"{t}: {exc['msg'][:80]}"
        if st == "ok" and not rr["stdout"].strip():
            return "no_output", ""
        return "crash_nonrepro", f"re-run status {st}"
    if idn is False:
        toks = rr["stdout"].strip().split() if rr["status"] == "ok" else []
        out = toks[-1] if toks else None
        gold = answer(task, geo_variants(task, row["n"], row["inst"])["identity"])
        if out is not None and canon(out) == canon(gold):
            return "output_format", f"printed {out!r}, expected {gold!r}"
        return "logic", (f"printed {out!r}, expected {gold!r}" if out is not None else f"re-run status {rr['status']}")
    bad = {v for v, ok in pv.items() if ok is not True}
    O = orientation_variants(task, geo_variants(task, row["n"], row["inst"]))
    pat = "+".join(v for v in ["translate", "rot90", "mirror", "permute", "scale", "big", "degen"] if v in bad)
    if bad <= O:
        return "orientation", pat
    if bad == {"degen"}:
        return "degenerate", pat
    if bad <= {"big", "scale"}:
        return "precision", pat
    return "variant_other", pat


# ----------------------------------------------------------------------------------------------------------------------------------
# 4. optimization classification
# ----------------------------------------------------------------------------------------------------------------------------------
CO_CLASSES = ["no_code", "runaway", "syntax", "api", "input_format", "output_format", "infeasible_model", "no_solution",
              "infeasible_output", "suboptimal", "crash_other", "timeout", "no_output", "nonrepro"]
CO_SUPER = {"no_code": "generation", "runaway": "generation", "syntax": "generation", "api": "API/knowledge",
            "input_format": "input format", "output_format": "output format", "infeasible_model": "modelling/logic",
            "no_solution": "modelling/logic", "infeasible_output": "modelling/logic", "suboptimal": "modelling/logic",
            "crash_other": "other runtime", "timeout": "other runtime", "no_output": "other runtime", "nonrepro": "other runtime"}
_ORT = None


def ortools_vocab():
    """(class names, public attribute names) of the OR-Tools Python modules the programs use, collected programmatically; attribute
    names that also exist on builtin types (list, dict, str, numbers, None) or are plain lowercase words (value, size, next) are
    dropped so they cannot match ordinary errors."""
    global _ORT
    if _ORT is None:
        import importlib
        import inspect
        mods = []
        for name in ("ortools.constraint_solver.pywrapcp", "ortools.constraint_solver.routing_enums_pb2",
                     "ortools.constraint_solver.routing_parameters_pb2", "ortools.sat.python.cp_model",
                     "ortools.sat.python.cp_model_helper", "ortools.sat.cp_model_pb2", "ortools.util.python.sorted_interval_list"):
            try:
                mods.append(importlib.import_module(name))
            except ImportError:
                pass
        classes = {n: o for mod in mods for n, o in vars(mod).items() if inspect.isclass(o) and not n.startswith("_")}
        builtin = set().union(*(dir(t) for t in (list, dict, str, int, float, tuple, set, bool, type(None), object)))
        attrs = {a for o in classes.values() for a in dir(o) if not a.startswith("_")} - builtin
        attrs = {a for a in attrs if a != a.lower() or "_" in a}   # distinctive API names only (CumulVar, new_int_var), not `value`/`size`
        _ORT = ({n for n in classes if len(n) >= 5}, attrs)
    return _ORT


_ATTR_MSG = re.compile(r"^'(\w+)' object has no attribute '(\w+)'")   # the interpreter's fixed AttributeError formats
_MOD_MSG = re.compile(r"^module '([\w.]+)' has no attribute '(\w+)'")


def co_success(r):
    if not (r["feasible"] and r["gap"] is not None):
        return False
    return r["gap"] <= (1e-9 if r["prob"] in ("cvrp", "vrptw") else 1.0)


_INST = {}


def co_inst(prob, n, key):
    if key not in _INST:
        _INST[key] = gen(prob, n, random.Random(key))
    return _INST[key]


def parse_last_line(stdout):
    lines = [l for l in stdout.strip().splitlines() if l.strip()]
    return re.findall(r"\d+", lines[-1]) if lines else None


def lenient_parses(stdout):
    """other readings of the same stdout: each line on its own, and all lines concatenated (routes printed one per line)"""
    lines = [l for l in stdout.strip().splitlines() if l.strip()]
    cands = [re.findall(r"\d+", l) for l in lines] + [re.findall(r"\d+", " ".join(lines))]
    cands += [c[:-1] for c in cands if len(c) > 1 and c[-1] == c[0]]   # a tour printed with its closing return to the start
    return [c for c in cands if c]


def co_needs_rerun(r):
    return bool(not co_success(r) and r.get("code") and not (r["status"] == "ok" and r["feasible"]))


def co_rerun(r, stdin=None):
    inst = co_inst(r["prob"], r["n"], r["key"])
    return cached_run(r["code"], stdin if stdin is not None else describe(r["prob"], inst)[1], timeout=40, mem=4 << 30)


def vrptw_cf_stdin(r):
    inst = co_inst(r["prob"], r["n"], r["key"])
    s = describe(r["prob"], inst)[1].split("\n")
    f = s[0].split()
    return "\n".join([" ".join(f[:3] + f[4:])] + s[1:])   # `n capacity K service horizon` -> `n capacity K horizon`


def eval_sol(r, sol):
    inst = co_inst(r["prob"], r["n"], r["key"])
    feas, val = objective(r["prob"], inst, sol) if sol else (False, None)
    if not feas or val is None:
        return "infeasible"
    gap = (r["ref"] - val) / r["ref"] * 100 if r["prob"] == "knapsack" else (val - r["ref"]) / r["ref"] * 100
    return "optimal" if gap <= (1e-9 if r["prob"] in ("cvrp", "vrptw") else 1.0) else "feasible"


def classify_co(meta, r, rr, cf):
    if co_success(r):
        return None
    if r["status"] == "no_code" or not r.get("code"):
        return ("runaway" if r.get("finish") == "length" else "no_code"), ""
    if cf is not None and cf != "infeasible":
        return "input_format", f"service field removed -> {cf}"
    if r["status"] == "ok" and r["feasible"]:
        return "suboptimal", f"gap {r['gap']:.1f}%"
    st, exc = rr["status"], rr["exc"]
    if st == "tle":
        return "timeout", ""
    if exc:
        t, msg = exc["type"], exc["msg"]
        if t in ("SyntaxError", "IndentationError", "TabError"):
            return ("runaway" if r.get("finish") == "length" else "syntax"), f"{t}: {msg[:80]}"
        if t == "Exception" and msg.strip() == "CP Solver fail":
            if r["prob"] == "vrptw":   # does the program get past this failure once the skipped `service` field is removed?
                o = co_rerun(r, vrptw_cf_stdin(r))
                past = not (o["exc"] and o["exc"]["msg"].strip() == "CP Solver fail")
                return "infeasible_model", ("CP Solver fail; with the service field removed it gets past it and then fails otherwise "
                                            "(skipped field + a second error)" if past else "CP Solver fail, also without the service field")
            return "infeasible_model", "CP Solver fail (a posted constraint is unsatisfiable)"
        if "Check failure" in t or "Check failure" in msg:   # glog CHECK abort inside OR-Tools native code = invalid use of its API
            return "api", "OR-Tools CHECK failure (native assertion)"
        classes, attrs = ortools_vocab()
        m1, m2 = _ATTR_MSG.match(msg), _MOD_MSG.match(msg)
        otype, oattr = (m1.group(1), m1.group(2)) if m1 else (None, (m2.group(2) if m2 else None))
        if t == "AttributeError" and otype == "NoneType" and oattr in attrs:
            return "no_solution", f"used the empty solver result: {msg[:80]}"
        mod = (m2.group(1) if m2 else "") or exc.get("obj_module") or ""
        vocab_hit = sorted(w for w in classes if re.search(rf"\b{w}\b", msg))
        if (exc.get("ortools_frame") or mod.startswith(("ortools", "google.protobuf")) or vocab_hit or
                (t in ("ModuleNotFoundError", "ImportError") and str(exc.get("name") or "").startswith("ortools")) or
                (t == "AttributeError" and oattr in attrs)):
            return "api", f"{t}: {msg[:100]}"
        return "crash_other", f"{t}: {msg[:100]}"
    if st != "ok":
        return "crash_other", f"re-run status {st}"
    sol = parse_last_line(rr["stdout"])
    for cand in lenient_parses(rr["stdout"]):
        if eval_sol(r, cand) != "infeasible":
            return "output_format", f"another reading of stdout is {eval_sol(r, cand)}"
    if not sol:
        return ("no_solution" if rr["stdout"].strip() else "no_output"), rr["stdout"].strip()[-80:]
    ev = eval_sol(r, sol)
    if ev == "infeasible":
        return "infeasible_output", ""
    return "nonrepro", f"re-run gives a {ev} solution (stored status {r['status']})"


# ----------------------------------------------------------------------------------------------------------------------------------
# 5. label-free selection
# ----------------------------------------------------------------------------------------------------------------------------------
MR = ["translate", "rot90", "mirror", "permute", "scale", "big"]


def mr_out(code, task, x):
    _, stdin, _ = render(task, x)
    r = cached_run(code, stdin, timeout=10, wrap=False)
    return (r["stdout"].strip().split() or [None])[-1].lower() if r["status"] == "ok" and r["stdout"].strip() else None


def expected_rel(task, v, base):
    if base is None:
        return None
    if v == "scale" and task == "clip":
        try:
            x = Fraction(base) * 9
            return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"
        except (ValueError, ZeroDivisionError):
            return None
    if v == "scale" and task in ("area2", "close", "rectunion"):
        try:
            return str(int(base) * 9)
        except ValueError:
            return None
    return base


def mr_check(code, task, V):   # same relations as poc/run_geo_mr.py mr_check
    base = mr_out(code, task, V["identity"])
    ok = base is not None
    for v in MR:
        if task == "lattice" and v == "scale":
            continue
        if ok and mr_out(code, task, V[v]) != expected_rel(task, v, base):
            ok = False
    return base, ok


def mr_select(rows3, key):
    """poc/mr_select.py: candidates whose outputs satisfy every metamorphic relation on the GIVEN instance; majority vote on the
    identity output; pick the first candidate with the winning output. Returns the picked row or None."""
    task, n, i = key
    V = geo_variants(task, n, i)
    cands = []
    for r in rows3:
        if r is not None and r.get("code"):
            base, ok = mr_check(r["code"], task, V)
            if ok:
                cands.append((r, base))
    if not cands:
        return None
    vote = Counter(b for _, b in cands).most_common(1)[0][0]
    return next(r for r, b in cands if b == vote)


def best_of(rows3):
    feas = [r for r in rows3 if r is not None and r["feasible"] and r["value"] is not None]
    if not feas:
        return None
    return (max if feas[0]["prob"] == "knapsack" else min)(feas, key=lambda r: r["value"])


# ----------------------------------------------------------------------------------------------------------------------------------
# 6. main
# ----------------------------------------------------------------------------------------------------------------------------------
# Manual validation (2026-10-13): for every class, 8 programs drawn with random.Random(f"e1-{domain}-{class}") (all of them if fewer) were read
# together with their per-version results / re-run output / exception, and the label checked. [agree, read, note]
VALIDATION = {
    "geometry": {
        "no_code": [7, 7, "no program extracted; 2 are gpt-oss-120b runs from before the extractor fixes (possible extraction artifacts), older runs do not store finish/tokens so a token-cap hit cannot be excluded"],
        "runaway": [8, 8, "finish=length at the cap (gpt-oss-20b high effort, Qwen3 lattice)"],
        "syntax": [8, 8, "unclosed brackets, a fragment starting with an indented line"],
        "environment": [8, 8, "shapely/scipy/sympy not installed; `from fractions import gcd` (removed in Python 3.9)"],
        "packaging": [8, 8, "an offered helper (orient, dist2, point_in_polygon, segments_intersect) is called but never defined"],
        "interface": [8, 8, "segments_intersect with 8 scalars / 2 segments / 3 points; orient given ints (scalar coordinates) or a map object"],
        "input_format": [8, 8, "every line parsed as a point, so the count line `n` breaks it; correct once count lines are dropped"],
        "crash_other": [8, 8, "2 parsing index-arithmetic bugs (no layout fixes them), 3 empty-slab IndexErrors in a rectangle sweep, 3 other bugs"],
        "timeout": [8, 8, "re-run also > 10 s"],
        "no_output": [8, 8, "runs, prints nothing"],
        "crash_nonrepro": [1, 1, "harness flake: the stored crash does not reproduce"],
        "output_format": [8, 8, "8.0 for 8, False/inside for no/yes, 19750/32 for 9875/16"],
        "logic": [8, 8, "Manhattan length instead of gcd for boundary points, wrong ray-casting sign, negative union area, broken intersection parameter, collinear handling in Jarvis march"],
        "orientation": [8, 8, "keeps the left side of each clip edge without orienting B counter-clockwise (2 normalize via an area that is already abs(), so the check never fires); signed area without abs in Pick's formula"],
        "degenerate": [7, 8, "touching segments missed, duplicate points skipped, duplicate rectangle collapsed by a set; 1 is a wrong inclusion-exclusion that only the degenerate version exposes (really logic)"],
        "precision": [8, 8, "float accumulator `area = 0.0` with ~1e18 products, float parsing, float intersection points"],
        "variant_other": [8, 8, "latent edge cases exposed by a rotated/permuted copy: collinear ties in Jarvis/Graham, empty sweep slab, broken ray-casting formula"],
    },
    "co": {
        "no_code": [1, 1, "gpt-oss-120b run from before the extractor fixes"],
        "runaway": [8, 8, "finish=length (thinking runs, R1, gpt-oss medium)"],
        "syntax": [8, 8, "repair answers that are only an indented fragment; unclosed brackets"],
        "api": [8, 8, "Python function passed where a callback index is needed, Python `if` on a BoundedLinearExpression, invented modules/classes (routing_enhanced_pb2, AssignmentProblemManager, CpModel.Sum), AddDimension's bool used as a dimension"],
        "input_format": [8, 8, "header read as `n capacity K horizon` (service skipped, SERVICE_TIME hard-coded); optimal/feasible once the field is removed"],
        "output_format": [8, 8, "7 TSP tours printed with the closing return to city 0 (optimal tours), 1 CVRP printing one route per line"],
        "infeasible_model": [2, 8, "all raise CP Solver fail as defined, but 6 of 8 also misread the header and fail on a second error once the field is restored (zero slack in the time dimension, invalid search-parameter field)"],
        "no_solution": [7, 8, "the solver found nothing ('No solution found'); 1 prints the program's own validation message"],
        "infeasible_output": [8, 8, "bin capacity exceeded, knapsack over capacity, TSP printing only `0 0`"],
        "suboptimal": [8, 8, "feasible with gaps of 4-398% (colours/bins/makespan not minimised)"],
        "crash_other": [3, 8, "3 program bugs; but 2 API misconceptions (solver.Value used while building the model), 1 invented method (SetServiceTime) and 2 header misreads (3 fields; a strict 4-field check) that the rules cannot catch"],
        "timeout": [8, 8, "re-run also > 40 s (CP-SAT bin packing at 40 items)"],
        "no_output": [8, 8, "runs, prints nothing"],
    },
}


def markdown_tables(out, meta):
    """the tables of results/E1_TAXONOMY_DRAFT.md, regenerated from the same counts"""
    L = []
    gs = ["algorithmic", "packaging/interface", "input format", "output format", "API/environment", "generation", "other runtime"]
    cs = ["API/knowledge", "input format", "output format", "modelling/logic", "generation", "other runtime"]

    def mlab(m):
        return m["model"] + (f" ({m['effort']})" if m["effort"] else "")

    def block(dom, title, sel, cond_of, SUP, cols):
        grp = defaultdict(lambda: [0, 0, Counter()])
        order = []
        for t, m in meta.items():
            if m["domain"] != dom or not sel(m):
                continue
            k = (mlab(m), cond_of(m))
            if k not in grp:
                order.append(k)
            g = grp[k]
            g[0] += out["per_tag"][t]["n"]; g[1] += out["per_tag"][t]["failures"]
            for c_, n_ in out["per_tag"][t]["classes"].items():
                g[2][SUP[c_]] += n_
        L.append(f"\n**{title}** (failures = k of n programs; each class column = k of the failures)\n")
        L.append("| model | condition | failures | " + " | ".join(cols) + " |")
        L.append("|---|---|---|" + "---|" * len(cols))
        for k in order:
            n, f, sup = grp[k]
            L.append(f"| {k[0]} | {k[1]} | {f}/{n} | " + " | ".join((f"{sup[c_]} ({100 * sup[c_] / f:.0f}%)" if sup[c_] else "0") if f else "–"
                                                                for c_ in cols) + " |")

    def fam(m):
        if m["model"].startswith(("gpt-oss", "R1")):
            return "reasoning models (R1-Distill, gpt-oss)"
        return "Qwen3 +think" if m["think"] else ("Qwen3, no thinking" if m["model"].startswith("Qwen3") else "Llama")

    def family_block(dom, title, sel, SUP, cols):
        S, N, F, order = defaultdict(Counter), Counter(), Counter(), []
        for t, m in meta.items():
            if m["domain"] != dom or not sel(m):
                continue
            f = fam(m)
            if f not in order:
                order.append(f)
            N[f] += out["per_tag"][t]["n"]; F[f] += out["per_tag"][t]["failures"]
            for c_, n_ in out["per_tag"][t]["classes"].items():
                S[f][SUP[c_]] += n_
        L.append(f"\n**{title}** (failures = k of n programs; each class column = k of the failures)\n")
        L.append("| model family | failures | " + " | ".join(cols) + " |")
        L.append("|---|---|" + "---|" * len(cols))
        for f in order:
            L.append(f"| {f} | {F[f]:,}/{N[f]:,} | " + " | ".join((f"{S[f][c_]:,} ({100 * S[f][c_] / F[f]:.0f}%)" if S[f][c_] else "0") if F[f] else "–"
                                                                for c_ in cols) + " |")

    family_block("geometry", "Table 1a. Geometry, all runs in the manifest", lambda m: True, GEO_SUPER, gs)
    family_block("geometry", "Table 1b. Geometry, the F1 setting: 5 core tasks with a toolbox (K0 or K8), copy-in header",
                 lambda m: m.get("tasks") == "main5" and m["toolbox"] in ("K0", "K8") and m["head"] == "should" and not m["extra"], GEO_SUPER, gs)
    family_block("geometry", "Table 1c. Geometry, hard tasks (lattice, rectangle union, polygon clipping, hull with 2 misleading helpers)",
                 lambda m: m.get("tasks") in ("hard", "clip", "lattice", "hull"), GEO_SUPER, gs)
    family_block("co", "Table 1d. Optimization, all runs in the manifest", lambda m: True, CO_SUPER, cs)
    family_block("co", "Table 1e. Optimization without VRPTW", lambda m: m.get("probs") != "vrptw", CO_SUPER, cs)
    L.append("\n<!-- per-model tables -->")
    main_nothink = lambda m: m.get("tasks") == "main5" and not m["think"] and m["head"] == "should" and not m["extra"] and m["toolbox"] in ("K0", "K8")   # noqa: E731
    block("geometry", "Geometry, 5 core tasks, needed helpers only (K0) vs. 8 extra helpers (K8), copy-in header, no thinking (seeds pooled)",
          main_nothink, lambda m: m["toolbox"], GEO_SUPER, gs)
    block("geometry", "Geometry, same tasks with thinking (Qwen3, n = 100 per seed)",
          lambda m: m.get("tasks") == "main5" and m["think"], lambda m: m["toolbox"] + " +think", GEO_SUPER, gs)
    block("geometry", "Geometry, hard tasks (lattice + rectangle union) and polygon clipping, no toolbox, no hint",
          lambda m: m.get("tasks") in ("hard", "clip") and m["toolbox"] == "none" and not m["extra"],
          lambda m: m["tasks"] + (" +think" if m["think"] else ""), GEO_SUPER, gs)
    co_set = lambda m: "6 problems" if m.get("probs") in ("core4", "held2", "core4+held2") else m.get("probs")   # noqa: E731
    block("co", "Optimization, by documentation (seeds pooled; 6 problems = knapsack, TSP, colouring, scheduling, bin packing, vertex cover)",
          lambda m: not m["think"] and not m["extra"], lambda m: f"{co_set(m)}: {m['doc']}", CO_SUPER, cs)
    block("co", "Optimization with thinking or the literal input", lambda m: m["think"] or m["extra"],
          lambda m: f"{co_set(m)}: {m['doc']}{' ' + m['extra'] if m['extra'] else ''}{' +think' if m['think'] else ''}", CO_SUPER, cs)
    # class x fix
    for dom, CL in (("geometry", GEO_CLASSES), ("co", CO_CLASSES)):
        agg = {k.split(" | ", 1)[1]: v for k, v in out["class_x_fix"].items() if k.startswith(dom + " | ")}
        used = [c_ for c_ in CL if sum(v.get(c_, [0, 0])[1] for v in agg.values()) >= 10]
        L.append(f"\n**Class x fix, {dom}** (k/n = failures of that class in the 'before' condition whose instance is solved after the fix; all paired "
                 f"runs and models pooled; classes with < 10 paired failures in total omitted)\n")
        L.append("| fix | all classes | " + " | ".join(used) + " |")
        L.append("|---|---|" + "---|" * len(used))
        ctrl = [k for k in agg if k.startswith("control")]
        for f in ctrl + sorted(k for k in agg if not k.startswith("control")):
            v = agg[f]
            tot = [sum(x[0] for x in v.values()), sum(x[1] for x in v.values())]
            L.append(f"| {f} | {tot[0]}/{tot[1]} ({100 * tot[0] / max(tot[1], 1):.0f}%) | " +
                     " | ".join((f"{v[c_][0]}/{v[c_][1]}" if c_ in v else "–") for c_ in used) + " |")
    return "\n".join(L)


def pct(k, n):
    return f"{k}/{n} ({100 * k / n:.0f}%)" if n else "0/0"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--co_workers", type=int, default=6)
    ap.add_argument("--cache", default=os.path.join(tempfile.gettempdir(), "e1_rerun_cache.jsonl"))
    ap.add_argument("--samples", default="", help="directory for the validation samples (8 per class, seed 0)")
    ap.add_argument("--no_select", action="store_true", help="skip the label-free selection runs (geometry MR-select is the slowest part)")
    a = ap.parse_args()
    load_cache(a.cache)

    # ---- manifest
    M = build_manifest()
    have = {m["file"] for m in M if os.path.exists(os.path.join(RES, m["file"]))}
    missing = [m["tag"] for m in M if m["file"] not in have]
    M = [m for m in M if m["file"] in have]
    rows = {m["tag"]: [json.loads(l) for l in open(os.path.join(RES, m["file"]))] for m in M}
    for m in M:
        m["rows"] = len(rows[m["tag"]])
    allfiles = sorted(os.path.basename(p) for p in glob.glob(os.path.join(RES, "geocross_*.jsonl")) + glob.glob(os.path.join(RES, "co_*.jsonl")))
    used = {m["file"] for m in M}
    skipped = [f for f in allfiles if f not in used]
    zebra = sorted(os.path.basename(p) for p in glob.glob(os.path.join(RES, "zebra*")))
    manifest = {"about": "E1 manifest: result files used by poc/analyze_e1_taxonomy.py, each with the run flags taken from the queue script "
                         "that launched it (`source`, in poc/). seed = sampling seed; temperature/max_tokens as launched. Geometry "
                         "toolbox: none = no helpers, K0 = needed helpers only, K8 = needed + 8 related extra helpers; head prelude = "
                         "helpers pre-defined at execution. CO doc: none / full sheet / exact (problem-specific) snippet / near-miss "
                         "(the CVRP snippet on VRPTW).",
                "n_used": len(M), "n_result_files": len(allfiles), "n_skipped": len(skipped),
                "skipped_note": "out of scope for E1 headline conditions (other ablations: budgets, autoscope, RAG, E5 LoRA, paraphrases, "
                                "neutral header, pt/prims, size-mult, old pilot runs, superseded gpt-oss K8 extractor runs, S2_ runs in "
                                "progress on the new stack); zebra_* and results/archive ignored by design",
                "missing_tags": missing, "entries": M, "skipped_files": skipped, "zebra_files_ignored": len(zebra)}
    json.dump(manifest, open(os.path.join(RES, "e1_manifest.json"), "w"), indent=1)
    meta = {m["tag"]: m for m in M}
    print(f"manifest: {len(M)} files used ({sum(m['domain'] == 'geometry' for m in M)} geometry, {sum(m['domain'] == 'co' for m in M)} CO), "
          f"{len(skipped)} of {len(allfiles)} result files skipped, missing tags: {missing}")

    # ---- re-execution
    gjobs = [(t, i) for t, m in meta.items() if m["domain"] == "geometry" for i, r in enumerate(rows[t]) if geo_needs_rerun(r)]
    cjobs = [(t, i) for t, m in meta.items() if m["domain"] == "co" for i, r in enumerate(rows[t]) if co_needs_rerun(r)]
    vjobs = [(t, i) for t, m in meta.items() if m["domain"] == "co" for i, r in enumerate(rows[t])
             if r["prob"] == "vrptw" and not co_success(r) and r.get("code")]
    print(f"re-runs: geometry identity {len(gjobs)}, CO final programs {len(cjobs)}, VRPTW counterfactual {len(vjobs)}", flush=True)
    # harness check: instances rebuilt today must reproduce stored successes (first correct program of every file; geometry all 8 variants)
    def recon(t):
        m = meta[t]
        r = next((r for r in rows[t] if (r["class"] == "correct_all" if m["domain"] == "geometry" else co_success(r)) and r.get("code")), None)
        if r is None:
            return t, None
        if m["domain"] == "geometry":
            V = geo_variants(r["task"], r["n"], r["inst"])
            pre = prelude_src(m, r)
            ok = all((lambda o: o["status"] == "ok" and o["stdout"].split() and o["stdout"].split()[-1].lower() == answer(r["task"], x))(
                cached_run(pre + r["code"], render(r["task"], x)[1], timeout=10, wrap=False)) for x in V.values())
            return t, bool(ok)
        rr = co_rerun(r)
        return t, rr["status"] == "ok" and eval_sol(r, parse_last_line(rr["stdout"])) != "infeasible"
    with ThreadPoolExecutor(a.co_workers) as ex:
        rc = dict(ex.map(recon, list(meta)))
    bad_recon = [t for t, v in rc.items() if v is False]
    print(f"reconstruction check: {sum(v is True for v in rc.values())} files reproduce a stored success, failed: {bad_recon}", flush=True)
    GR, CR, CF = {}, {}, {}
    GF = {}
    with ThreadPoolExecutor(a.workers) as ex:
        for (t, i), rr in zip(gjobs, ex.map(lambda j: geo_rerun(meta[j[0]], rows[j[0]][j[1]]), gjobs)):
            GR[(t, i)] = rr
        for (t, i), f in zip(gjobs, ex.map(lambda j: geo_format_cf(meta[j[0]], rows[j[0]][j[1]]), gjobs)):
            GF[(t, i)] = f
    with ThreadPoolExecutor(a.co_workers) as ex:
        for (t, i), rr in zip(cjobs, ex.map(lambda j: co_rerun(rows[j[0]][j[1]]), cjobs)):
            CR[(t, i)] = rr
        for (t, i), rr in zip(vjobs, ex.map(lambda j: co_rerun(rows[j[0]][j[1]], vrptw_cf_stdin(rows[j[0]][j[1]])), vjobs)):
            sol = parse_last_line(rr["stdout"]) if rr["status"] == "ok" else None
            CF[(t, i)] = eval_sol(rows[t][i], sol)

    # ---- classify
    LAB = {}
    repro = Counter()
    for t, m in meta.items():
        for i, r in enumerate(rows[t]):
            if m["domain"] == "geometry":
                rr = GR.get((t, i))
                if rr is not None:   # reproduction of the stored identity result
                    if r["per_variant"]["identity"] is None:
                        repro["geo_crash_reproduced" if (rr["status"] != "ok" or not rr["stdout"].strip()) else "geo_crash_not_reproduced"] += 1
                    else:
                        toks = rr["stdout"].strip().split()
                        same = rr["status"] == "ok" and toks and toks[-1].lower() != answer(r["task"], geo_variants(r["task"], r["n"], r["inst"])["identity"])
                        repro["geo_wrong_reproduced" if same else "geo_wrong_not_reproduced"] += 1
                LAB[(t, i)] = classify_geo(m, r, rr, GF.get((t, i)))
            else:
                rr = CR.get((t, i))
                if rr is not None:
                    st_now = rr["status"] if rr["status"] != "ok" else ("ok" if parse_last_line(rr["stdout"]) else "no_output")
                    repro[f"co_{'reproduced' if st_now == r['status'] else 'not_reproduced'}"] += 1
                LAB[(t, i)] = classify_co(m, r, rr, CF.get((t, i)))

    # ---- per-tag counts
    per_tag = {}
    for t, m in meta.items():
        lab = [LAB[(t, i)] for i in range(len(rows[t]))]
        cl = Counter(l[0] for l in lab if l)
        per_tag[t] = {"domain": m["domain"], "model": m["model"], "effort": m["effort"], "condition": m["condition"], "seed": m["seed"],
                      "n": len(lab), "failures": sum(cl.values()), "classes": dict(cl)}

    def mlabel(m):
        return m["model"] + (f" ({m['effort']})" if m["effort"] else "")

    out = {"about": "E1 failure taxonomy; classes and rules in results/E1_TAXONOMY_DRAFT.md and poc/analyze_e1_taxonomy.py",
           "geo_classes": GEO_CLASSES, "co_classes": CO_CLASSES, "geo_super": GEO_SUPER, "co_super": CO_SUPER, "per_tag": per_tag,
           "reproduction": dict(repro), "reconstruction_check": {"reproduced": sum(v is True for v in rc.values()), "failed": bad_recon}}

    # ---- table 1: share of failures by class per model x condition (seeds pooled)
    for dom, CL, SUP in (("geometry", GEO_CLASSES, GEO_SUPER), ("co", CO_CLASSES, CO_SUPER)):
        grp = defaultdict(lambda: [0, 0, Counter()])
        for t, m in meta.items():
            if m["domain"] != dom:
                continue
            g = grp[(mlabel(m), m["condition"])]
            g[0] += per_tag[t]["n"]; g[1] += per_tag[t]["failures"]; g[2].update(per_tag[t]["classes"])
        out[f"{dom}_by_model_condition"] = {f"{k[0]} | {k[1]}": {"programs": v[0], "failures": v[1], "classes": dict(v[2])} for k, v in grp.items()}
        print(f"\n=== {dom}: failures by class, per model x condition (seeds pooled; k of failures) ===")
        for (ml, cond), (n, f, cl) in sorted(grp.items()):
            sup = Counter()
            for c_, k in cl.items():
                sup[SUP[c_]] += k
            print(f"{ml:28s} | {cond:42s} | fail {f:4d}/{n:4d} | " + ", ".join(f"{c_} {cl[c_]}" for c_ in CL if cl.get(c_)) +
                  " || " + ", ".join(f"{s} {k}" for s, k in sup.most_common()))
        # family x domain summary of super-classes
        fam = defaultdict(Counter)
        for t, m in meta.items():
            if m["domain"] != dom:
                continue
            key = ("reasoning (R1 / gpt-oss)" if m["model"].startswith(("gpt-oss", "R1")) else
                   ("Qwen3 +think" if m["think"] else ("Qwen3" if m["model"].startswith("Qwen3") else "Llama")))
            for c_, k in per_tag[t]["classes"].items():
                fam[key][SUP[c_]] += k
                fam[key]["_total"] += k
        out[f"{dom}_super_by_family"] = {k: dict(v) for k, v in fam.items()}
        print(f"--- {dom}: super-classes per model family (all conditions pooled) ---")
        for k, v in fam.items():
            tot = v["_total"]
            print(f"  {k:26s} failures {tot:5d}: " + ", ".join(f"{s} {pct(n_, tot)}" for s, n_ in v.most_common() if s != "_total"))

    # ---- table 2: class x fix transitions
    def key_of(dom, r):
        return inst_key(r) if dom == "geometry" else r["key"]

    def success(dom, r):
        return r["class"] == "correct_all" if dom == "geometry" else co_success(r)

    trans = []
    for fix, dom, b, af, flt in fix_pairs():
        if b not in rows or af not in rows:
            continue
        A = {key_of(dom, r): r for r in rows[af]}
        by = defaultdict(lambda: [0, 0])
        new_fail, paired = 0, 0
        for i, r in enumerate(rows[b]):
            if flt and not flt(r):
                continue
            k = key_of(dom, r)
            if k not in A:
                continue
            paired += 1
            lab = LAB[(b, i)]
            if lab is None:
                new_fail += not success(dom, A[k])
                continue
            by[lab[0]][1] += 1
            by[lab[0]][0] += success(dom, A[k])
        trans.append({"fix": fix, "domain": dom, "before": b, "after": af, "model": mlabel(meta[b]), "paired": paired,
                      "by_class": {c_: v for c_, v in by.items()}, "before_correct_now_wrong": new_fail})
    # label-free selection over 3 seeds
    if not a.no_select:
        for dom, tags in select_groups():
            if not all(t in rows for t in tags):
                continue
            idx = [{key_of(dom, r): r for r in rows[t]} for t in tags]
            keys = [key_of(dom, r) for r in rows[tags[0]]]
            if dom == "geometry":
                with ThreadPoolExecutor(a.workers) as ex:
                    picks = list(ex.map(lambda k: mr_select([d.get(k) for d in idx], k), keys))
            else:
                picks = [best_of([d.get(k) for d in idx]) for k in keys]
            by = defaultdict(lambda: [0, 0])
            new_fail = 0
            for i, (k, p) in enumerate(zip(keys, picks)):
                lab = LAB[(tags[0], i)]
                ok = p is not None and success(dom, p)
                if lab is None:
                    new_fail += not ok
                    continue
                by[lab[0]][1] += 1
                by[lab[0]][0] += ok
            fixname = "label-free selection over 3 seeds (" + ("metamorphic check, MR-select" if dom == "geometry" else "feasible + best objective") + ")"
            trans.append({"fix": fixname, "domain": dom, "before": tags[0], "after": "+".join(tags), "model": mlabel(meta[tags[0]]),
                          "paired": len(keys), "by_class": dict(by), "before_correct_now_wrong": new_fail})
            print(f"  selected {tags[0]} (+2 seeds): {sum(v[0] for v in by.values())} of {sum(v[1] for v in by.values())} failures rescued", flush=True)
    out["fix_transitions"] = trans
    # aggregated class x fix
    agg = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for tr in trans:
        for c_, (k, n) in tr["by_class"].items():
            agg[(tr["domain"], tr["fix"])][c_][0] += k
            agg[(tr["domain"], tr["fix"])][c_][1] += n
    out["class_x_fix"] = {f"{d} | {f}": {c_: v for c_, v in cl.items()} for (d, f), cl in agg.items()}
    for dom, CL in (("geometry", GEO_CLASSES), ("co", CO_CLASSES)):
        print(f"\n=== {dom}: class x fix (failures of the 'before' condition that are correct after the fix; pooled over models/pairs) ===")
        for (d, f), cl in sorted(agg.items()):
            if d != dom:
                continue
            tot = [sum(v[0] for v in cl.values()), sum(v[1] for v in cl.values())]
            print(f"{f:58s} all {pct(*tot):>14s} | " + ", ".join(f"{c_} {cl[c_][0]}/{cl[c_][1]}" for c_ in CL if c_ in cl))
        print(f"--- {dom}: per pair ---")
        for tr in trans:
            if tr["domain"] != dom:
                continue
            tot = [sum(v[0] for v in tr["by_class"].values()), sum(v[1] for v in tr["by_class"].values())]
            print(f"  {tr['fix'][:40]:40s} {tr['before']:30s} -> {tr['after'][:34]:34s} paired {tr['paired']:4d} rescued {pct(*tot):>13s} "
                  f"(+{tr['before_correct_now_wrong']} newly wrong) | " + ", ".join(f"{c_} {v[0]}/{v[1]}" for c_, v in sorted(tr["by_class"].items())))

    # ---- packaging: is the uncopied helper the only problem? (same program, helpers pre-defined, all 8 versions)
    pk = [(t, i) for (t, i), lab in LAB.items() if lab and lab[0] == "packaging"]
    with ThreadPoolExecutor(a.workers) as ex:
        pkr = list(ex.map(lambda j: geo_packaging_cf(meta[j[0]], rows[j[0]][j[1]]), pk))
    for (t, i), ok in zip(pk, pkr):
        LAB[(t, i)] = ("packaging", LAB[(t, i)][1] + ("; correct on all 8 once the helpers are defined" if ok else "; still wrong with the helpers defined"))
    pkm = defaultdict(lambda: [0, 0])
    for (t, i), ok in zip(pk, pkr):
        pkm[mlabel(meta[t])][0] += ok; pkm[mlabel(meta[t])][1] += 1
    out["packaging_counterfactual"] = {"correct_once_helpers_defined": sum(pkr), "packaging_failures": len(pkr), "by_model": dict(pkm)}
    print(f"packaging failures correct on all 8 versions once the offered helpers are pre-defined: {sum(pkr)}/{len(pkr)}", dict(pkm))

    # ---- what is inside "other crash": exception types, and (geometry) programs that get past the crash in another input layout
    for dom, RR in (("geometry", GR), ("co", CR)):
        ct = Counter()
        for (t, i), lab in LAB.items():
            if lab and lab[0] == "crash_other" and meta[t]["domain"] == dom and RR.get((t, i)) and RR[(t, i)]["exc"]:
                ct[RR[(t, i)]["exc"]["type"]] += 1
        out[f"{dom}_crash_other_types"] = dict(ct.most_common())
        print(f"{dom} other-crash exception types:", dict(ct.most_common(12)))
    past = Counter()
    for (t, i), lab in LAB.items():
        if lab and lab[0] == "crash_other" and meta[t]["domain"] == "geometry":
            r = rows[t][i]
            stdin = render(r["task"], geo_variants(r["task"], r["n"], r["inst"])["identity"])[1]
            src = prelude_src(meta[t], r) + r["code"]
            ok = [n_ for n_, f in GEO_LAYOUTS.items() if (lambda o: o["status"] == "ok" and o["stdout"].strip())(
                cached_run(src, f(stdin), timeout=10, wrap=False))]
            past[ok[0] if ok else "crashes in every layout"] += 1
    out["geometry_crash_other_layouts"] = dict(past)
    print("geometry other crashes that run to completion when the input is given in another layout:", dict(past))

    # ---- VRPTW counterfactual summary
    cf_sum = defaultdict(Counter)
    for (t, i), v in CF.items():
        cf_sum[t][v] += 1
    out["vrptw_counterfactual"] = {t: dict(v) for t, v in cf_sum.items()}
    print("\n=== VRPTW input-format counterfactual (failing programs re-run with the service field removed from the header) ===")
    for t, v in sorted(cf_sum.items()):
        print(f"  {t:34s} failing {sum(v.values()):3d}: optimal {v['optimal']}, feasible {v['feasible']}, still infeasible/crash {v['infeasible']}")
    print("\nreproduction of stored failures on re-run:", dict(repro))

    # ---- details per failing program (for drill-down) and validation samples
    out["labels"] = {t: {str(i): list(LAB[(t, i)]) for i in range(len(rows[t])) if LAB[(t, i)]} for t in meta}
    out["validation_manual"] = {d: {c_: {"agree": v[0], "read": v[1], "note": v[2]} for c_, v in cl.items()} for d, cl in VALIDATION.items()}
    for d, cl in VALIDATION.items():
        print(f"manual validation {d}: {sum(v[0] for v in cl.values())}/{sum(v[1] for v in cl.values())} sampled labels confirmed")
    md = markdown_tables(out, meta)
    out["markdown_tables"] = md
    print("\n=== markdown tables (results/E1_TAXONOMY_DRAFT.md) ===\n" + md)
    json.dump(out, open(os.path.join(RES, "e1_taxonomy.json"), "w"), indent=0)
    if a.samples:
        os.makedirs(a.samples, exist_ok=True)
        byc = defaultdict(list)
        for (t, i), lab in LAB.items():
            if lab:
                byc[(meta[t]["domain"], lab[0])].append((t, i))
        for (dom, c_), lst in sorted(byc.items()):
            pick = random.Random(f"e1-{dom}-{c_}").sample(sorted(lst), min(8, len(lst)))   # fixed seed per class
            with open(os.path.join(a.samples, f"{dom}_{c_}.txt"), "w") as f:
                for t, i in pick:
                    r = rows[t][i]
                    rr = GR.get((t, i)) if dom == "geometry" else CR.get((t, i))
                    f.write(f"########## {t} row {i} | {meta[t]['model']} | {meta[t]['condition']} | class {c_} | detail {LAB[(t, i)][1]}\n")
                    if dom == "geometry":
                        f.write(f"task {r['task']} n {r['n']} inst {r['inst']} per_variant {r['per_variant']} offered {sorted(offered_helpers(meta[t], r))} "
                                f"finish {r.get('finish')} out_tokens {r.get('out_tokens')}\n")
                    else:
                        f.write(f"key {r['key']} status {r['status']} feasible {r['feasible']} value {r['value']} ref {r['ref']} gap {r['gap']} "
                                f"finish {r.get('finish')} rounds {r.get('repair_rounds')}\nstored err: {(r.get('err') or '')[-300:]!r}\n"
                                f"VRPTW counterfactual: {CF.get((t, i))}\n")
                    if rr:
                        f.write(f"re-run: status {rr['status']} stdout {rr['stdout'][-300:]!r}\nexc {json.dumps(rr['exc'])[:900]}\n")
                    f.write("----- code -----\n" + (r.get("code") or "(none)") + "\n\n")
        print(f"validation samples written to {a.samples}")


if __name__ == "__main__":
    main()
