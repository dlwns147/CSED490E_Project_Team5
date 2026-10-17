from ortools.sat.python import cp_model

import sys

def solve_knapsack():
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
    
    # Create binary variables for each item
    x = [model.NewBoolVar(f'x_{i}') for i in range(n)]
    
    # Constraint: total weight <= capacity
    model.Add(sum(weights[i] * x[i] for i in range(n)) <= capacity)
    
    # Objective: maximize total value
    total_value = sum(values[i] * x[i] for i in range(n))
    model.Maximize(total_value)
    
    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 20
    
    status = solver.Solve(model)
    
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        chosen = [str(i) for i in range(n) if solver.Value(x[i]) == 1]
        print(' '.join(chosen))

if __name__ == '__main__':
    solve_knapsack()
