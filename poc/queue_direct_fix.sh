#!/bin/bash
# after the exec run: drop invalid direct-mode rows (truncated explanations) and re-run direct with assistant prefill
cd /NAS/SJ/POSTECH/nlp
until grep -q EXEC_DONE results/run_exec_qwen3-8b.log 2>/dev/null; do sleep 30; done
P=/root/venvs/llm_algo_poc/bin/python
$P -c "
import json
p='results/exec_qwen3-8b.jsonl'; rows=[json.loads(l) for l in open(p)]
json.dump([r for r in rows if r['mode']=='direct'], open('results/exec_qwen3-8b_direct_v1_invalid.json','w'))
open(p,'w').write(''.join(json.dumps(r)+'\n' for r in rows if r['mode']!='direct'))"
$P poc/run_exec.py --model_tag qwen3-8b --modes direct > results/run_exec_direct_qwen3-8b.log 2>&1
echo DIRECT_DONE >> results/run_exec_direct_qwen3-8b.log
