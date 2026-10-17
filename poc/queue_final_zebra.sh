#!/bin/bash
# Final, powered zebra table: 24 puzzles per cell (144), no think: code+snippet+status x3 seeds (best-of-k), code (no snippet) x3 seeds;
# think: direct x1 (the comparison arm). 8B / 14B / 32B. Puzzles pre-generated (cache not rewritten by concurrent runs).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() {
  S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4; X="--n_per 24 --temperature 0.7"
  for sd in 1 2 3; do
    $P poc/run_zebra.py --model_tag F_z${m}_docst_s$sd --arms code --api_doc --doc_status $X --seed $sd --max_tokens 4096 > results/run_F_z${m}_docst_s$sd.log 2>&1
    $P poc/run_zebra.py --model_tag F_z${m}_code_s$sd --arms code $X --seed $sd --max_tokens 4096 > results/run_F_z${m}_code_s$sd.log 2>&1
  done
  $P poc/run_zebra.py --model_tag F_z${m}_thinkdirect_s1 --arms direct --think $X --seed 1 --max_tokens 20000 > results/run_F_z${m}_thinkdirect_s1.log 2>&1
  kill $S
}
lane /SSD/huggingface/Qwen/Qwen3-8B 8047 q8b_fz 8b & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-14B 8048 q14b_fz 14b & L2=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8049 q32b_fz 32b & L3=$!
wait $L1 $L2 $L3
echo FINALZEBRA_DONE >> results/queue_zebra.log
