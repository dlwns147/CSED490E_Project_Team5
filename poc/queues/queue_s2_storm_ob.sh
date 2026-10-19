#!/bin/bash
# OB-P2: STORM-Qwen3-4B official TIR inference on OptiBench (605, 3 samples); first free GPU of 2-3 (after HO-L / the Qwen3-32B repeat).
cd /SSD/lean_postech/storm/STORM
G=""; for i in $(seq 1440); do for g in 2 3; do
  [ "$(nvidia-smi -i $g --query-gpu=memory.used --format=csv,noheader,nounits)" -lt 2000 ] && mkdir /NAS/SJ/POSTECH/nlp/results/.gpu_claim_$g 2>/dev/null && { G=$g; break 2; }; done; sleep 30; done
[ -n "$G" ] || exit 1
echo "S2_STORM_OB started on GPU$G $(date)" >> /NAS/SJ/POSTECH/nlp/results/queue_log.txt
CUDA_VISIBLE_DEVICES=$G TOKENIZERS_PARALLELISM=false VLLM_USE_FLASHINFER_SAMPLER=0 timeout 43200 /SSD/lean_postech/storm/venv/bin/python -m infer.inference_and_eval \
  --input_file data/test.tir_prompt.optibench.jsonl --output_dir /SSD/lean_postech/storm/out_optibench --model_name_or_path /SSD/huggingface/tangzhy/STORM-Qwen3-4B \
  --engine vllm --tensor_parallel_size 1 --n_sampling 3 --temperature 0.6 --max_model_len 40960 --max_tokens_per_call 32768 \
  >> /NAS/SJ/POSTECH/nlp/results/x3/run_storm_optibench.log 2>&1
rmdir /NAS/SJ/POSTECH/nlp/results/.gpu_claim_$G
echo "S2_STORM_OB done $(date)" >> /NAS/SJ/POSTECH/nlp/results/queue_log.txt
