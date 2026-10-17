from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import sys
import math

def distance(x1, y1, x2, y2):
    return round(math.hypot(x1 - x2, y1 - y2))

def main():
    data = [list(map(int, line.split())) for line in sys.stdin.read().splitlines()]
    n = data[0][0]
    cities = data[1:]

    # Create the manager and routing model
    manager = pywrapcp.RoutingIndexManager(n, 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance(cities[from_node][0], cities[from_node][1], cities[to_node][0], cities[to_node][1])

    transit_callback_index = routing.RegisterTransitCallback(callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Set search parameters
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.seconds = 20

    # Solve the problem
    solution = routing.SolveWithParameters(search_parameters)

    if solution:
        # Build the tour
        index = routing.Start(0)
        tour = [manager.IndexToNode(index)]
        while not routing.IsEnd(index):
            index = solution.Value(routing.NextVar(index))
            tour.append(manager.IndexToNode(index))
        print(' '.join(map(str, tour)))

if __name__ == "__main__":
    main()
