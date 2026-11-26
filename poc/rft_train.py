"""RFT-C training (PREREG_DIFF, 2026-11-26): LoRA supervised fine-tuning of gpt-oss-20b on its own RIGHT OWN-E attempts on training-problem instances
(rejection-sampling fine-tuning / expert iteration: STaR 2203.14465, RFT 2308.01825, ReST-EM 2312.06585). Loss on model-generated tokens only (mask).
Per instance at most two traces, the shortest right ones (utility prices tokens), each at most MAXLEN tokens (eager attention with sinks is quadratic).
usage: python rft_train.py <rows.jsonl> <out_dir> [--smoke]   (one GPU; out_dir gets the adapter and, with MERGE=1, a merged bf16 checkpoint for vLLM)
Temporary files: none besides out_dir; the merged checkpoint (~40 GB) is deleted by the lane script after evaluation."""
import json, os, sys, time, random, collections
import torch
MAXLEN = int(os.environ.get("RFT_MAXLEN", 8192)); PER = int(os.environ.get("RFT_PER", 2)); EPOCHS = float(os.environ.get("RFT_EPOCHS", 2)); LR = float(os.environ.get("RFT_LR", 1e-4)); ACC = int(os.environ.get("RFT_ACC", 16))
MODEL = os.environ.get("RFT_BASE", "/SSD/huggingface/openai/gpt-oss-20b")


def data(path):
    by = collections.defaultdict(list)
    for l in open(path):
        z = json.loads(l)
        if z.get("correct") and z.get("ids") and len(z["ids"]) <= MAXLEN:
            by[z["id"]].append(z)
    out = []
    for k, v in by.items():
        out += sorted(v, key=lambda z: z["out_tokens"])[:PER]
    return out


def main(path, out, smoke=False):
    from transformers import AutoModelForCausalLM, Mxfp4Config
    from peft import LoraConfig, get_peft_model
    D = data(path); random.Random(0).shuffle(D)
    print(f"traces {len(D)} from {len({z['id'] for z in D})} instances; tokens {sum(len(z['ids']) for z in D)}, trained {sum(sum(z['mask']) for z in D)}", flush=True)
    model = AutoModelForCausalLM.from_pretrained(MODEL, quantization_config=Mxfp4Config(dequantize=True), torch_dtype=torch.bfloat16, device_map="cuda:0", attn_implementation="eager", use_cache=False)
    model.gradient_checkpointing_enable(); model.enable_input_require_grads()
    model = get_peft_model(model, LoraConfig(r=int(os.environ.get("RFT_R", 32)), lora_alpha=64, lora_dropout=0.0, target_modules=["q_proj", "k_proj", "v_proj", "o_proj"], task_type="CAUSAL_LM"))
    model.print_trainable_parameters()
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=LR, weight_decay=0.0)
    steps = 5 if smoke else int(len(D) * EPOCHS); sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / 10) * max(0.0, 1 - s / max(1, steps // ACC)))
    model.train(); t0 = time.time(); tot = 0.0; ntok = 0
    for i in range(steps):
        z = D[i % len(D)]; ids = torch.tensor([z["ids"]], device="cuda:0"); lab = ids.clone(); lab[0, torch.tensor(z["mask"], device="cuda:0") == 0] = -100
        loss = model(input_ids=ids, labels=lab).loss / ACC; loss.backward(); tot += loss.item() * ACC; ntok += len(z["ids"])
        if (i + 1) % ACC == 0 or i == steps - 1:
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sched.step(); opt.zero_grad()
        if smoke or (i + 1) % 50 == 0:
            print(f"step {i+1}/{steps} loss {tot/(i+1):.4f} {ntok/(time.time()-t0):.0f} tok/s peak {torch.cuda.max_memory_allocated()/2**30:.1f} GiB", flush=True)
    os.makedirs(out, exist_ok=True); model.save_pretrained(f"{out}/adapter")
    if os.environ.get("MERGE") and not smoke:
        m = model.merge_and_unload(); m.config.use_cache = True
        if hasattr(m.config, "quantization_config"):
            delattr(m.config, "quantization_config")
        m.save_pretrained(f"{out}/merged", safe_serialization=True, max_shard_size="5GB")
        from transformers import AutoTokenizer
        AutoTokenizer.from_pretrained(MODEL).save_pretrained(f"{out}/merged")
        for f in ("chat_template.jinja", "generation_config.json"):
            if os.path.exists(f"{MODEL}/{f}"):
                os.system(f"cp {MODEL}/{f} {out}/merged/")
    print(f"done {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], "--smoke" in sys.argv)
