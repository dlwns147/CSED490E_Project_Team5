#!/bin/bash
# Re-run gpt-oss-120b K8 (low / medium) after the SECOND last_block fix: the remaining "no code" rows were a doubled opening fence
# ("\`\`\`python\n\`\`\`python\n<code>...") that produced an empty first block. GPU 1 (started directly).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(poc/start_server.sh /SSD/huggingface/openai/gpt-oss-120b 8067 1 0.88 gptoss120_fix2) || { echo "gptoss120_fix2 failed" >> results/queue_log.txt; exit 1; }
export POC_BASE_URL=http://127.0.0.1:8067/v1
for eff in low medium; do t=oss120${eff:0:3}
  POC_REASONING_EFFORT=$eff $P poc/run_geo_cross.py --model_tag O5_geox${t}_k8fix2 --stdlib --n_inst 30 --max_tokens 16000 --temperature 0.7 --seed 1 --distract 8 > results/run_O5_geox${t}_k8fix2.log 2>&1
done
kill $S
echo OSSFIX2_DONE >> results/queue_log.txt
