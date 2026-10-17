import sys
import math
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

def main():
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    
    iterator = iter(input_data)
    
    try:
        n = int(next(iterator))
        capacity = int(next(iterator))
        K = int(next(iterator))
        
        depot_x = int(next(iterator))
        depot_y = int(next(iterator))
        
        customers = []
        for i in range(1, n + 1):
            cx = int(next(iterator))
            cy = int(next(iterator))
            demand = int(next(iterator))
            customers.append((cx, cy, demand))
    except StopIteration:
        return
    
    # Build distance matrix
    # Nodes: 0 is depot, 1..n are customers
    num_nodes = n + 1
    coords = [(depot_x, depot_y)] + [(c[0], c[1]) for c in customers]
    demands = [0] + [c[2] for c in customers]
    
    D = [[0] * num_nodes for _ in range(num_nodes)]
    for i in range(num_nodes):
        for j in range(num_nodes):
            if i == j:
                D[i][j] = 0
            else:
                dx = coords[i][0] - coords[j][0]
                dy = coords[i][1] - coords[j][1]
                dist = math.sqrt(dx * dx + dy * dy)
                D[i][j] = round(dist)
    
    # Create index manager
    mgr = pywrapcp.RoutingIndexManager(num_nodes, K, 0)
    r = pywrapcp.RoutingModel(mgr)
    
    # Define cost function
    def cost(i, j):
        u = mgr.IndexToNode(i)
        v = mgr.IndexToNode(j)
        return D[u][v]
    
    cb = r.RegisterTransitCallback(cost)
    r.SetArcCostEvaluatorOfAllVehicles(cb)
    
    # Define demand function and add capacity constraint
    def demand(i):
        node = mgr.IndexToNode(i)
        return demands[node]
    
    dcb = r.RegisterUnaryTransitCallback(demand)
    r.AddDimensionWithVehicleCapacity(dcb, 0, [capacity] * K, True, "Load")
    
    # Set search parameters
    p = pywrapcp.DefaultRoutingSearchParameters()
    p.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    p.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    p.time_limit.seconds = 20
    
    # Solve
    sol = r.SolveWithParameters(p)
    
    if sol is None:
        return
    
    # Extract routes
    routes = []
    for v in range(K):
        i = r.Start(v)
        route = []
        while not r.IsEnd(i):
            node = mgr.IndexToNode(i)
            route.append(node)
            i = sol.Value(r.NextVar(i))
        if route:  # Only add non-empty routes
            routes.append(route)
    
    # Print routes as one sequence
    output = []
    for route in routes:
        output.append(0)
        output.extend(route)
        output.append(0)
    
    print(' '.join(map(str, output)))

if __name__ == '__main__':
    main()
