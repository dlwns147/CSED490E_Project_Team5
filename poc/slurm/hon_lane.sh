#!/bin/bash
# HO-N (docs/prereg/PREREG_HON.md): Qwen3.5-9B (tag q35) on the held-out benchmarks, one RTX 3090 per job. Groups:
#   words <set> [seeds]   free / freef / formx / thinkfree on one word-problem benchmark (optibench, bwor, logior, optmath)
#   think <set> <seed>    thinkfree only (to split OptiBench's thinking over jobs)
#   thinkshard <set> <seed> <i/k>   thinkfree on problems i, i+k, ... only (NLOPT_SHARD; poc/merge_shards.py merges after)
#   cheap <set> [seeds]   free / freef / formx only
#   geo                   held-out geometry: fact and think, seeds 1-3 (geofact: fact only; geothink <seed>: think only)
# 10-23 01:2x UTC: thinking runs of this model are long and its KV cache holds ~73k tokens, so a job with all arms decodes ~200 tokens/s;
# the work is now split into one job per arm group and seed (poc/slurm/hon_array.sh + hon_specs.txt; runs resume from their rows).
#   sbatch -J hon_bwor poc/slurm/job.sh poc/slurm/hon_lane.sh words bwor
#   smoke: sbatch -J hon_smoke poc/slurm/job.sh poc/slurm/hon_lane.sh smoke   (smoke2: thinking only, at the amended settings)
# Thinking (amended before the main runs, PREREG_HON.md): the model card's thinking sampling and a 32k budget; cheap arms as all models.
# Another unseen model (HO-N2): a leading `--model g4e` (Gemma-4-E4B-it, PREREG_HON.md addendum) selects it; default q35.
m=q35; dir=Qwen/Qwen3.5-9B; TS=temperature=1.0,top_p=0.95,top_k=20,presence_penalty=1.5   # model card thinking sampling
if [ "$1" = --model ]; then
  case $2 in g4e) m=g4e; dir=google/gemma-4-E4B-it; TS=temperature=1.0,top_p=0.95,top_k=64 ;; esac; shift 2
fi
grp=$1 set=$2 seeds=${3:-"1 2 3"}
S=$(bash poc/start_server.sh /SSD/huggingface/$dir $PORT 0 0.92 hon_${m}_${grp}_$set --max-model-len 36864 --language-model-only --max-num-seqs 32) || exit 1
export POC_BASE_URL=http://127.0.0.1:$PORT/v1 POC_TIMEOUT=7200
export POC_THINK_SAMPLING=$TS   # applied to thinking calls only (llm.chat)
TK=32000
L=results/x3/run_hon_${m}_${grp}_${set}${3:+_$3}${4:+_${4/\//of}}.log
GX="--stdlib --n_inst 12 --temperature 0.7 --tasks overlap,convex,tri,clip --resume"
case $grp in
  smoke) export POC_THINK_SAMPLING=   # the first smoke ran the harness sampling
         NLOPT_LIMIT=8 NLOPT_SET=bwor $P poc/run_nlopt.py q35smoke_bwor free 1 --max_tokens 8192 >> $L 2>&1 &
         NLOPT_LIMIT=8 NLOPT_SET=bwor $P poc/run_nlopt.py q35smoke_bwor thinkfree 1 --think --max_tokens 16000 >> $L 2>&1 & ;;
  probe) PYTHONPATH=poc $P -c "
from llm import client
for think in (False, True):
    r = client.chat.completions.create(model='local', messages=[{'role': 'user', 'content': 'Write a Python program that prints the area of a 3-4-5 triangle.'}],
        max_tokens=4000, temperature=1.0, extra_body={'chat_template_kwargs': {'enable_thinking': think}, 'skip_special_tokens': False})
    t = r.choices[0].message.content or ''
    print('THINK' if think else 'PLAIN', r.choices[0].finish_reason, r.usage.completion_tokens, repr(t[:300]), '...', repr(t[-300:]))
" >> $L 2>&1
         NLOPT_LIMIT=8 NLOPT_SET=bwor $P poc/run_nlopt.py ${m}smoke_bwor free 1 --max_tokens 8192 >> $L 2>&1 &
         NLOPT_LIMIT=8 NLOPT_SET=bwor $P poc/run_nlopt.py ${m}smoke_bwor thinkfree 1 --think --max_tokens $TK >> $L 2>&1 &
         NLOPT_LIMIT=16 NLOPT_SET=optibench $P poc/run_nlopt.py ${m}smoke_optibench thinkfree 1 --think --max_tokens $TK >> $L 2>&1 & ;;
  smoke2) NLOPT_LIMIT=8 NLOPT_SET=bwor $P poc/run_nlopt.py q35smoke2_bwor thinkfree 1 --think --max_tokens $TK >> $L 2>&1 &
          NLOPT_LIMIT=16 NLOPT_SET=optibench $P poc/run_nlopt.py q35smoke2_optibench thinkfree 1 --think --max_tokens $TK >> $L 2>&1 & ;;
  words) for sd in $seeds; do
           NLOPT_SET=$set $P poc/run_nlopt.py ${m}_$set free $sd --max_tokens 8192 >> $L 2>&1 &
           NLOPT_SET=$set $P poc/run_nlopt.py ${m}_$set freef $sd --max_tokens 8192 >> $L 2>&1 &
           NLOPT_SET=$set $P poc/run_form.py $m formx $sd >> $L 2>&1 &
           NLOPT_SET=$set $P poc/run_nlopt.py ${m}_$set thinkfree $sd --think --max_tokens $TK >> $L 2>&1 &
         done ;;
  cheap) for sd in $seeds; do
           NLOPT_SET=$set $P poc/run_nlopt.py ${m}_$set free $sd --max_tokens 8192 >> $L 2>&1 &
           NLOPT_SET=$set $P poc/run_nlopt.py ${m}_$set freef $sd --max_tokens 8192 >> $L 2>&1 &
           NLOPT_SET=$set $P poc/run_form.py $m formx $sd >> $L 2>&1 &
         done ;;
  geofact) for sd in 1 2 3; do
           $P poc/run_geo_cross.py --model_tag S2_HOG_${m}_geo_fact_s$sd $GX --seed $sd --distract 0 --algo_hint --max_tokens 4096 >> $L 2>&1 &
         done ;;
  geothink) $P poc/run_geo_cross.py --model_tag S2_HOG_${m}_geo_think_s$set $GX --seed $set --distract 8 --think --max_tokens $TK >> $L 2>&1 & ;;
  thinkshard) NLOPT_SHARD=$4 NLOPT_SET=$set $P poc/run_nlopt.py ${m}_$set thinkfree $seeds --think --max_tokens $TK >> $L 2>&1 & ;;
  think) NLOPT_SET=$set $P poc/run_nlopt.py ${m}_$set thinkfree $seeds --think --max_tokens $TK >> $L 2>&1 & ;;
  geo)   for sd in 1 2 3; do
           $P poc/run_geo_cross.py --model_tag S2_HOG_${m}_geo_fact_s$sd $GX --seed $sd --distract 0 --algo_hint --max_tokens 4096 >> $L 2>&1 &
           $P poc/run_geo_cross.py --model_tag S2_HOG_${m}_geo_think_s$sd $GX --seed $sd --distract 8 --think --max_tokens $TK >> $L 2>&1 &
         done ;;
esac; wait
kill $S; sleep 15
echo "SL_HON $grp $set done $(date -u)" >> results/queue_log.txt
