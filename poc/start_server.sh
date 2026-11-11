#!/bin/bash
# start_server.sh <model-dir> <port> <gpu> <frac> <tag> [extra vllm args...]: start vLLM in the background, wait until healthy, print PID
# 9>&- : the server must NOT inherit the GPU-pick lock fd from start_server_retry.sh (it used to hold the lock for its
# whole lifetime, which serialised every second lane behind the first lane's server).
# Port guard: vLLM binds with SO_REUSEPORT, so a second server on a busy port starts and the health check below passes against
# the OTHER server, silently splitting requests between two models (2026-10-10 Llama/Qwen clash). `ss` is not installed here,
# so probe with curl. Server 2: /NAS is CIFS without exec bits, so call scripts via `bash poc/...`. Port convention (old shared server): session A 8040-8099, session sj-c4 8100+; on Slurm each job has its own container network,
# so poc/slurm/job.sh passes PORT = 20000 + job id mod 20000.
# With POC_LOCAL (Slurm, poc/slurm/job.sh, 2026-11-11) the server log is written on the node ($POC_LOCAL/stage/nlp/results, moved to /home1
# when the job ends) and the GPU-choice lines go to stderr (the job's own log) instead of the shared results/gpu_choice.log.
L=results GC=results/gpu_choice.log
if [ -n "$POC_LOCAL" ]; then L=$POC_LOCAL/stage/nlp/results GC=/dev/stderr; mkdir -p $L; fi
if curl -sf -m 3 localhost:$2/health >/dev/null 2>&1; then echo "$5 failed: port $2 already answering ($(date))" >> $GC; exit 1; fi
bash poc/serve_gpu.sh $1 $2 $3 $4 "${@:6}" > $L/server_vllm_$5.log 2>&1 9>&- &
SPID=$!
echo "$5: GPU $3 frac $4 port $2 ($(date))" >> $GC
while kill -0 $SPID 2>/dev/null; do curl -sf localhost:$2/health >/dev/null && { echo $SPID; exit 0; }; sleep 5; done
echo "$5 failed: $(grep -m1 -oE 'ValueError: .{0,120}' $L/server_vllm_$5.log)" >> $GC; exit 1
