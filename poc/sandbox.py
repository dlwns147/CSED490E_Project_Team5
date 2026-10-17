"""Minimal execution sandbox for untrusted Python solutions.

Each run is a fresh `python3 -I` subprocess in a throwaway directory with CPU-time,
address-space, file-size and process-count rlimits. Good enough for a PoC on a
single-user box; for anything shared, wrap in a container (e.g. bubblewrap/nsjail).
"""
import os
import resource
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

PYTHON = os.environ.get("POC_PYTHON", sys.executable)


@dataclass
class RunResult:
    status: str  # ok | re (runtime error) | tle | mle
    stdout: str
    stderr: str


def _limits(cpu_s: float, mem_bytes: int):
    def fn():
        os.setsid()
        resource.setrlimit(resource.RLIMIT_CPU, (int(cpu_s) + 1, int(cpu_s) + 2))
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        resource.setrlimit(resource.RLIMIT_FSIZE, (64 << 20, 64 << 20))
        resource.setrlimit(resource.RLIMIT_NPROC, (512, 512))
    return fn


def run_python(code: str, stdin: str, timeout: float = 4.0, mem_bytes: int = 1 << 30, cpu_s: float | None = None) -> RunResult:
    """cpu_s: CPU-time limit (default = timeout). Multi-threaded solvers need cpu_s >> timeout: with RLIMIT_CPU = timeout a CP-SAT
    program with 8-64 workers is killed by SIGXCPU after a few seconds of wall time (2026-10-14 H5 bug: reported as 'tle')."""
    with tempfile.TemporaryDirectory(prefix="sbx_") as d:
        path = os.path.join(d, "main.py")
        with open(path, "w") as f:
            f.write(code)
        try:
            p = subprocess.run(
                [PYTHON, "-I", path], input=stdin, capture_output=True, text=True,
                timeout=timeout, cwd=d, preexec_fn=_limits(cpu_s or timeout, mem_bytes),
                env={"PATH": "/usr/bin:/bin", "PYTHONHASHSEED": "0",
                 "MALLOC_ARENA_MAX": "2"},  # multi-threaded solvers (CP-SAT: 64 workers) blew RLIMIT_AS via per-thread arenas
            )
        except subprocess.TimeoutExpired:
            return RunResult("tle", "", "")
        except Exception as e:  # e.g. invalid unicode in output
            return RunResult("re", "", repr(e))
        if p.returncode != 0:
            st = "mle" if "MemoryError" in p.stderr else ("tle" if p.returncode in (-9, -24) else "re")
            return RunResult(st, p.stdout, p.stderr[-2000:])
        return RunResult("ok", p.stdout, p.stderr[-2000:])


def norm(out: str) -> list[str]:
    """Token-level normalisation used by most CF checkers (whitespace-insensitive)."""
    return out.split()


def same_output(a: str, b: str) -> bool:
    ta, tb = norm(a), norm(b)
    if ta == tb:
        return True
    if len(ta) != len(tb):
        return False
    # tolerate float formatting differences (1e-6 relative/absolute)
    for x, y in zip(ta, tb):
        if x == y:
            continue
        try:
            fx, fy = float(x), float(y)
        except ValueError:
            return False
        if abs(fx - fy) > 1e-6 * max(1.0, abs(fy)):
            return False
    return True


def run_many(jobs, workers: int = 32):
    """jobs: list of (code, stdin, timeout). Returns list[RunResult] in order."""
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(lambda j: run_python(*j), jobs))
