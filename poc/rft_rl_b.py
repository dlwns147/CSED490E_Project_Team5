"""RFT-R driver, second chain (2026-11-27 06:0x UTC; a copy of poc/rft_rl.py, which is in use): RL_DIR, RL_ROWS and RL_SEED choose the output folder, the rollout log and the instance order / attempt seeds, so a second independent chain runs on the other GPU.
RFT-R driver (PREREG_DIFF, 2026-11-27): on-policy reinforcement learning of gpt-oss-20b (LoRA) with the MathConstruct checker as reward, on the
training problems only; one GPU alternates between serving the current policy (vLLM, base MXFP4 + adapter) and one policy-gradient step
(poc/rft_rl_step.py). Pool: the training instances the base did not solve 4 of 4 times (its RFT-C rollouts), i.e. where a reward signal exists.
Per iteration: B instances × G attempts (OWN-E recipe, rft_gen.solve), a rollout deadline, then the update. Ends after N iterations or at RL_UNTIL (epoch s).
usage: python rft_rl.py <gpu> <port> [N]  -> results/rft/rl/adapter_<it>/, results/x44/rft_rl_rollouts.jsonl (no token ids), results/rft/rl/log.txt
Temporary files: each iteration's batch file (token ids) is deleted after its update; adapters of iterations other than the last two are deleted."""
import json, os, random, subprocess, sys, time, zlib, collections, shutil
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
GPU, PORT = sys.argv[1], sys.argv[2]; N = int(sys.argv[3]) if len(sys.argv) > 3 else 12
os.environ["POC_BASE_URL"] = f"http://127.0.0.1:{PORT}/v1"
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); ROOT = os.path.dirname(HERE)
import rft_gen as RG
B, G, DEAD = int(os.environ.get("RL_B", 32)), int(os.environ.get("RL_G", 4)), int(os.environ.get("RL_DEADLINE", 900)); UNTIL = float(os.environ.get("RL_UNTIL", 1e18))
D = f"{ROOT}/results/rft/" + os.environ.get("RL_DIR", "rl_b"); SEED = int(os.environ.get("RL_SEED", 1)); os.makedirs(D, exist_ok=True); LOG = open(f"{D}/log.txt", "a")
log = lambda s: (LOG.write(s + "\n"), LOG.flush(), print(s, flush=True))


def server(adapter):
    extra = ["--max-model-len", "65536"] + (["--enable-lora", "--max-lora-rank", "32", "--lora-modules", f"pol={adapter}"] if adapter else [])
    pid = subprocess.run(["bash", "poc/start_server.sh", "/SSD/huggingface/openai/gpt-oss-20b", PORT, GPU, "0.92", f"rlb{GPU}"] + extra, cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if not pid.isdigit():
        raise RuntimeError("server did not start")
    return int(pid)


def stop(pid):
    try:
        os.kill(pid, 15)          # the server's own PID only (it shares our process group: never killpg)
    except Exception:
        pass
    for _ in range(60):
        used = subprocess.run(["nvidia-smi", "-i", GPU, "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout.strip()
        if used.isdigit() and int(used) < 2000:
            return
        time.sleep(5)


def main():
    P = {p["id"]: p for p in RG.problems("train")}
    base = collections.defaultdict(list)
    for l in open(f"{ROOT}/results/x44/rft_base_train_s1.jsonl"):
        z = json.loads(l); base[z["id"]].append(bool(z["correct"]))
    pool = sorted(k for k, v in base.items() if sum(v) < len(v) and k in P); rng = random.Random(SEED); order = []
    log(f"{time.strftime('%F %T', time.gmtime())} start: pool {len(pool)} instances of {len({k.split('__')[0] for k in pool})} problems; B {B} G {G} deadline {DEAD}s N {N}")
    adapter = None
    for it in range(N):
        if time.time() > UNTIL:
            log("stop: time budget"); break
        if len(order) < B:
            order += rng.sample(pool, len(pool))
        batch, order = order[:B], order[B:]
        pid = server(adapter); os.environ["RFT_MODEL"] = "pol" if adapter else "local"; t0 = time.time(); rows = []
        jobs = [(P[k], g) for k in batch for g in range(G)]
        ex = ThreadPoolExecutor(64)
        def one(pg):
            p, g = pg
            s = 100000 * (1 + SEED) + it * 1000 + g * 97 + zlib.crc32(p["id"].encode()) % 89
            z = RG.solve(p["problem"], "medium", s); z.update(id=p["id"], seed=s, it=it, **RG.grade(p, z["final"])); return z
        fs = {ex.submit(one, j) for j in jobs}; end = t0 + DEAD
        while fs and time.time() < end:
            done, fs = wait(fs, timeout=max(1, end - time.time()), return_when=FIRST_COMPLETED)
            for f in done:
                try:
                    rows.append(f.result())
                except Exception:
                    pass
        ex.shutdown(wait=False, cancel_futures=True); stop(pid); t1 = time.time()
        bf = f"{D}/batch_{it}.jsonl"
        with open(bf, "w") as f:
            f.writelines(json.dumps(z) + "\n" for z in rows)
        with open(f"{ROOT}/results/x44/" + os.environ.get("RL_ROWS", "rft_rlb_rollouts.jsonl"), "a") as f:
            f.writelines(json.dumps({k: v for k, v in z.items() if k not in ("ids", "mask")}) + "\n" for z in rows)
        out = f"{D}/adapter_{it}"
        r = subprocess.run(["/opt/conda/bin/python", "poc/rft_rl_step.py", bf, adapter or "none", out], cwd=ROOT, env={**os.environ, "CUDA_VISIBLE_DEVICES": GPU}, capture_output=True, text=True)
        os.remove(bf)
        step = [l for l in (r.stdout or "").splitlines() if l.startswith(("batch", "step done"))]
        log(f"{time.strftime('%F %T', time.gmtime())} it {it}: {len(rows)} of {len(jobs)} attempts by the deadline ({t1-t0:.0f}s), right {sum(z['correct'] for z in rows)}, "
            f"ktok {sum(z['out_tokens'] for z in rows)/max(1,len(rows))/1000:.2f}; update rc {r.returncode} {' | '.join(step)} ({time.time()-t1:.0f}s)")
        if r.returncode != 0 or not os.path.exists(f"{out}/adapter_model.safetensors"):
            log("update failed: " + (r.stderr or "")[-800:]); break
        old = f"{D}/adapter_{it-2}"
        if it >= 2 and os.path.exists(old):
            shutil.rmtree(old)
        adapter = out
    if adapter:
        shutil.copytree(adapter, f"{D}/adapter_final", dirs_exist_ok=True)
    log(f"{time.strftime('%F %T', time.gmtime())} end; final adapter {adapter}")


if __name__ == "__main__":
    main()
