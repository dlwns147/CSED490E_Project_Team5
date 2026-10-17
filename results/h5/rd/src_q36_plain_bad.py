import sys
from ortools.sat.python import cp_model


def main():
    input_data = sys.stdin.read().split()
    idx = 0
    n = int(input_data[idx]); idx += 1
    m = int(input_data[idx]); idx += 1

    # operations[j][k] = (machine, duration)
    operations = []
    for j in range(n):
        job_ops = []
        for k in range(m):
            machine = int(input_data[idx]); idx += 1
            duration = int(input_data[idx]); idx += 1
            job_ops.append((machine, duration))
        operations.append(job_ops)

    model = cp_model.CpModel()

    # For each job j and operation k, define start and end variables
    # Also define the machine for each operation
    starts = []
    ends = []
    machines_used = []

    for j in range(n):
        job_starts = []
        job_ends = []
        job_machines = []
        for k in range(m):
            machine, duration = operations[j][k]
            s = model.NewIntVar(0, 10**9, f"s_{j}_{k}")
            e = model.NewIntVar(0, 10**9, f"e_{j}_{k}")
            model.Add(e == s + duration)
            job_starts.append(s)
            job_ends.append(e)
            job_machines.append(machine)
        starts.append(job_starts)
        ends.append(job_ends)
        machines_used.append(job_machines)

    # Job precedence constraints: operation k of job j starts after operation k-1 of job j ends
    for j in range(n):
        for k in range(1, m):
            model.Add(starts[j][k] >= ends[j][k - 1])

    # Machine capacity: for each machine, all operations on that machine must not overlap
    # Group operations by machine
    machine_ops = {}
    for j in range(n):
        for k in range(m):
            machine = machines_used[j][k]
            if machine not in machine_ops:
                machine_ops[machine] = []
            machine_ops[machine].append((j, k))

    for machine, ops in machine_ops.items():
        # Create interval variables for each operation on this machine
        intervals = []
        for j, k in ops:
            s = starts[j][k]
            e = ends[j][k]
            d = e - s  # duration
            interval = model.NewIntervalVar(s, d, e, f"interval_{j}_{k}")
            intervals.append(interval)
        # No overlap on this machine
        model.AddNoOverlap(intervals)

    # Minimize makespan
    all_ends = [ends[j][m - 1] for j in range(n)]
    makespan = model.NewIntVar(0, 10**9, "makespan")
    model.AddMaxEquality(makespan, all_ends)
    model.Minimize(makespan)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 55.0
    solver.parameters.num_workers = 1  # Use single worker for consistency, or more for speed
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        for j in range(n):
            line = []
            for k in range(m):
                line.append(str(solver.Value(starts[j][k])))
            print(" ".join(line))
    else:
        # Should not happen for valid instances
        pass


if __name__ == "__main__":
    main()
