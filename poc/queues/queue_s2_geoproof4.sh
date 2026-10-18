#!/bin/bash
# GEO-P5: Qwen3.6 thinking proposes auxiliary points with an 80k cap; GPU2.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
mkdir results/.gpu_claim_2 || exit 1
for att in 1 2 3 4; do   # 2026-10-18 10:11 the first server died (NCCL watchdog, host load): retries resume the file
  S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8087 2 0.88 geoproof_q36b_$att --max-num-seqs 64 --language-model-only --max-model-len 90000) || { sleep 60; continue; }
  POC_TIMEOUT=14400 POC_THINK_SAMPLING=temperature=1.0,top_p=0.95,top_k=20 POC_BASE_URL=http://127.0.0.1:8087/v1 $P poc/geoproof_gen.py q36_think80k 16 --think --max_tokens 80000 >> results/geoproof/run_q36_think80k.log 2>&1
  kill $S; sleep 20
  [ "$(wc -l < results/geoproof/aux_q36_think80k.jsonl)" -ge 288 ] && break
done
rmdir results/.gpu_claim_2
echo "S2_GEOPROOF4 q36_think80k proposals done $(date)" >> results/queue_log.txt
cd /SSD/lean_postech/ag && nice -n 10 venv/bin/python ddar_aux.py /NAS/SJ/POSTECH/nlp/results/geoproof/aux_q36_think80k.jsonl 600 >> /NAS/SJ/POSTECH/nlp/results/geoproof/run_q36_think80k.log 2>&1
echo "S2_GEOPROOF4 q36_think80k checked by DD+AR $(date)" >> /NAS/SJ/POSTECH/nlp/results/queue_log.txt
