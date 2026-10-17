#!/usr/bin/env python3
import sys
import math
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

def main():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    it = iter(data)
    n = int(next(it))
    capacity = int(next(it))
    K = int(next(it))
    depot_x = int(next(it))
    depot_y = int(next(it))
    nodes = [(depot_x, depot_y)]  # node 0 = depot
    demands = [0]
    for _ in range(n):
        x = int(next(it)); y = int(next(it)); d = int(next(it))
        nodes.append((x, y))
        demands.append(d)

    # distance matrix (rounded to nearest int)
    D = [[0]*(n+1) for _ in range(n+1)]
    for i in range(n+1):
        xi, yi = nodes[i]
        for j in range(n+1):
            if i==j: continue
            xj, yj = nodes[j]
            D[i][j] = int(round(math.hypot(xi-xj, yi-yj)))

    # OR-Tools model
    mgr = pywrapcp.RoutingIndexManager(n+1, K, 0)
    r = pywrapcp.RoutingModel(mgr)

    def dist_callback(i, j):
        return D[mgr.IndexToNode(i)][mgr.IndexToNode(j)]
    transit_cb = r.RegisterTransitCallback(dist_callback)
    r.SetArcCostEvaluatorOfAllVehicles(transit_cb)

    def demand_callback(i):
        return demands[mgr.IndexToNode(i)]
    demand_cb = r.RegisterUnaryTransitCallback(demand_callback)
    r.AddDimensionWithVehicleCapacity(
        demand_cb, 0, [capacity]*K, True, "Load")

    # search parameters
    p = pywrapcp.DefaultRoutingSearchParameters()
    p.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    p.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    p.time_limit.seconds = 20

    sol = r.SolveWithParameters(p)
    if not sol:
        print("No solution")
        return

    # collect routes
    output = []
    for v in range(K):
        i = r.Start(v)
        if sol.Value(r.NextVar(i)) == r.End(v):  # empty route
            continue
        output.append(0)
        while not r.IsEnd(i):
            output.append(mgr.IndexToNode(i))
            i = sol.Value(r.NextVar(i))
        output.append(0)
    print(" ".join(map(str, output)))

if __name__ == "__main__":
    main()
