import sys
import math
from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2

def solve():
    # Read all input from stdin
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    
    iterator = iter(input_data)
    try:
        n = int(next(iterator))
    except StopIteration:
        return

    coords = []
    for _ in range(n):
        try:
            x = int(next(iterator))
            y = int(next(iterator))
            coords.append((x, y))
        except StopIteration:
            break

    # Compute distance matrix
    # Distance is Euclidean distance rounded to nearest integer
    dist = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            dx = coords[i][0] - coords[j][0]
            dy = coords[i][1] - coords[j][1]
            d = math.sqrt(dx*dx + dy*dy)
            dist[i][j] = round(d)

    # Create the routing index manager
    # n locations, 1 vehicle, start and end at 0
    manager = pywrapcp.RoutingIndexManager(n, 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    # Define distance callback
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return dist[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Search parameters
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.seconds = 20

    # Solve
    status = routing.SolveWithParameters(search_parameters)

    # Status codes: UNKNOWN=0, FEASIBLE=1, OPTIMAL=2, INFEASIBLE=3
    # We proceed if we found a feasible or optimal solution
    if status in (1, 2):
        index = routing.Start(0)
        tour = []
        while True:
            node = manager.IndexToNode(index)
            # If we encounter a node already in the tour, we have completed the cycle
            if node in tour:
                break
            tour.append(node)
            # Move to next node
            # routing.Value returns the integer value of the variable
            next_index = routing.Value(routing.NextVar(index))
            # Safety break to prevent infinite loops in case of unexpected behavior
            if len(tour) > n:
                break
            index = next_index
        print(*(tour))
    else:
        # Fallback: print 0..n-1 if no solution found (should not happen for valid TSP)
        print(*(range(n)))

if __name__ == '__main__':
    solve()
