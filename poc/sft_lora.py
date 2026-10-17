"""E5: LoRA SFT of Qwen3-8B (no thinking) on oracle-verified programs written by Qwen3-8B WITH thinking on training instances.
Each example: user = the exact harness prompt (saved by run_geo_cross --save_prompt), assistant = "```python\n<program>\n```", formatted with the
Qwen3 chat template and enable_thinking=False (empty think block), loss on the assistant tokens only. The LoRA is merged into the base weights
and saved as a full model directory that vLLM can serve.
usage (old server: /opt/conda/bin/python with PYTHONPATH=/dev/shm/pylib_vllm; server 2: /opt/conda/bin/python as is):
  sft_lora.py <out_dir> <arm: mixed|clean> [n_examples=600] [epochs=2]"""
import json, os, random, sys, time
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model

BASE = "/SSD/huggingface/Qwen/Qwen3-8B"
RES = "/NAS/SJ/POSTECH/nlp/results"
out_dir, arm = sys.argv[1], sys.argv[2]
N = int(sys.argv[3]) if len(sys.argv) > 3 else 600
EPOCHS = int(sys.argv[4]) if len(sys.argv) > 4 else 2
EXCLUDE = sys.argv[5] if len(sys.argv) > 5 else ""   # leave-one-task-out: drop this task from the training data
SEED = int(os.environ.get("E4_SEED", "0"))   # training-seed replication: example sampling, data order and LoRA init
rng = random.Random(SEED)
torch.manual_seed(SEED) if SEED else None


EXTRA_DATA = os.environ.get("E5_EXTRA", "")   # E5c: comma list of extra training-data tags per K (e.g. "T_geox8b_train2_k{k}_think")


def load(k):
    rows = [json.loads(l) for l in open(f"{RES}/geocross_T_geox8b_train_k{k}_think.jsonl")]
    for tag in filter(None, EXTRA_DATA.split(",")):
        rows += [json.loads(l) for l in open(f"{RES}/geocross_{tag.format(k=k)}.jsonl")]
    return [r for r in rows if r["class"] == "correct_all" and r.get("code") and r.get("prompt") and r["task"] != EXCLUDE]


pools = {k: load(k) for k in (0, 4, 8)} if not os.environ.get("E4_DATA") else {0: [], 4: [], 8: []}
print({k: len(v) for k, v in pools.items()}, "verified programs per K", flush=True)
if arm == "clean":
    data = rng.sample(pools[0], min(N, len(pools[0])))
else:   # equal thirds from K0 / K4 / K8
    per = N // 3
    data = sum((rng.sample(pools[k], min(per, len(pools[k]))) for k in (0, 4, 8)), [])
if os.environ.get("E4_DATA"):   # B2: train on a prepared (prompt, code) file instead of the teacher pools (SDFT rewrites, self-SFT)
    data = [json.loads(l) for l in open(os.environ["E4_DATA"])]
    print(f"B2 data: {len(data)} examples from {os.environ['E4_DATA']}", flush=True)
REPLAY = os.environ.get("E4_REPLAY", "")   # E4: extra (prompt, code) examples appended AFTER the main sampling (main selection unchanged)
if REPLAY:
    rep = [json.loads(l) for l in open(REPLAY)]
    print(f"E4 replay: +{len(rep)} examples from {REPLAY}", flush=True)
    data += rep
rng.shuffle(data)
print(f"arm={arm}: {len(data)} examples; tasks", {t: sum(r['task'] == t for r in data) for t in sorted({r['task'] for r in data})}, flush=True)

tok = AutoTokenizer.from_pretrained(BASE)
def encode(r):
    msgs = [{"role": "user", "content": r["prompt"]}]
    prompt_ids = tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, enable_thinking=False)
    ans = r["answer"] if r.get("answer") else "```python\n" + r["code"].strip() + "\n```"   # D1b: full answer text (explanation + code)
    full = tok.apply_chat_template(msgs + [{"role": "assistant", "content": ans}],
                                   tokenize=True, enable_thinking=False)
    if hasattr(prompt_ids, "input_ids"):
        prompt_ids, full = prompt_ids["input_ids"], full["input_ids"]
    if full[:len(prompt_ids)] != prompt_ids:   # the template may render the assistant turn differently; align by prefix length anyway
        print("warning: prompt/full prefix mismatch", flush=True)
    labels = [-100] * len(prompt_ids) + full[len(prompt_ids):]
    return full[:4096], labels[:4096]
enc = [encode(r) for r in data]
print("mean tokens", sum(len(a) for a, _ in enc) / len(enc), "max", max(len(a) for a, _ in enc), flush=True)
# show one rendered example (sanity: empty think block, assistant code)
print(tok.decode(enc[0][0])[-600:], flush=True)

model = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.bfloat16, device_map={"": 0}, attn_implementation="sdpa")
model.gradient_checkpointing_enable()
model.enable_input_require_grads()
R_ = int(os.environ.get("E5_R", "16"))
model = get_peft_model(model, LoraConfig(r=R_, lora_alpha=2 * R_, lora_dropout=0.05, task_type="CAUSAL_LM",
                                         target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]))
model.print_trainable_parameters()
opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=float(os.environ.get("E5_LR", "1e-4")), weight_decay=0.0)
ACC = 8   # effective batch 8 (one sequence per micro-step: no padding needed)
total = EPOCHS * len(enc) // ACC
sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / 10) * max(0.0, 1 - s / max(1, total)))
model.train(); step = 0; t0 = time.time()
for ep in range(EPOCHS):
    order = list(range(len(enc))); rng.shuffle(order); run = 0.0
    for j, idx in enumerate(order):
        ids, lab = enc[idx]
        out = model(input_ids=torch.tensor([ids], device="cuda"), labels=torch.tensor([lab], device="cuda"))
        (out.loss / ACC).backward(); run += out.loss.item()
        if (j + 1) % ACC == 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sched.step(); opt.zero_grad(); step += 1
            if step % 10 == 0:
                print(f"epoch {ep} step {step}/{total} loss {run / ACC:.4f} ({time.time() - t0:.0f}s)", flush=True)
            run = 0.0
model = model.merge_and_unload()
model.save_pretrained(out_dir, safe_serialization=True)
tok.save_pretrained(out_dir)
for f in ("generation_config.json",):
    src = os.path.join(BASE, f)
    if os.path.exists(src):
        open(os.path.join(out_dir, f), "w").write(open(src).read())
print("saved", out_dir, f"{time.time() - t0:.0f}s", flush=True)
