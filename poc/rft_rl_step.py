"""RFT-R policy-gradient step (PREREG_DIFF, 2026-11-27): one update of the LoRA policy from a batch of on-policy attempts with group-relative advantages
(GRPO's advantage, 2402.03300, without the ratio clip: each trace is used once, in one of MB minibatch steps = REINFORCE with a group baseline). Reward r = 1[right] − 0.005·ktok
(our utility divided by 100). Loss = −Σ_i A_i · mean over the generated tokens of trace i of log π(token) (first MAXLEN tokens of each trace).
usage: python rft_rl_step.py <batch.jsonl> <adapter_in|none> <adapter_out>"""
import json, os, sys, time, collections
import torch
MAXLEN = int(os.environ.get("RL_MAXLEN", 8192)); LR = float(os.environ.get("RL_LR", 5e-5)); MB = int(os.environ.get("RL_MB", 2)); MODEL = os.environ.get("RFT_BASE", "/SSD/huggingface/openai/gpt-oss-20b")


def main(batch, ain, aout):
    from transformers import AutoModelForCausalLM, Mxfp4Config
    from peft import LoraConfig, get_peft_model, PeftModel
    Z = [json.loads(l) for l in open(batch)]; G = collections.defaultdict(list)
    for z in Z:
        if z.get("ids"):
            z["r"] = float(bool(z["correct"])) - 0.005 * z["out_tokens"] / 1000; G[z["id"]].append(z)
    items = []
    for k, v in G.items():
        if len(v) < 2:
            continue
        m = sum(z["r"] for z in v) / len(v); s = (sum((z["r"] - m) ** 2 for z in v) / len(v)) ** 0.5
        if s < 1e-6:
            continue
        items += [(z, (z["r"] - m) / (s + 1e-4)) for z in v]
    print(f"batch {len(Z)} attempts, {len(G)} groups, {len(items)} traces with nonzero advantage; right {sum(bool(z['correct']) for z in Z)}", flush=True)
    model = AutoModelForCausalLM.from_pretrained(MODEL, quantization_config=Mxfp4Config(dequantize=True), dtype=torch.bfloat16, device_map="cuda:0", attn_implementation="eager", use_cache=False)
    model.gradient_checkpointing_enable(); model.enable_input_require_grads()
    if ain != "none":
        model = PeftModel.from_pretrained(model, ain, is_trainable=True)
    else:
        model = get_peft_model(model, LoraConfig(r=32, lora_alpha=64, lora_dropout=0.0, target_modules=["q_proj", "k_proj", "v_proj", "o_proj"], task_type="CAUSAL_LM"))
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=LR, weight_decay=0.0); model.train(); t0 = time.time(); ntok = 0
    import random
    random.Random(len(items)).shuffle(items); per = max(1, -(-len(items) // MB))
    for j, (z, a) in enumerate(items):
        ids = z["ids"][:MAXLEN]; mk = torch.tensor(z["mask"][:MAXLEN][1:], device="cuda:0", dtype=torch.bool)
        if mk.sum() == 0:
            continue
        x = torch.tensor([ids], device="cuda:0"); logits = model(input_ids=x).logits[0, :-1]
        sel = logits[mk].float(); tgt = x[0, 1:][mk]
        lp = -torch.nn.functional.cross_entropy(sel, tgt, reduction="mean")
        (-(a / per) * lp).backward(); ntok += len(ids)
        del logits, sel
        if (j + 1) % per == 0 or j == len(items) - 1:          # MB optimizer steps per batch (two passes of PPO-style reuse would need the ratio; here each trace is used once)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); opt.zero_grad()
    os.makedirs(aout, exist_ok=True); model.save_pretrained(aout)
    print(f"step done: {len(items)} traces, {ntok} tokens, {time.time()-t0:.0f}s, peak {torch.cuda.max_memory_allocated()/2**30:.1f} GiB", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:4])
