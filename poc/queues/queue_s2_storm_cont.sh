#!/bin/bash
# 2026-10-19 10:50 UTC: STORM's first MAMO pass alone took ~3.5 h and its code only writes results at the end, so the 6 h `timeout` in
# queue_s2_storm.sh would likely kill it before any output. The queue script and its timeout were killed by PID (the inference process
# itself keeps running); this script waits for that PID, then runs the X3 set with a 12 h limit and releases GPU0.
# usage: bash poc/queues/queue_s2_storm_cont.sh <pid of the running mamo_full inference>
cd /SSD/lean_postech/storm/STORM
while kill -0 $1 2>/dev/null; do sleep 60; done
echo "S2_STORM mamo_full ended (pid $1; outputs: $(ls /SSD/lean_postech/storm/out_mamo_full | tr '\n' ' ')) $(date)" >> /NAS/SJ/POSTECH/nlp/results/queue_log.txt
for set in x3; do
  CUDA_VISIBLE_DEVICES=0 TOKENIZERS_PARALLELISM=false VLLM_USE_FLASHINFER_SAMPLER=0 timeout 43200 /SSD/lean_postech/storm/venv/bin/python -m infer.inference_and_eval \
    --input_file data/test.tir_prompt.$set.jsonl --output_dir /SSD/lean_postech/storm/out_$set --model_name_or_path /SSD/huggingface/tangzhy/STORM-Qwen3-4B \
    --engine vllm --tensor_parallel_size 1 --n_sampling 3 --temperature 0.6 --max_model_len 40960 --max_tokens_per_call 32768 \
    >> /NAS/SJ/POSTECH/nlp/results/x3/run_storm_$set.log 2>&1
  echo "S2_STORM $set done $(date)" >> /NAS/SJ/POSTECH/nlp/results/queue_log.txt
done
rmdir /NAS/SJ/POSTECH/nlp/results/.gpu_claim_0
