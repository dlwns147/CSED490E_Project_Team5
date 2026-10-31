"""DT (docs/prereg/PREREG_DT.md): LoRA fine-tuning of Qwen3-8B on the label-free checked programs (poc/build_sft_data.py), then a merged
copy that vLLM serves like the base model. Loss on the target only; the prompt is rendered with the chat template, thinking off.
usage: python sft_lora.py <base model dir> <data.jsonl> <adapter out dir> <merged out dir> [--epochs 2] [--max_len 3072] [--steps N]
Data-parallel over k GPUs (VER, 10-31): torchrun --nproc_per_node k sft_lora.py ... (one full copy per GPU, the same effective batch of 16;
rank 0 saves and merges). --tail-loss: the logits of the target positions only (batch 1, the target ends the row; the same loss, without
the full-vocabulary logits of the prompt, which ran a 3090 out of memory under data parallelism)."""
import json, os, sys

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments


class TailTrainer(Trainer):
    """mean cross-entropy over the target tokens of a one-example batch, from the logits of the last positions only"""
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.model_accepts_loss_kwargs = False   # the Trainer divides by the accumulation steps itself

    def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
        labels = inputs["labels"]
        k = int((labels != -100).sum(1).max()) + 1
        out = model(input_ids=inputs["input_ids"], attention_mask=inputs["attention_mask"], logits_to_keep=k)
        if k == 1:   # the target was truncated away (a prompt longer than max_len): no loss, as with the full logits
            loss = out.logits.sum() * 0.0
        else:
            logits, tgt = out.logits[:, :-1].float(), labels[:, -(k - 1):]
            loss = torch.nn.functional.cross_entropy(logits.reshape(-1, logits.size(-1)), tgt.reshape(-1), ignore_index=-100)
        return (loss, out) if return_outputs else loss


def arg(name, default):
    return type(default)(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def main():
    from peft import LoraConfig, get_peft_model
    base, data, ad_out, merged_out = sys.argv[1:5]
    epochs, max_len, steps = arg("--epochs", 2), arg("--max_len", 3072), arg("--steps", -1)
    tok = AutoTokenizer.from_pretrained(base)
    rows = [json.loads(l) for l in open(data)]
    feats = []
    for r in rows:
        prompt = tok.apply_chat_template([{"role": "user", "content": r["prompt"]}], tokenize=False, add_generation_prompt=True,
                                         enable_thinking=False)
        p_ids = tok(prompt, add_special_tokens=False)["input_ids"]
        t_ids = tok(r["target"] + "<|im_end|>\n", add_special_tokens=False)["input_ids"]
        ids = (p_ids + t_ids)[:max_len]
        labels = ([-100] * len(p_ids) + t_ids)[:max_len]
        feats.append({"input_ids": ids, "labels": labels})
    print(f"{len(feats)} examples, mean {sum(len(f['input_ids']) for f in feats) / len(feats):.0f} tokens, "
          f"{sum(len(f['input_ids']) >= max_len for f in feats)} truncated", flush=True)

    def collate(batch):
        n = max(len(b["input_ids"]) for b in batch)
        pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
        return {"input_ids": torch.tensor([b["input_ids"] + [pad] * (n - len(b["input_ids"])) for b in batch]),
                "labels": torch.tensor([b["labels"] + [-100] * (n - len(b["labels"])) for b in batch]),
                "attention_mask": torch.tensor([[1] * len(b["input_ids"]) + [0] * (n - len(b["input_ids"])) for b in batch])}

    rank, ws = int(os.environ.get("LOCAL_RANK", -1)), int(os.environ.get("WORLD_SIZE", 1))
    model = AutoModelForCausalLM.from_pretrained(base, torch_dtype=torch.bfloat16, device_map={"": rank} if rank >= 0 else "auto")
    model.gradient_checkpointing_enable(**({"gradient_checkpointing_kwargs": {"use_reentrant": False}} if ws > 1 else {}))
    model.enable_input_require_grads(); model.config.use_cache = False
    model = get_peft_model(model, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, task_type="CAUSAL_LM",
                                             target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]))
    model.print_trainable_parameters()
    args = TrainingArguments(output_dir=ad_out, per_device_train_batch_size=1, gradient_accumulation_steps=max(1, 16 // ws), num_train_epochs=epochs,
                             max_steps=steps, learning_rate=1e-4, lr_scheduler_type="cosine", warmup_ratio=0.03, bf16=True, logging_steps=5,
                             save_strategy="no", report_to=[], remove_unused_columns=False, seed=0,
                             **({"ddp_find_unused_parameters": False} if ws > 1 else {}))
    (TailTrainer if "--tail-loss" in sys.argv else Trainer)(model=model, args=args, train_dataset=feats, data_collator=collate).train()
    if rank > 0:
        return
    model.save_pretrained(ad_out)
    merged = model.merge_and_unload()
    merged.config.use_cache = True
    merged.save_pretrained(merged_out, safe_serialization=True)
    tok.save_pretrained(merged_out)
    for f in ("generation_config.json",):
        src = os.path.join(base, f)
        if os.path.exists(src):
            open(os.path.join(merged_out, f), "w").write(open(src).read())
    print("saved", ad_out, merged_out, flush=True)


if __name__ == "__main__":
    main()
