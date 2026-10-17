import sys
from ortools.sat.python import cp_model

def main():
    input_lines = sys.stdin.read().splitlines()
    n, capacity = map(int, input_lines[0].split())
    items = [tuple(map(int, line.split())) for line in input_lines[1:]]

    model = cp_model.CpModel()

    # Variables
    select = [model.NewBoolVar(f'select_{i}') for i in range(n)]

    # Weight constraint
    model.Add(sum(select[i] * items[i][0] for i in range(n)) <= capacity)

    # Maximize total value
    model.Maximize(sum(select[i] * items[i][1] for i in range(n)))

    # Solver
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 20
    status = solver.Solve(model)

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        chosen = [i for i in range(n) if solver.Value(select[i])]
        print(' '.join(map(str, chosen)))

if __name__ == "__main__":
    main()
