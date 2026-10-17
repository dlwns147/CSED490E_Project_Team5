#!/bin/bash
# after the remaining X6 q36 mip / mipf processes finish, stop their server (PID 2145860, GPU2). Bounded: <= 5 h.
cd /NAS/SJ/POSTECH/nlp
for i in $(seq 900); do ps -p 2153288,2153289,2153290,2153291,2153292,2153293 >/dev/null || break; sleep 20; done
kill 2145860 && echo "S2_X6 q36 mip/mipf finished; server on GPU2 stopped $(date)" >> results/queue_log.txt
