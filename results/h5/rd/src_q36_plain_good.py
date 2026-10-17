import sys
from ortools.sat.python import cp_model

def main():
    input_data = sys.stdin.read().split()
    idx = 0
    n = int(input_data[idx]); idx += 1
    m = int(input_data[idx]); idx += 1
    
    # job_ops[j][op] = (machine, duration)
    job_ops = []
    for j in range(n):
        ops = []
        for op in range(m):
            machine = int(input_data[idx]); idx += 1
            duration = int(input_data[idx]); idx += 1
            ops.append((machine, duration))
        job_ops.append(ops)
    
    model = cp_model.CpModel()
    
    # Variables: start[j][op], end[j][op]
    start = {}
    end = {}
    for j in range(n):
        for op in range(m):
            dur = job_ops[j][op][1]
            start[(j, op)] = model.NewIntVar(0, 10**9, f'start_{j}_{op}')
            end[(j, op)] = model.NewIntVar(0, 10**9, f'end_{j}_{op}')
            model.Add(end[(j, op)] == start[(j, op)] + dur)
    
    # Job precedence: each operation starts after previous one ends
    for j in range(n):
        for op in range(1, m):
            model.Add(start[(j, op)] >= end[(j, op - 1)])
    
    # Machine: no overlap for operations on same machine
    # Group operations by machine
    machine_ops = {}
    for j in range(n):
        for op in range(m):
            machine = job_ops[j][op][0]
            if machine not in machine_ops:
                machine_ops[machine] = []
            machine_ops[machine].append((j, op))
    
    for machine, ops_list in machine_ops.items():
        # Use interval variables for disjunctive constraint
        intervals = []
        for (j, op) in ops_list:
            dur = job_ops[j][op][1]
            intervals.append(model.NewIntervalVar(start[(j, op)], dur, end[(j, op)], f'int_{j}_{op}'))
        model.AddNoOverlap(intervals)
    
    # Objective: minimize makespan
    makespan = model.NewIntVar(0, 10**9, 'makespan')
    # Makespan is the max of all end times
    model.AddMaxEquality(makespan, [end[(j, op)] for j in range(n) for op in range(m)])
    model.Minimize(makespan)
    
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 55.0
    solver.parameters.num_workers = 4
    
    status = solver.Solve(model)
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        for j in range(n):
            starts = []
            for op in range(m):
                starts.append(str(solver.Value(start[(j, op)])))
            print(' '.join(starts))
    else:
        # Fallback: should not happen for valid instances
        pass

if __name__ == '__main__':
    main()
