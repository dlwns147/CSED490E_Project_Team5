import sys
from ortools.sat.python import cp_model

def read_instance():
    input_lines = sys.stdin.read().strip().splitlines()
    n, m = map(int, input_lines[0].split())
    jobs = []
    for i in range(n):
        operations = []
        for j in range(m):
            machine, duration = map(int, input_lines[i + 1].split()[j * 2 : j * 2 + 2])
            operations.append((machine, duration))
        jobs.append(operations)
    return n, m, jobs

def solve_job_shop():
    n, m, jobs = read_instance()
    model = cp_model.CpModel()

    # Create variables for each operation's start time
    start_times = [[model.NewIntVar(0, 10**9, f'start_job_{i}_op_{j}') for j in range(m)] for i in range(n)]

    # Create variables for each operation's end time
    end_times = [[start_times[i][j] + jobs[i][j][1] for j in range(m)] for i in range(n)]

    # Ensure each job's operations are scheduled in the correct order
    for i in range(n):
        for j in range(m - 1):
            model.Add(start_times[i][j + 1] >= end_times[i][j])

    # Ensure that on each machine, operations do not overlap
    machine_to_operations = [{} for _ in range(m)]
    for i in range(n):
        for j in range(m):
            machine, duration = jobs[i][j]
            op = model.NewIntervalVar(start_times[i][j], duration, end_times[i][j], f'op_job_{i}_op_{j}')
            machine_to_operations[machine].setdefault(op, []).append((i, j))

    for machine in range(m):
        operations = machine_to_operations[machine].keys()
        model.AddNoOverlap(list(operations))

    # Minimize the makespan (the end time of the last operation)
    makespan = model.NewIntVar(0, 10**9, 'makespan')
    model.AddMaxEquality(makespan, [end_times[i][m - 1] for i in range(n)])
    model.Minimize(makespan)

    # Solve the model
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0
    status = solver.Solve(model)

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        for i in range(n):
            print(' '.join(str(solver.Value(start_times[i][j])) for j in range(m)))
    else:
        print("No solution found.")

if __name__ == "__main__":
    solve_job_shop()
