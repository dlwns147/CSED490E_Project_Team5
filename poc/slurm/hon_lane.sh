#!/bin/bash
# HO-N (docs/prereg/PREREG_HON.md): Qwen3.5-9B (tag q35) on the held-out benchmarks, one RTX 3090 per job. Groups:
#   words <set> [seeds]   free / freef / formx / thinkfree on one word-problem benchmark (optibench, bwor, logior, optmath)
#   think <set> <seed>    thinkfree only (to split OptiBench's thinking over jobs)
#   geo                   held-out geometry: fact and think, seeds 1-3
#   sbatch -J hon_bwor poc/slurm/job.sh poc/slurm/hon_lane.sh words bwor
#   smoke: sbatch -J hon_smoke poc/slurm/job.sh poc/slurm/hon_lane.sh smoke
grp=$1 set=$2 seeds=${3:-"1 2 3"}
m=q35; dir=Qwen/Qwen3.5-9B
S=$(bash poc/start_server.sh /SSD/huggingface/$dir $PORT 0 0.92 hon_${grp}_$set --max-model-len 20480 --language-model-only --max-num-seqs 32) || exit 1
export POC_BASE_URL=http://127.0.0.1:$PORT/v1 POC_TIMEOUT=7200
L=results/x3/run_hon_${grp}_$set.log
GX="--stdlib --n_inst 12 --temperature 0.7 --tasks overlap,convex,tri,clip --resume"
case $grp in
  smoke) NLOPT_LIMIT=8 NLOPT_SET=bwor $P poc/run_nlopt.py q35smoke_bwor free 1 --max_tokens 8192 >> $L 2>&1 &
         NLOPT_LIMIT=8 NLOPT_SET=bwor $P poc/run_nlopt.py q35smoke_bwor thinkfree 1 --think --max_tokens 16000 >> $L 2>&1 & ;;
  words) for sd in $seeds; do
           NLOPT_SET=$set $P poc/run_nlopt.py ${m}_$set free $sd --max_tokens 8192 >> $L 2>&1 &
           NLOPT_SET=$set $P poc/run_nlopt.py ${m}_$set freef $sd --max_tokens 8192 >> $L 2>&1 &
           NLOPT_SET=$set $P poc/run_form.py $m formx $sd >> $L 2>&1 &
           NLOPT_SET=$set $P poc/run_nlopt.py ${m}_$set thinkfree $sd --think --max_tokens 16000 >> $L 2>&1 &
         done ;;
  think) NLOPT_SET=$set $P poc/run_nlopt.py ${m}_$set thinkfree $seeds --think --max_tokens 16000 >> $L 2>&1 & ;;
  geo)   for sd in 1 2 3; do
           $P poc/run_geo_cross.py --model_tag S2_HOG_${m}_geo_fact_s$sd $GX --seed $sd --distract 0 --algo_hint --max_tokens 4096 >> $L 2>&1 &
           $P poc/run_geo_cross.py --model_tag S2_HOG_${m}_geo_think_s$sd $GX --seed $sd --distract 8 --think --max_tokens 16000 >> $L 2>&1 &
         done ;;
esac; wait
kill $S; sleep 15
echo "SL_HON $grp $set done $(date -u)" >> results/queue_log.txt
