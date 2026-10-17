import sys
from ortools.sat.python import cp_model

def main():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    n = int(next(it))
    capacity = int(next(it))
    weights = []
    values = []
    for _ in range(n):
        w = int(next(it))
        v = int(next(it))
        weights.append(w)
        values.append(v)

    model = cp_model.CpModel()
    bools = [model.NewBoolVar(f"x{i}") for i in range(n)]

    # weight constraint
    model.Add(sum(w * b for w, b in zip(weights, bools)) <= capacity)

    # objective: maximize value
    model.Maximize(sum(v * b for v, b in zip(values, bools)))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 20.0

    status = solver.Solve(model)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        chosen = [str(i) for i, b in enumerate(bools) if solver.Value(b) == 1]
        print(" ".join(chosen))
    else:
        # no feasible solution found
        print()

if __name__ == "__main__":
    main()
