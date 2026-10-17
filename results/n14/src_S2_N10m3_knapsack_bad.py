import sys
from ortools.sat.python import cp_model

def solve():
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    
    iterator = iter(input_data)
    n = int(next(iterator))
    capacity = int(next(iterator))
    
    weights = []
    values = []
    
    for i in range(n):
        w = int(next(iterator))
        v = int(next(iterator))
        weights.append(w)
        values.append(v)
    
    model = cp_model.CpModel()
    
    # Binary variables for each item
    x = [model.NewBoolVar(f'x{i}') for i in range(n)]
    
    # Constraint: total weight <= capacity
    model.Add(sum(weights[i] * x[i] for i in range(n)) <= capacity)
    
    # Maximize total value
    objective = model.NewIntVar(0, sum(values), 'obj')
    model.AddMaxEquality(objective, [values[i] * x[i] for i in range(n)])
    model.Maximize(objective)
    
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 20
    
    status = solver.Solve(model)
    
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        chosen = [i for i in range(n) if solver.Value(x[i]) == 1]
        print(' '.join(map(str, chosen)))
    else:
        # Should not happen with valid input
        pass

if __name__ == '__main__':
    solve()
