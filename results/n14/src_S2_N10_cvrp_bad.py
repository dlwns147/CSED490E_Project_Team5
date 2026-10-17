from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import sys
import math

def main():
    input_lines = [line.strip() for line in sys.stdin if line.strip()]
    n, capacity, K = map(int, input_lines[0].split())
    depot_x, depot_y = map(int, input_lines[1].split())
    customers = []
    for i in range(n):
        x, y, demand = map(int, input_lines[i + 2].split())
        customers.append((x, y, demand))

    # Add depot as node 0
    nodes = [(depot_x, depot_y)] + customers

    # Compute Euclidean distances rounded to nearest integer
    def distance(i, j):
        x1, y1 = nodes[i]
        x2, y2 = nodes[j]
        return round(math.hypot(x1 - x2, y1 - y2))

    # Demands for each node (0 is depot with 0 demand)
    demands = [0] + [d for _, _, d in customers]

    # Create routing index manager
    manager = pywrapcp.RoutingIndexManager(n + 1, K, 0)
    routing = pywrapcp.RoutingModel(manager)

    # Define cost function between nodes
    def cost_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance(from_node, to_node)

    transit_callback_index = routing.RegisterTransitCallback(cost_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add capacity constraint
    def demand_callback(manager, routing_index):
        return demands[manager.IndexToNode(routing_index)]

    demand_callback_index = routing.RegisterUnaryTransitCallback(
        lambda index: demand_callback(manager, index)
    )
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index, 0, [capacity] * K, True, "Capacity"
    )

    # Set search parameters
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.seconds = 20

    # Solve
    solution = routing.SolveWithParameters(search_parameters)

    # Output the solution
    if solution:
        routes = []
        for vehicle_id in range(K):
            index = routing.Start(vehicle_id)
            route = [0]
            while not routing.IsEnd(index):
                index = solution.Value(routing.NextVar(index))
                node = manager.IndexToNode(index)
                route.append(node)
            route.append(0)
            routes.extend(route)

        print(' '.join(map(str, routes)))

if __name__ == "__main__":
    main()
