from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import sys
import math

def euclidean_distance(x1, y1, x2, y2):
    return round(math.hypot(x1 - x2, y1 - y2))

def main():
    lines = sys.stdin.read().splitlines()
    n, capacity, K = map(int, lines[0].split())
    depot_x, depot_y = map(int, lines[1].split())
    
    customers = []
    for i in range(n):
        x, y, d = map(int, lines[i + 2].split())
        customers.append((x, y, d))
    
    # Add depot to the list of nodes
    nodes = [(depot_x, depot_y)] + [c[:2] for c in customers]
    demands = [0] + [c[2] for c in customers]  # depot has 0 demand

    # Create the manager and routing model
    manager = pywrapcp.RoutingIndexManager(n + 1, K, 0)
    routing = pywrapcp.RoutingModel(manager)

    # Define the cost function
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return euclidean_distance(nodes[from_node][0], nodes[from_node][1], nodes[to_node][0], nodes[to_node][1])

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add capacity constraint
    def demand_callback(from_index):
        return demands[manager.IndexToNode(from_index)]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index, 0, [capacity] * K, True, "Capacity")
    
    # Set parameters
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.seconds = 20

    # Solve
    solution = routing.SolveWithParameters(search_parameters)

    # Print routes
    routes = []
    for vehicle_id in range(K):
        index = routing.Start(vehicle_id)
        route = [0]
        while not routing.IsEnd(index):
            index = solution.Value(routing.NextVar(index))
            node_index = manager.IndexToNode(index)
            route.append(node_index)
        route.append(0)
        routes.extend(route)

    print(' '.join(map(str, routes)))

if __name__ == "__main__":
    main()
