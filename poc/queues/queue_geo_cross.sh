#!/bin/bash
# after the G2 runs: cross-variant execution of one program per instance (thinking off, then on)
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export POC_BASE_URL=http://127.0.0.1:8000/v1
until grep -q GEO_DONE results/queue_geo.log 2>/dev/null; do sleep 60; done
$P poc/run_geo_cross.py --model_tag geox8b > results/run_geox8b.log 2>&1
$P poc/run_geo_cross.py --model_tag geox8b_think --think --max_tokens 10000 > results/run_geox8b_think.log 2>&1
echo GEOX_DONE >> results/queue_geo_cross.log
