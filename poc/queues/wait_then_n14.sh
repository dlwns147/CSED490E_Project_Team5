#!/bin/bash
# Start N14 on GPUs 0 + 2 once the N12 replication there is done and the source programs exist (bounded wait: 3 h).
cd /NAS/SJ/POSTECH/nlp
for i in $(seq 540); do
  grep -q "S2_N12R runs done" results/queue_log.txt && [ -f results/n14/sources_S2_N10.json ] && [ -f results/n14/sources_S2_N10m3.json ] && break
  sleep 20
done
grep -q "S2_N12R runs done" results/queue_log.txt || { echo "N14 waiter gave up $(date)" >> results/queue_log.txt; exit 1; }
echo "S2_N14 started (GPUs 0+2) $(date)" >> results/queue_log.txt
G1=0 G2=2 bash poc/queues/queue_s2_n14.sh
