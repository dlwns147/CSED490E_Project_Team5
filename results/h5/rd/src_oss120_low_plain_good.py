#!/usr/bin/env python3
import sys
from ortools.sat.python import cp_model

def main() -> None:
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    n = int(next(it))          # number of jobs
    m = int(next(it))          # number of machines

    # jobs[j][k] = (machine, duration) for the k‑th operation of job j
    jobs = []
    for _ in range(n):
        ops = []
        for _ in range(m):
            machine = int(next(it))
            duration = int(next(it))
            ops.append((machine, duration))
        jobs.append(ops)

    model = cp_model.CpModel()
    horizon = sum(d for job in jobs for _, d in job)   # simple upper bound

    # start[j][k] – start time of k‑th operation of job j
    start = [[model.NewIntVar(0, horizon, f'start_{j}_{k}') for k in range(m)]
             for j in range(n)]
    # end[j][k] – end time of the same operation
    end = [[model.NewIntVar(0, horizon, f'end_{j}_{k}') for k in range(m)]
           for j in range(n)]

    # link start/end with duration
    for j in range(n):
        for k, (_, dur) in enumerate(jobs[j]):
            model.Add(end[j][k] == start[j][k] + dur)

    # precedence inside each job
    for j in range(n):
        for k in range(1, m):
            model.Add(start[j][k] >= end[j][k-1])

    # machine capacity constraints (disjunctive)
    # collect all intervals per machine
    intervals_per_machine = [[] for _ in range(m)]
    for j in range(n):
        for k, (mach, _) in enumerate(jobs[j]):
            interval = model.NewIntervalVar(start[j][k], jobs[j][k][1],
                                            end[j][k], f'interval_{j}_{k}')
            intervals_per_machine[mach].append(interval)

    for mach in range(m):
        model.AddNoOverlap(intervals_per_machine[mach])

    # makespan variable
    makespan = model.NewIntVar(0, horizon, 'makespan')
    all_ends = [end[j][m-1] for j in range(n)]   # last operation of each job
    model.AddMaxEquality(makespan, all_ends)
    model.Minimize(makespan)

    # solver
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 55.0   # leave a margin
    solver.parameters.num_search_workers = 8       # use parallelism if available
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # fallback: simple serial schedule (never happens for valid input)
        for j in range(n):
            cur = 0
            out = []
            for k, (_, dur) in enumerate(jobs[j]):
                out.append(str(cur))
                cur += dur
            print(' '.join(out))
        return

    # output start times in the order given in the input
    for j in range(n):
        times = [str(solver.Value(start[j][k])) for k in range(m)]
        print(' '.join(times))

if __name__ == '__main__':
    main()
