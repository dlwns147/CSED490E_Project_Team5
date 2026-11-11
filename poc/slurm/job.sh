#!/bin/bash
# poc/slurm/job.sh: run one lane script on one GPU of the Slurm cluster, inside the project's docker image (2026-10-22).
#   cd /home1/leesangjun/SJ/POSTECH/nlp && sbatch -J <name> poc/slurm/job.sh poc/slurm/<lane>.sh [args...]
# Any model + client commands: poc/slurm/lane.sh (or `python bench.py submit ...`, which writes that sbatch line).
# CPU-only work (analyses that re-run stored programs) uses the same image on a CPU partition, e.g.
#   sbatch -J hogc_an -p cpu-max16,cpu-max10,cpu-max24 -q nogpu --gres=none poc/slurm/job.sh '$P poc/analyze_hogc.py'
# Partition: RTX3090 (24 GB, the project's target GPU; the user reserves RTX6000ADA / L40S / A100-80GB for other sessions).
# Cluster rules: 4 CPUs per GPU, no --time, no -q on non-A100 partitions. Reuse a node that already holds the image with
# `--nodelist=<node>` (`docker load` of the 26 GB tar is per node: 258 s on n19; the first line of the log names the node).
# Inside the container (root): repo at /NAS/SJ/POSTECH/nlp (= /home1/leesangjun/SJ/POSTECH/nlp), models /SSD/huggingface
# (= /home/leesangjun/SSD/huggingface, root-owned shared pool), data $POC_DATA (= /home1/leesangjun/SJ/POSTECH/nlp_data).
# The lane gets: the allocated GPU as index 0, PORT (free, from the job id), P (client / sandbox python), SLURM_ARRAY_TASK_ID (arrays). Files the container
# writes under results/ are chowned back to the submitting user at the end.
# Node-local outputs (user 2026-11-11: save on /local-data, then move to /home1; nothing left owned by root):
# - the job's own output (everything after the first line of the Slurm log) goes to $LOCAL/job.out on the node and is appended to the Slurm log at the end;
# - POC_LOCAL=$LOCAL and PYTHONPATH=poc/slurm/localio make every Python process write files under /NAS/SJ/POSTECH (repo, nlp_data) to $LOCAL/stage
#   (reads see staged files first); lane.sh and start_server.sh stage their logs the same way; at the end the stage is chowned and moved onto /home1;
# - any root-owned file left under the repo or nlp_data (a non-Python writer) is chowned back to the user.
#SBATCH -J nlp
#SBATCH -o /home1/leesangjun/out/nlp/%j.out
#SBATCH -p RTX3090
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH -N 1
#SBATCH -n 1

[ -n "$1" ] || { echo "usage: sbatch poc/slurm/job.sh <lane script .sh> [args ...] | '<command>'"; exit 1; }
case "$1" in *.sh) LANE="bash $(printf '%q ' "$@")" ;; *) LANE="$*" ;; esac   # a lane script keeps each argument's quoting
IMAGE_NAME="nlp_project:261021"
IMAGE_FILE="/home/leesangjun/images/nlp_project_261021.tar"
DOCKER_NAME="leesangjun_nlp_${SLURM_JOB_ID:-x}_${RANDOM}"
HOST_UID=$(id -u); HOST_GID=$(id -g)
LOCAL=/local-data/${DOCKER_NAME}

cleanup() {
	docker exec ${DOCKER_NAME} bash -c "chown -R ${HOST_UID}:${HOST_GID} /NAS/SJ/POSTECH/nlp/results ${LOCAL}; find /NAS/SJ/POSTECH/nlp /NAS/SJ/POSTECH/nlp_data -xdev -user root -exec chown ${HOST_UID}:${HOST_GID} {} +" > /dev/null 2>&1
	/home1/leesangjun/script/cleanup.sh "${DOCKER_NAME}" "${IMAGE_NAME}"
	if [ -d "${LOCAL}/stage" ]; then rsync -a --remove-source-files "${LOCAL}/stage/" /home1/leesangjun/SJ/POSTECH/ && echo "staged outputs moved to /home1 $(date -u '+%F %T') UTC"; fi
	if [ -f "${LOCAL}/job.out" ]; then exec 1>&3 2>&4; cat "${LOCAL}/job.out"; fi
	rm -rf "${LOCAL}" 2> /dev/null || docker run --rm --entrypoint "" -v /local-data:/local-data ${IMAGE_NAME} rm -rf "${LOCAL}"   # /local-data is root's: only root can remove the directory itself
	exit
}
trap cleanup 0
trap 'exit 143' TERM INT   # scancel: run cleanup (move the stage) before Slurm's kill

echo "node $(hostname) job ${SLURM_JOB_ID} gpus ${CUDA_VISIBLE_DEVICES} start $(date -u '+%F %T') UTC: ${LANE}"
if ! docker image inspect ${IMAGE_NAME} > /dev/null 2>&1; then
	t0=$(date +%s); docker load -i ${IMAGE_FILE} || exit 1; echo "docker load: $(( $(date +%s) - t0 )) s"
fi
# /local-data is root's: make the job's directory there (as root, through the image) and hand it to the user
docker run --rm --entrypoint "" -v /local-data:/local-data ${IMAGE_NAME} bash -c "mkdir -p ${LOCAL} && chown ${HOST_UID}:${HOST_GID} ${LOCAL}" || exit 1
echo "job output on the node in ${LOCAL}/job.out; appended below when the job ends"
exec 3>&1 4>&2 >> "${LOCAL}/job.out" 2>&1
GPUS=()   # only the GPUs Slurm allocated (none for a CPU-partition job, even on a node that has GPUs)
if [ -n "${SLURM_JOB_GPUS:-}" ] && nvidia-smi -L > /dev/null 2>&1; then
	GPUS=(--gpus "\"device=$(nvidia-smi -L | cut -d '(' -f 2 | awk '{print $2}' | tr -d ')' | paste -s -d, -)\"")
fi
CPULIST=$(grep "Cpus_allowed_list" /proc/self/status | awk '{print $2}')
docker run -itd "${GPUS[@]}" --cpuset-cpus ${CPULIST} --name ${DOCKER_NAME} --ipc=host \
	-v /home1/leesangjun/SJ:/NAS/SJ -v /home/leesangjun/SSD:/SSD -v /home1/leesangjun:/home1/leesangjun -v ${LOCAL}:${LOCAL} \
	${IMAGE_NAME} > /dev/null || exit 1

# Caches stay inside the container (the host /dev/shm is shared by every job on the node through --ipc=host).
docker exec -e PORT=$((20000 + ${SLURM_JOB_ID:-0} % 20000)) -e P=/root/venvs/llm_algo_poc/bin/python \
	-e POC_DATA=/NAS/SJ/POSTECH/nlp_data -e HF_HOME=/root/.cache/hf_home_poc -e VLLM_CACHE_ROOT=/root/.cache/vllm_cache_poc \
	-e VLLM_WORKER_MULTIPROC_METHOD=spawn -e SLURM_JOB_ID=${SLURM_JOB_ID} -e SLURM_ARRAY_TASK_ID=${SLURM_ARRAY_TASK_ID:-} \
	-e POC_LOCAL=${LOCAL} -e PYTHONPATH=/NAS/SJ/POSTECH/nlp/poc/slurm/localio -e PYTHONDONTWRITEBYTECODE=1 \
	${DOCKER_NAME} bash -c "cd /NAS/SJ/POSTECH/nlp && ${LANE}"
echo "lane exit $? end $(date -u '+%F %T') UTC"
