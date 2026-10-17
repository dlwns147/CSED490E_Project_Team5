#!/usr/bin/env python3
# Job‑shop scheduling using OR‑Tools CP‑SAT

import sys
from ortools.sat.python import cp_model

def main() -> None:
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    n = int(next(it))
    m = int(next(it))

    # Read job operations: list of (machine, duration) for each job
    jobs = []
    for _ in range(n):
        ops = []
        for _ in range(m):
            machine = int(next(it))
            duration = int(next(it))
            ops.append((machine, duration))
        jobs.append(ops)

    model = cp_model.CpModel()

    horizon = sum(d for job in jobs for _, d in job)  # upper bound on makespan

    # Variables
    start = [[None] * m for _ in range(n)]
    end = [[None] * m for _ in range(n)]
    interval = [[None] * m for _ in range(n)]

    for j, job in enumerate(jobs):
        for o, (machine, duration) in enumerate(job):
            s = model.NewIntVar(0, horizon, f'start_{j}_{o}')
            e = model.NewIntVar(0, horizon, f'end_{j}_{o}')
            iv = model.NewIntervalVar(s, duration, e, f'interval_{j}_{o}')
            start[j][o] = s
            end[j][o] = e
            interval[j][o] = iv

    # Precedence constraints within each job
    for j, job in enumerate(jobs):
        for o in range(1, m):
            model.Add(start[j][o] >= end[j][o - 1])

    # Machine constraints: no overlap on same machine
    for machine in range(m):
        # collect all operations on this machine
        ops_on_machine = []
        for j, job in enumerate(jobs):
            for o, (mach, _) in enumerate(job):
                if mach == machine:
                    ops_on_machine.append(interval[j][o])
        model.AddNoOverlap(ops_on_machine)

    # Makespan variable
    makespan = model.NewIntVar(0, horizon, 'makespan')
    all_ends = [end[j][m - 1] for j in range(n)]
    model.AddMaxEquality(makespan, all_ends)

    # Objective: minimize makespan
    model.Minimize(makespan)

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 55.0  # leave some headroom
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        out_lines = []
        for j in range(n):
            times = [str(solver.Value(start[j][o])) for o in range(m)]
            out_lines.append(' '.join(times))
        sys.stdout.write('\n'.join(out_lines))
    else:
        sys.stderr.write('No solution found.\n')

if __name__ == '__main__':
    main()
