#!/bin/bash
# E3 (results/PREREG_E3.md): escalation runs for the pipeline simulation, Qwen3-8B, seed 1, same instances as C1.
# Three identical Qwen3-8B servers: 8044 (GPU 0), 8046 (GPU 1), 8047 (GPU 2); runs are spread over them (relaunched 12:35 after the
# first launch on 8044 alone was KV-cache bound).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
X="--stdlib --n_inst 30 --temperature 0.7 --seed 1"
r() { port=$1; tag=S2_E3_geox8b_$2_t07s1; shift 2; POC_BASE_URL=http://127.0.0.1:$port/v1 $P poc/run_geo_cross.py --model_tag $tag $X "$@" > results/run_$tag.log 2>&1; }
r 8046 dis0_think --distract 0 --think --max_tokens 16000 &
r 8047 dis8_think --distract 8 --think --max_tokens 16000 &
r 8046 hard_think --tasks lattice,rectunion --think --max_tokens 16000 &
r 8044 dis0_b1024 --distract 0 --think_budget 1024 --max_tokens 4096 &
r 8044 dis8_b1024 --distract 8 --think_budget 1024 --max_tokens 4096 &
r 8047 hard_b1024 --tasks lattice,rectunion --think_budget 1024 --max_tokens 4096 &
r 8044 dis0_selfhint --distract 0 --self_hint --max_tokens 4096 &
r 8044 dis8_selfhint --distract 8 --self_hint --max_tokens 4096 &
r 8047 hard_selfhint --tasks lattice,rectunion --self_hint --max_tokens 4096 &
wait
echo "S2_E3 runs done $(date)" >> results/queue_log.txt
