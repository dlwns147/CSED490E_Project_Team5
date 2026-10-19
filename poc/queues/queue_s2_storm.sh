#!/bin/bash
# STORM-Qwen3-4B baseline with its official TIR inference (github.com/tangzhy/STORM), on our full MAMO and the X3 set; GPU0.
cd /SSD/lean_postech/storm/STORM
for i in $(seq 360); do [ -f /SSD/huggingface/tangzhy/STORM-Qwen3-4B/model.safetensors.index.json ] || [ -f /SSD/huggingface/tangzhy/STORM-Qwen3-4B/model.safetensors ] && [ "$(du -s /SSD/huggingface/tangzhy/STORM-Qwen3-4B | cut -f1)" -gt 8000000 ] && break; sleep 20; done
mkdir /NAS/SJ/POSTECH/nlp/results/.gpu_claim_0 || exit 1
for set in mamo_full x3; do
  CUDA_VISIBLE_DEVICES=0 TOKENIZERS_PARALLELISM=false VLLM_USE_FLASHINFER_SAMPLER=0 timeout 21600 /SSD/lean_postech/storm/venv/bin/python -m infer.inference_and_eval \
    --input_file data/test.tir_prompt.$set.jsonl --output_dir /SSD/lean_postech/storm/out_$set --model_name_or_path /SSD/huggingface/tangzhy/STORM-Qwen3-4B \
    --engine vllm --tensor_parallel_size 1 --n_sampling 3 --temperature 0.6 --max_model_len 40960 --max_tokens_per_call 32768 \
    >> /NAS/SJ/POSTECH/nlp/results/x3/run_storm_$set.log 2>&1
  echo "S2_STORM $set done $(date)" >> /NAS/SJ/POSTECH/nlp/results/queue_log.txt
done
rmdir /NAS/SJ/POSTECH/nlp/results/.gpu_claim_0
