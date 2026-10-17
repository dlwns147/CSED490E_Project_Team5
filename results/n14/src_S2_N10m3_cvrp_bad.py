import sys
import math
from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2

def main():
    input_data = sys.stdin.read().strip().split('\n')
    idx = 0
    n, capacity, K = map(int, input_data[idx].split())
    idx += 1
    depot_x, depot_y = map(int, input_data[idx].split())
    idx += 1
    
    customers = []
    for i in range(n):
        parts = input_data[idx].split()
        x, y, demand = int(parts[0]), int(parts[1]), int(parts[2])
        customers.append((x, y, demand))
        idx += 1
    
    # Total nodes: depot (0) + n customers (1..n)
    total_nodes = n + 1
    
    # Compute distance matrix with Euclidean distance rounded to nearest integer
    # Node 0 is depot, nodes 1..n are customers
    dist_matrix = [[0] * total_nodes for _ in range(total_nodes)]
    
    all_points = [(depot_x, depot_y)] + [(c[0], c[1]) for c in customers]
    
    for i in range(total_nodes):
        for j in range(total_nodes):
            if i == j:
                dist_matrix[i][j] = 0
            else:
                dx = all_points[i][0] - all_points[j][0]
                dy = all_points[i][1] - all_points[j][1]
                dist = math.sqrt(dx * dx + dy * dy)
                dist_matrix[i][j] = round(dist)
    
    # Create routing index manager
    # num_nodes = total_nodes, num_vehicles = K, depot = 0
    manager = pywrapcp.RoutingIndexManager(total_nodes, K, 0)
    routing = pywrapcp.RoutingModel(manager)
    
    # Define cost function
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return dist_matrix[from_node][to_node]
    
    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    
    # Add capacity constraint
    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        if from_node == 0:
            return 0
        return customers[from_node - 1][2]
    
    demand_callback_index = routing.RegisterTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # null capacity slack
        [capacity] * K,  # vehicle maximum capacities
        True,  # start cumul to zero
        'Capacity'
    )
    
    # Search parameters
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.seconds = 20
    
    # Solve
    solution = routing.SolveWithParameters(search_parameters)
    
    if solution:
        # Extract routes
        routes = []
        for vehicle_id in range(K):
            index = routing.Start(vehicle_id)
            route_nodes = []
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                route_nodes.append(node)
                index = solution.Value(routing.NextVar(index))
            if route_nodes:
                routes.append(route_nodes)
        
        # Print routes as one line: depot 0, then route nodes, then 0 for each route, all separated by spaces
        output_parts = []
        for route in routes:
            output_parts.append(0)
            for node in route:
                output_parts.append(node)
            output_parts.append(0)
        
        print(' '.join(map(str, output_parts)))
    else:
        # No solution found
        pass

if __name__ == '__main__':
    main()
