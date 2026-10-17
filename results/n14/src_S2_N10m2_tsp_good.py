#!/usr/bin/env python3
"""
Travelling salesman solver using OR-Tools Routing library.
Reads: first line n, then n lines "x y".
Outputs a single line with a permutation of 0..n-1 that is a tour
(minimising total Euclidean distance rounded to nearest integer).
The solver is limited to 20 seconds.
"""

import sys
import math
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

def read_input():
    data = sys.stdin.read().strip().split()
    if not data:
        return []
    it = iter(data)
    n = int(next(it))
    coords = [(int(next(it)), int(next(it))) for _ in range(n)]
    return coords

def distance_matrix(coords):
    n = len(coords)
    D = [[0]*n for _ in range(n)]
    for i in range(n):
        xi, yi = coords[i]
        for j in range(i+1, n):
            xj, yj = coords[j]
            d = int(round(math.hypot(xi - xj, yi - yj)))
            D[i][j] = D[j][i] = d
    return D

def solve_tsp(coords, time_limit_sec=20):
    n = len(coords)
    D = distance_matrix(coords)

    # Routing setup
    manager = pywrapcp.RoutingIndexManager(n, 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def transit_callback(i, j):
        return D[manager.IndexToNode(i)][manager.IndexToNode(j)]

    transit_cb_index = routing.RegisterTransitCallback(transit_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_cb_index)

    # Parameters
    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    search_params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    search_params.time_limit.seconds = time_limit_sec

    solution = routing.SolveWithParameters(search_params)

    if solution:
        # Extract tour
        index = routing.Start(0)
        tour = []
        while not routing.IsEnd(index):
            tour.append(manager.IndexToNode(index))
            index = solution.Value(routing.NextVar(index))
        return tour
    else:
        return None

def main():
    coords = read_input()
    if not coords:
        return
    tour = solve_tsp(coords, time_limit_sec=20)
    if tour is None:
        print("No solution found")
    else:
        print(' '.join(map(str, tour)))

if __name__ == "__main__":
    main()
