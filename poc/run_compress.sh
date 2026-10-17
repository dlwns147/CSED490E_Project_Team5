#!/bin/bash
# PoC #7 — compression sweep: does weight / KV-cache quantization hurt algorithmic tasks more than perplexity shows?
# per config: wikitext-2 PPL, text-simulation (bfs/lis, n=6/12/24, CoT + code, temp 0), counterexample stress (40 items, k=2)
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
T=/root/llm_algo_poc_tools
CONFIGS=(
  "q8_0-kvf16|Qwen3-8B-Q8_0.gguf|"
  "q4km-kvf16|Qwen3-8B-Q4_K_M.gguf|"
  "q3km-kvf16|Qwen3-8B-Q3_K_M.gguf|"
  "q2k-kvf16|Qwen3-8B-Q2_K.gguf|"
  "q4km-kvq8|Qwen3-8B-Q4_K_M.gguf|-fa on -ctk q8_0 -ctv q8_0"
  "q4km-kvq4|Qwen3-8B-Q4_K_M.gguf|-fa on -ctk q4_0 -ctv q4_0"
)
for c in "${CONFIGS[@]}"; do
  IFS='|' read -r tag model extra <<< "$c"
  log=results/compress_${tag}.log
  grep -q CONFIG_DONE $log 2>/dev/null && continue
  echo "== $tag $(date)" >> $log
  # PPL, plus KL divergence of token distributions vs the Q8_0 reference (base logits saved by the first config)
  if [ "$tag" = "q8_0-kvf16" ]; then KL="--kl-divergence-base /root/llm_algo_poc_tools/kl_base_q8.bin"; \
  else KL="--kl-divergence-base /root/llm_algo_poc_tools/kl_base_q8.bin --kl-divergence"; fi
  LD_LIBRARY_PATH=$T/llama.cpp/build2/bin $T/llama.cpp/build2/bin/llama-perplexity -m $T/models/$model \
     -f data/wiki.test.raw -c 512 --chunks 20 -t 32 $extra $KL > results/ppl_${tag}.txt 2>&1
  grep -E "Final estimate|Mean +KLD|Same top p|error" results/ppl_${tag}.txt >> $log
  poc/serve_cpu.sh $model 8090 16 $extra > results/server_${tag}.log 2>&1 &
  SPID=$!
  until curl -sf localhost:8090/health >/dev/null; do sleep 2; kill -0 $SPID 2>/dev/null || { echo "server died" >> $log; break; }; done
  export POC_BASE_URL=http://127.0.0.1:8090/v1
  $P poc/run_exec.py --model_tag c_${tag} --tasks bfs,lis --sizes 6,12 --modes code,cot >> $log 2>&1
  $P poc/run_hack.py --model_tag c_${tag} --n_items 40 --k 2 --workers 16 --strategies stress >> $log 2>&1
  # solving the same kind of problems (falsification vs solving under compression): 40 unique-answer easy CF problems
  $P poc/run_perturb.py --model_tag c_${tag} --source train --exclude_multi --n_items 40 --k 1 --versions orig --workers 16 >> $log 2>&1
  kill $SPID; wait $SPID 2>/dev/null
  echo CONFIG_DONE >> $log
done
echo SWEEP_DONE >> results/compress_sweep.log
