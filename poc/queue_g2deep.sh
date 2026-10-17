#!/bin/bash
# G2-deep: solutions S1 (metamorphic self-repair), S4 (exact primitives), S2b (canonical prompt) + code-mode rerun with
# stored programs (mechanism analysis). Lane A: Qwen3-8B; lane B: Qwen3-32B. Each lane owns its server.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
(
  S=$(start /SSD/huggingface/Qwen/Qwen3-8B 8020 q8b_g2deep)
  export POC_BASE_URL=http://127.0.0.1:8020/v1
  $P poc/run_geo_mr.py --model_tag mr8b > results/run_geomr8b.log 2>&1 &
  a=$!
  $P poc/run_geo_cross.py --model_tag geox8b_prims --primitives > results/run_geox8b_prims.log 2>&1 &
  b=$!
  $P poc/run_geo.py --model_tag geo8b_code_v2 --mode code --max_tokens 2048 > results/run_geo8b_code_v2.log 2>&1 &
  c=$!
  $P poc/run_geo.py --model_tag geo8b_code_canonprompt --mode code --canon_prompt --max_tokens 2048 > results/run_geo8b_code_cp.log 2>&1 &
  d=$!
  wait $a $b $c $d
  kill $S
) &
LA=$!
sleep 300
(
  S=$(start /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8021 q32b_g2deep)
  export POC_BASE_URL=http://127.0.0.1:8021/v1
  $P poc/run_geo_mr.py --model_tag mr32b --max_tokens 4096 > results/run_geomr32b.log 2>&1 &
  a=$!
  $P poc/run_geo_cross.py --model_tag geox32b_prims --primitives --max_tokens 4096 > results/run_geox32b_prims.log 2>&1 &
  b=$!
  wait $a $b
  kill $S
) &
LB=$!
wait $LA $LB
echo G2DEEP_DONE >> results/queue_g2deep.log
