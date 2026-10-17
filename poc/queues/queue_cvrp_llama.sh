#!/bin/bash
# Chained after queue_t7bud.sh (R1 on GPU 3): model coverage on the realistic CO problem. Llama-3.3-70B-w4a16 on CVRP:
# no doc / full sheet / snippet x 3 seeds (best-of-3), solver arm, repair 2, T=0.7. Then R1-Distill-Llama-70B snippet (T=0.6, 16k tokens).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
while kill -0 146222 2>/dev/null; do sleep 60; done
X="--arms solver --probs cvrp --n_inst 10 --repair 2"
S=$(poc/start_server.sh /SSD/huggingface/RedHatAI/Llama-3.3-70B-Instruct-quantized.w4a16 8090 3 0.7 llama70_cvrp) && {
  export POC_BASE_URL=http://127.0.0.1:8090/v1
  $P poc/run_co.py --model_tag V_col70_nodoc_s1 $X --temperature 0.7 --seed 1 > results/run_V_col70_nodoc.log 2>&1
  $P poc/run_co.py --model_tag V_col70_doc_s1 $X --temperature 0.7 --seed 1 --api_doc > results/run_V_col70_doc.log 2>&1
  for sd in 1 2 3; do $P poc/run_co.py --model_tag V_col70_doctask_s$sd $X --temperature 0.7 --seed $sd --api_doc --api_doc_task > results/run_V_col70_doctask_s$sd.log 2>&1; done
  kill $S; sleep 20; }
S=$(poc/start_server.sh /SSD/huggingface/RedHatAI/DeepSeek-R1-Distill-Llama-70B-quantized.w4a16 8091 3 0.7 r1l70_cvrp) && {
  export POC_BASE_URL=http://127.0.0.1:8091/v1
  $P poc/run_co.py --model_tag V_cor1l70_doctask_s1 $X --temperature 0.6 --seed 1 --api_doc --api_doc_task --max_tokens 16000 > results/run_V_cor1l70_doctask.log 2>&1
  $P poc/run_co.py --model_tag V_cor1l70_nodoc_s1 $X --temperature 0.6 --seed 1 --max_tokens 16000 > results/run_V_cor1l70_nodoc.log 2>&1
  kill $S; }
echo CVRPLLAMA_DONE >> results/queue_log.txt
