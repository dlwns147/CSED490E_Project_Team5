from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import sys
import math

def euclidean_distance(x1, y1, x2, y2):
    return round(math.hypot(x1 - x2, y1 - y2))

def main():
    input_lines = sys.stdin.read().splitlines()
    n = int(input_lines[0])
    cities = []
    for i in range(n):
        x, y = map(int, input_lines[i+1].split())
        cities.append((x, y))

    # Create the manager and routing model
    manager = pywrapcp.RoutingIndexManager(n, 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    # Define the cost function for the TSP
    def cost_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return euclidean_distance(cities[from_node][0], cities[from_node][1],
                                  cities[to_node][0], cities[to_node][1])

    transit_callback_index = routing.RegisterTransitCallback(cost_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Set search parameters
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    search_parameters.time_limit.FromSeconds(20)

    # Solve the TSP
    solution = routing.SolveWithParameters(search_parameters)

    if solution:
        # Extract the tour
        index = routing.Start(0)
        tour = [manager.IndexToNode(index)]
        while not routing.IsEnd(index):
            index = solution.Value(routing.NextVar(index))
            tour.append(manager.IndexToNode(index))
        # Print the tour (excluding the final return to the start)
        print(' '.join(map(str, tour[:-1])))

if __name__ == "__main__":
    main()
