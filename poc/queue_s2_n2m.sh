#!/bin/bash
# N2m (PREREG_N.md): repair rounds 2-3 for gpt-oss-20b low seed 1 on 8042 (GPU1).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full POC_REASONING_EFFORT=low POC_BASE_URL=http://127.0.0.1:8042/v1
S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-20b 8042 1 0.85 n2m_o20) || exit 1
$P poc/repair_cc.py rep_oss20_low 1 --max_tokens 16000 > results/h2/run_rep2_oss20_low_s1.log 2>&1
$P poc/repair_cc.py rep_rep_oss20_low 1 --max_tokens 16000 > results/h2/run_rep3_oss20_low_s1.log 2>&1
kill $S
echo "S2_N2m runs done $(date)" >> results/queue_log.txt
