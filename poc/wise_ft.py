"""B2: WiSE-FT weight interpolation (Wortsman et al. 2022) between the base model and a fine-tuned (merged LoRA) model:
theta = (1 - alpha) * theta_base + alpha * theta_tuned, written as a full model directory that vLLM can serve.
usage: /opt/conda/bin/python wise_ft.py <base_dir> <tuned_dir> <out_dir> <alpha>"""
import glob, json, os, shutil, sys
import torch
from safetensors.torch import load_file, save_file

base_dir, tuned_dir, out_dir, alpha = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])


def load_all(d):
    w = {}
    for f in sorted(glob.glob(os.path.join(d, "*.safetensors"))):
        w.update(load_file(f))
    return w


B, T = load_all(base_dir), load_all(tuned_dir)
assert set(B) == set(T), (len(set(B) ^ set(T)), sorted(set(B) ^ set(T))[:5])
os.makedirs(out_dir, exist_ok=True)
out, shard, size, idx, n = {}, {}, 0, {}, 0
for k in sorted(T):
    shard[k] = ((1 - alpha) * B[k].float() + alpha * T[k].float()).to(T[k].dtype).contiguous()
    size += shard[k].numel() * shard[k].element_size()
    if size > 4e9:
        n += 1; name = f"model-{n:05d}.safetensors"; save_file(shard, os.path.join(out_dir, name), metadata={"format": "pt"})
        idx.update({kk: name for kk in shard}); shard, size = {}, 0
if shard:
    n += 1; name = f"model-{n:05d}.safetensors"; save_file(shard, os.path.join(out_dir, name), metadata={"format": "pt"})
    idx.update({kk: name for kk in shard})
json.dump({"metadata": {}, "weight_map": idx}, open(os.path.join(out_dir, "model.safetensors.index.json"), "w"))
for f in os.listdir(tuned_dir):
    if not f.endswith(".safetensors") and f != "model.safetensors.index.json":
        shutil.copy(os.path.join(tuned_dir, f), out_dir)
print("wrote", out_dir, "alpha", alpha, "tensors", len(idx), "max |diff| sample",
      max(float((T[k].float() - B[k].float()).abs().max()) for k in list(T)[:20]))
