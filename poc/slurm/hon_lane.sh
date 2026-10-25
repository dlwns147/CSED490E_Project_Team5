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
# HO-N4: `--model n3n` = NVIDIA-Nemotron-3-Nano-30B-A3B (hybrid Mamba-Transformer MoE, a new family) on 4 x RTX 3090, tensor parallel:
#   sbatch --gres=gpu:4 --cpus-per-task=16 poc/slurm/job.sh poc/slurm/hon_lane.sh --model n3n <group> ...
m=q35; dir=Qwen/Qwen3.5-9B; TS=temperature=1.0,top_p=0.95,top_k=20,presence_penalty=1.5   # model card thinking sampling
GPUL=0; XV="--language-model-only"; MNS=32
if [ "$1" = --model ]; then
  case $2 in
    g4e) m=g4e; dir=google/gemma-4-E4B-it; TS=temperature=1.0,top_p=0.95,top_k=64 ;;
    n3n) m=n3n; dir=derived/Nemotron-3-Nano-30B-A3B; TS=temperature=1.0,top_p=1.0   # model card: reasoning sampling
         # the shared copy lacks the config class its config.json names: a derived dir of links + that file (official repo, read first)
         D=/SSD/huggingface/$dir; [ -f $D/configuration_nemotron_h.py ] || { mkdir -p $D && ln -sf /SSD/huggingface/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16/* $D/ \
           && cp $POC_DATA/stage/n3n_code/configuration_nemotron_h.py $D/; }
         export POC_RAW_SYSTEM=1   # budget forcing (reviews): its template opens with an empty system turn
         GPUL=0,1,2,3; XV="--tensor-parallel-size 4 --trust-remote-code --mamba-ssm-cache-dtype float32"
         MNS=128 ;;   # 10-25: at 32 sequences the KV cache was 17% used with 1,120 requests waiting
  esac; shift 2
fi
grp=$1 set=$2 seeds=${3:-"1 2 3"}
# 10-23: the library prompt of long OptMATH problems + 32k thinking exceeded 36,864 tokens (vLLM rejects such a request, and the client
# then stops writing rows); thinking with the fact gets a 45,056-token context (generation is unchanged: still at most 32k new tokens).
MML=36864; case $grp in thinkfact|geothinkfact) MML=45056 ;; esac
S=$(bash poc/start_server.sh /SSD/huggingface/$dir $PORT $GPUL 0.92 hon_${m}_${grp}_${set}${3:+_$3} --max-model-len $MML $XV --max-num-seqs $MNS) || exit 1
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
  thinkfact) sub=""; [ "$set" = optibench ] && sub="FORM_SUBSET=0/3"   # HO-TF2: thinking with the library program in the prompt
         env $sub ${4:+NLOPT_SHARD=$4} NLOPT_SET=$set $P poc/run_form.py $m formx $seeds --tarm --think --max_tokens $TK >> $L 2>&1 & ;;
  geothinkfact) $P poc/run_geo_cross.py --model_tag S2_HOG_${m}_geo_thinkfact_s$set $GX --seed $set --distract 0 --algo_hint --think --max_tokens $TK >> $L 2>&1 & ;;
  repair) for sd in $seeds; do NLOPT_SET=$set $P poc/run_repair.py $m $sd formx >> $L 2>&1 & done ;;   # HO-N3
  review) sub=""; [ "$set" = optibench ] && sub="FORM_SUBSET=0/3"   # HO-N4: the 2k-token self-review gate (HO-VR), answer cap 2,048
         for sd in $seeds; do env $sub REVIEW_ANSWER_MAX=2048 NLOPT_SET=$set $P poc/run_review.py $m $sd 2000 formx >> $L 2>&1 & done ;;
  gaterep) sub=""; [ "$set" = optibench ] && sub="FORM_SUBSET=0/3"   # HO-N4: review + one cheap repair of the formx programs, one job
         for sd in $seeds; do env $sub REVIEW_ANSWER_MAX=2048 NLOPT_SET=$set $P poc/run_review.py $m $sd 2000 formx >> $L 2>&1 &
           NLOPT_SET=$set $P poc/run_repair.py $m $sd formx >> $L 2>&1 & done ;;
  budget2k) for st in optibench bwor logior optmath; do sub=""; [ "$st" = optibench ] && sub="FORM_SUBSET=0/3"   # HO-SB: budgeted thinking
           for sd in 1 2 3; do env $sub NLOPT_SET=$st $P poc/run_form.py $m formx $sd --think_budget 2000 >> $L 2>&1 & done; done ;;
  budget2kset) sub=""; [ "$set" = optibench ] && sub="FORM_SUBSET=0/3"   # HO-SB, one benchmark per job (resumes from its rows)
           for sd in 1 2 3; do env $sub NLOPT_SET=$set $P poc/run_form.py $m formx $sd --think_budget 2000 >> $L 2>&1 & done ;;
  geobudget) for sd in 1 2 3; do   # HO-SB3: geometry thinking with the fact under a 2,000-token budget
           $P poc/run_geo_cross.py --model_tag S2_HOG_${m}_geo_thinkfactb2000_s$sd $GX --seed $sd --distract 0 --algo_hint --think_budget 2000 --max_tokens 8192 >> $L 2>&1 &
         done ;;
  budgetsweep) for B in ${set//,/ }; do for st in optibench bwor logior optmath; do sub=""; [ "$st" = optibench ] && sub="FORM_SUBSET=0/3"   # HO-SB4
           for sd in 1 2 3; do env $sub NLOPT_SET=$st $P poc/run_form.py $m formx $sd --think_budget $B >> $L 2>&1 & done; done; done ;;
  cc) for sd in 1 2 3; do   # HO-CC: contest geometry (hidden tests), no fact: plain / 2k-budget think / full think
           CC_SET=full $P poc/run_cc.py run ${m}_plain $sd >> $L 2>&1 &
           CC_SET=full $P poc/run_cc.py run ${m}_tb2000 $sd --think_budget 2000 >> $L 2>&1 &
           CC_SET=full $P poc/run_cc.py run ${m}_think $sd --think >> $L 2>&1 &
         done ;;
  cc32k) for sd in 1 2 3; do CC_SET=full $P poc/run_cc.py run ${m}_think32k $sd --think --max_tokens 32000 >> $L 2>&1 & done ;;   # HO-CC amendment
  thinkshard) NLOPT_SHARD=$4 NLOPT_SET=$set $P poc/run_nlopt.py ${m}_$set thinkfree $seeds --think --max_tokens $TK >> $L 2>&1 & ;;
  think) NLOPT_SET=$set $P poc/run_nlopt.py ${m}_$set thinkfree $seeds --think --max_tokens $TK >> $L 2>&1 & ;;
  geo)   for sd in 1 2 3; do
           $P poc/run_geo_cross.py --model_tag S2_HOG_${m}_geo_fact_s$sd $GX --seed $sd --distract 0 --algo_hint --max_tokens 4096 >> $L 2>&1 &
           $P poc/run_geo_cross.py --model_tag S2_HOG_${m}_geo_think_s$sd $GX --seed $sd --distract 8 --think --max_tokens $TK >> $L 2>&1 &
         done ;;
esac; wait
kill $S; sleep 15
echo "SL_HON $grp $set done $(date -u)" >> results/queue_log.txt
