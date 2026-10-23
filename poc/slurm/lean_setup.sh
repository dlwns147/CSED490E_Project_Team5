#!/bin/bash
# Lean 4 v4.15.0 + Mathlib v4.15.0 for poc/run_lean.py on the Slurm cluster (proof direction, 2026-10-23): elan in $POC_DATA/elan, the
# Lake project in $POC_DATA/mf2f (Mathlib's prebuilt cache, no local build), then one test file. Run inside the image:
#   sbatch -J lean_setup poc/slurm/job.sh poc/slurm/lean_setup.sh
set -e
export ELAN_HOME=$POC_DATA/elan PATH=$POC_DATA/elan/bin:$PATH
L=results/x4/lean_setup.log; mkdir -p results/x4
{
which git curl
[ -x $ELAN_HOME/bin/elan ] || curl -sSfL https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | sh -s -- -y --no-modify-path --default-toolchain none
mkdir -p $POC_DATA/mf2f && cd $POC_DATA/mf2f
echo "leanprover/lean4:v4.15.0" > lean-toolchain
cat > lakefile.lean <<'LK'
import Lake
open Lake DSL
package mf2f
require mathlib from git "https://github.com/leanprover-community/mathlib4" @ "v4.15.0"
LK
[ -d .lake/packages/mathlib ] || lake update
lake exe cache get
printf 'import Mathlib\nexample (a b : ℕ) : a + b = b + a := by omega\n' > Test.lean
time lake env lean Test.lean && echo "LEAN OK"
du -sh $POC_DATA/mf2f $POC_DATA/elan
chown -R $(stat -c %u:%g /NAS/SJ/POSTECH/nlp) $POC_DATA/mf2f $POC_DATA/elan
} >> /NAS/SJ/POSTECH/nlp/$L 2>&1
