#!/usr/bin/env python3
import sys
from ortools.sat.python import cp_model

def main():
    data = sys.stdin.read().strip().splitlines()
    if not data:
        return
    n, m = map(int, data[0].split())
    jobs_data = []
    for line in data[1:1+n]:
        parts = line.split()
        ops = []
        for i in range(0, len(parts), 2):
            machine = int(parts[i])
            duration = int(parts[i+1])
            ops.append((machine, duration))
        jobs_data.append(ops)

    model = cp_model.CpModel()

    # Create interval variables
    all_intervals = []
    machine_to_intervals = [[] for _ in range(m)]
    start_vars = [[None] * m for _ in range(n)]
    for job_id, ops in enumerate(jobs_data):
        for op_id, (machine, dur) in enumerate(ops):
            suffix = f'j{job_id}_o{op_id}'
            start = model.NewIntVar(0, sum(d for _, d in ops), f'start_{suffix}')
            end = model.NewIntVar(0, sum(d for _, d in ops), f'end_{suffix}')
            interval = model.NewIntervalVar(start, dur, end, f'interval_{suffix}')
            start_vars[job_id][op_id] = start
            all_intervals.append(interval)
            machine_to_intervals[machine].append(interval)

    # Job precedence constraints
    for job_id, ops in enumerate(jobs_data):
        for op_id in range(1, len(ops)):
            model.Add(start_vars[job_id][op_id] >=
                       start_vars[job_id][op_id-1] + ops[op_id-1][1])

    # Machine disjunctive constraints
    for machine in range(m):
        if machine_to_intervals[machine]:
            model.AddNoOverlap(machine_to_intervals[machine])

    # Makespan variable
    makespan = model.NewIntVar(0, sum(d for ops in jobs_data for _, d in ops), 'makespan')
    last_ops = []
    for job_id, ops in enumerate(jobs_data):
        op_id = len(ops) - 1
        last_ops.append(start_vars[job_id][op_id] + ops[op_id][1])
    model.AddMaxEquality(makespan, last_ops)
    model.Minimize(makespan)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 55.0
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        out_lines = []
        for job_id in range(n):
            times = [str(solver.Value(start_vars[job_id][op_id]))
                     for op_id in range(m)]
            out_lines.append(' '.join(times))
        sys.stdout.write('\n'.join(out_lines))
    else:
        print('No solution found', file=sys.stderr)

if __name__ == '__main__':
    main()
