#!/bin/bash
# Gemma-3-27B lane of queue_xfam2.sh, re-launched with a flash_attn import blocker.
# Geometry --stdlib n=300: greedy base / task-matched; T=0.7 base x3 (MR-select k=3); T=0.7 K=8 distractors.  CO 84 inst: no doc / full / scoped, T=0.7 s1.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
runs() {  # runs <port> <short>
  export POC_BASE_URL=http://127.0.0.1:$1/v1; m=$2; X="--stdlib --n_inst 30 --max_tokens 4096"
  $P poc/run_geo_cross.py --model_tag X_geox${m}_base $X > results/run_X_geox${m}_base.log 2>&1
  $P poc/run_geo_cross.py --model_tag X_geox${m}_pt $X --primitives --prims_task > results/run_X_geox${m}_pt.log 2>&1
  for sd in 1 2 3; do $P poc/run_geo_cross.py --model_tag X_geox${m}_base_t07s$sd $X --temperature 0.7 --seed $sd > results/run_X_geox${m}_base_t07s$sd.log 2>&1; done
  $P poc/run_geo_cross.py --model_tag X_geox${m}_dis0_t07s1 $X --distract 0 --temperature 0.7 --seed 1 > results/run_X_geox${m}_dis0_t07s1.log 2>&1
  $P poc/run_geo_cross.py --model_tag X_geox${m}_dis8_t07s1 $X --distract 8 --temperature 0.7 --seed 1 > results/run_X_geox${m}_dis8_t07s1.log 2>&1
  for v in "nodoc:" "doc:--api_doc" "doctask:--api_doc_task"; do n=${v%%:*}; x=${v#*:}
    $P poc/run_co.py --model_tag X_co${m}_${n} --arms solver $x --repair 2 --temperature 0.7 --seed 1 > results/run_X_co${m}_${n}.log 2>&1; done
}
export POC_PYLIB=/dev/shm/noflash:/dev/shm/pylib_vllm   # flash_attn in /opt/conda is ABI-mismatched (Gemma-3 vision tower imports it)
S=$(start /SSD/huggingface/gaunernst/gemma-3-27b-it-int4-awq 8074 gemma27_x2); runs 8074 gemma27; kill $S
echo GEMMA_DONE >> results/queue_distract.log
