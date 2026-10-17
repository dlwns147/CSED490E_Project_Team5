#!/bin/bash
# E1 x E2: Llama-3.3-70B on the held-out CO problems (bin packing, vertex cover; 108 inst): direct, solver no doc / full sheet / scoped snippet, T=0.7 s1
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
while true; do G=$(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits | awk -F', ' '$2 < 5000 {print $1; exit}'); [ -n "$G" ] && break; sleep 120; done
S=$(poc/start_server.sh /SSD/huggingface/RedHatAI/Llama-3.3-70B-Instruct-quantized.w4a16 8081 $G 0.7 llama70_held) || exit 1
export POC_BASE_URL=http://127.0.0.1:8081/v1; X="--probs binpack,vcover --n_inst 18 --temperature 0.7 --seed 1"
$P poc/run_co.py --model_tag H_collama70_direct_s1 --arms direct $X > results/run_H_collama70_direct_s1.log 2>&1
for v in "nodoc:" "doc:--api_doc" "doctask:--api_doc_task"; do n=${v%%:*}; x=${v#*:}
  $P poc/run_co.py --model_tag H_collama70_${n}_s1 --arms solver $x --repair 2 $X > results/run_H_collama70_${n}_s1.log 2>&1; done
kill $S
echo L70HELD_DONE >> results/queue_log.txt
