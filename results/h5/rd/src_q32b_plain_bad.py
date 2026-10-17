import sys
from ortools.sat.python import cp_model

def read_instance():
    lines = sys.stdin.read().strip().split('\n')
    n, m = map(int, lines[0].split())
    jobs = []
    for line in lines[1:]:
        ops = []
        for i in range(0, 2 * m, 2):
            machine = int(line[i])
            duration = int(line[i + 1])
            ops.append((machine, duration))
        jobs.append(ops)
    return n, m, jobs

def main():
    n, m, jobs = read_instance()
    model = cp_model.CpModel()

    # Variables: start_time[j][o] is the start time of operation o in job j
    start_time = [[model.NewIntVar(0, 1_000_000, f'start_job_{j}_op_{o}') for o in range(m)] for j in range(n)]

    # Constraints for each job's operations: sequential processing
    for j in range(n):
        for o in range(1, m):
            model.Add(start_time[j][o] >= start_time[j][o - 1] + jobs[j][o - 1][1])

    # Constraints for each machine: no overlapping operations
    for machine_id in range(m):
        machine_ops = []
        for j in range(n):
            for o in range(m):
                if jobs[j][o][0] == machine_id:
                    op_duration = jobs[j][o][1]
                    end_var = start_time[j][o] + op_duration
                    machine_ops.append((start_time[j][o], end_var))
        # Add no overlap constraints using the 'AddNoOverlap' constraint
        if machine_ops:
            intervals = []
            for start, end in machine_ops:
                intervals.append(model.NewIntervalVar(start, end - start, f'interval_{machine_id}_{len(intervals)}'))
            model.AddNoOverlap(intervals)

    # Objective: minimize the makespan (max end time of all operations)
    makespan = model.NewIntVar(0, 1_000_000, 'makespan')
    model.AddMaxEquality(makespan, [start_time[j][m - 1] + jobs[j][m - 1][1] for j in range(n)])
    model.Minimize(makespan)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0
    status = solver.Solve(model)

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        for j in range(n):
            print(' '.join(str(solver.Value(start_time[j][o])) for o in range(m)))
    else:
        print("No solution found.")

if __name__ == '__main__':
    main()
