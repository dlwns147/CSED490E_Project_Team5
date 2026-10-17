import sys
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

def main():
    input_data = sys.stdin.read().strip().split('\n')
    n = int(input_data[0])
    cities = []
    for i in range(1, n + 1):
        x, y = map(int, input_data[i].split())
        cities.append((x, y))
    
    # Compute distance matrix with Euclidean distance rounded to nearest integer
    D = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            dx = cities[i][0] - cities[j][0]
            dy = cities[i][1] - cities[j][1]
            dist = round((dx * dx + dy * dy) ** 0.5)
            D[i][j] = dist
    
    # Create routing index manager
    mgr = pywrapcp.RoutingIndexManager(n, 1, 0)
    r = pywrapcp.RoutingModel(mgr)
    
    def cost(i, j):
        return D[mgr.IndexToNode(i)][mgr.IndexToNode(j)]
    
    cb = r.RegisterTransitCallback(cost)
    r.SetArcCostEvaluatorOfAllVehicles(cb)
    
    # Set search parameters
    p = pywrapcp.DefaultRoutingSearchParameters()
    p.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    p.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    p.time_limit.seconds = 20
    
    # Solve
    sol = r.SolveWithParameters(p)
    
    if sol is not None:
        i = r.Start(0)
        tour = []
        while not r.IsEnd(i):
            tour.append(mgr.IndexToNode(i))
            i = sol.Value(r.NextVar(i))
        
        print(' '.join(map(str, tour)))

if __name__ == '__main__':
    main()
