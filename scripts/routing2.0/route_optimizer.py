"""
Route Optimizer Module

Multi-factor A* pathfinding on the multi-dimensional graph.
Supports weighted optimization considering:
- Cost (terrain difficulty)
- Slope (steepness)
- NDVI (vegetation)
- Distance
- Priority (inverse of cost)
"""

import heapq
import math
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional, Any, List, Callable

import numpy as np
import networkx as nx

logger = logging.getLogger("routing2.0.route_optimizer")


def euclidean_heuristic(node_data_a: Dict, node_data_b: Dict) -> float:
    """Euclidean distance heuristic for A*."""
    dx = node_data_a.get("x", 0) - node_data_b.get("x", 0)
    dy = node_data_a.get("y", 0) - node_data_b.get("y", 0)
    return math.hypot(dx, dy)


def grid_heuristic(node_data_a: Dict, node_data_b: Dict) -> float:
    """Grid-based heuristic using row/col indices."""
    dr = abs(node_data_a.get("grid_row", 0) - node_data_b.get("grid_row", 0))
    dc = abs(node_data_a.get("grid_col", 0) - node_data_b.get("grid_col", 0))
    return math.hypot(dr, dc)


def compute_edge_weight(
    edge_data: Dict,
    weights: Dict[str, float] = None
) -> float:
    """Compute weighted edge cost combining multiple factors.
    
    Args:
        edge_data: Edge attributes dictionary
        weights: Factor weights {'cost': w1, 'slope': w2, 'ndvi': w3, 'distance': w4}
        
    Returns:
        Combined weighted cost
    """
    if weights is None:
        weights = {
            "cost": 0.4,
            "slope": 0.2,
            "ndvi": 0.2,
            "distance": 0.2
        }
    
    # Normalize weights
    total = sum(weights.values())
    if total > 0:
        weights = {k: v/total for k, v in weights.items()}
    
    # Get edge values (with defaults)
    cost = edge_data.get("cost", 1.0)
    slope = edge_data.get("slope", 0.0)
    ndvi = edge_data.get("ndvi", 0.5)
    distance = edge_data.get("distance", 1.0)
    
    # Higher slope = harder, lower NDVI = harder
    # Normalize slope (assume 0-45 degree range)
    slope_factor = min(slope / 45.0, 1.0) if slope >= 0 else 0.0
    
    # NDVI penalty (lower NDVI = higher penalty)
    # NDVI ranges from -1 to 1, normalize to 0-1
    ndvi_normalized = (ndvi + 1) / 2.0
    ndvi_penalty = 1.0 - ndvi_normalized
    
    # Combined weight
    # Drone / Forestry Logic:
    # - Slope: Affects battery (z-change), but not traversability. Weight lower.
    # - NDVI: Forests are the target? Or obstacle? If forestry, we scan forests.
    #   High NDVI = High Interest = Lower Cost (Higher Priority).
    #   Previous logic: High NDVI = High Penalty. 
    #   New Logic: High NDVI (Tree) = Good. Low NDVI (Dirt) = High Cost?
    #   Actually, A* finds "Low Cost" path. If we want to scan trees, we want path to go THROUGH trees.
    #   So High NDVI should be LOW COST.
    
    # Invert NDVI logic from previous version if "trace based on objectives" means scanning trees.
    # Original: ndvi_penalty = 1.0 - ndvi_normalized (High NDVI -> Low Penalty -> Low Cost).
    # Wait. ndvi_normalized is 0..1. 1 is dense green.
    # ndvi_penalty = 1.0 - 1.0 = 0.0. So High NDVI was Low Cost. That is correct for "stay in forest".
    
    # Let's just create a smoother 'drone' profile.
    
    combined = (
        weights.get("cost", 0.4) * cost +
        weights.get("slope", 0.1) * slope_factor +  # Reduced slope weight for drones
        weights.get("ndvi", 0.2) * ndvi_penalty +
        weights.get("distance", 0.3) * (distance / 100.0)  # Increased distance weight for smoothness
    )
    
    return max(combined, 0.001)  # Ensure positive


def astar_multifactor(
    G: nx.Graph,
    start_node: int,
    goal_node: int,
    weights: Dict[str, float] = None,
    heuristic: Callable = None
) -> Tuple[List[int], float, Dict[str, Any]]:
    """A* pathfinding with multi-factor edge weights.
    
    Args:
        G: NetworkX graph with node/edge attributes
        start_node: Starting node ID
        goal_node: Goal node ID
        weights: Factor weights for edge cost computation
        heuristic: Heuristic function (node_data_a, node_data_b) -> float
        
    Returns:
        (path as list of node IDs, total cost, route statistics)
    """
    if heuristic is None:
        heuristic = euclidean_heuristic
    
    if start_node not in G or goal_node not in G:
        logger.error(f"Start ({start_node}) or goal ({goal_node}) not in graph")
        return [], 0.0, {"error": "Invalid start or goal"}
    
    goal_data = G.nodes[goal_node]
    
    # Priority queue: (f_score, counter, node)
    counter = 0
    frontier = [(0.0, counter, start_node)]
    
    came_from = {start_node: None}
    g_score = {start_node: 0.0}
    
    # Track factor contributions for analysis
    factor_totals = {"cost": 0.0, "slope": 0.0, "ndvi": 0.0, "distance": 0.0}
    
    while frontier:
        _, _, current = heapq.heappop(frontier)
        
        if current == goal_node:
            break
        
        current_g = g_score[current]
        
        for neighbor in G.neighbors(current):
            edge_data = G.edges[current, neighbor]
            
            # Compute weighted edge cost
            move_cost = compute_edge_weight(edge_data, weights)
            new_g = current_g + move_cost
            
            if neighbor not in g_score or new_g < g_score[neighbor]:
                g_score[neighbor] = new_g
                
                # Compute heuristic
                neighbor_data = G.nodes[neighbor]
                h = heuristic(neighbor_data, goal_data)
                f = new_g + h
                
                counter += 1
                heapq.heappush(frontier, (f, counter, neighbor))
                came_from[neighbor] = current
    
    # Reconstruct path
    if goal_node not in came_from:
        return [], 0.0, {"error": "No path found", "nodes_explored": len(g_score)}
    
    path = []
    current = goal_node
    while current is not None:
        path.append(current)
        current = came_from[current]
    path.reverse()
    
    # Compute route statistics
    total_cost = g_score[goal_node]
    total_distance = 0.0
    total_slope = 0.0
    costs = []
    
    for i in range(len(path) - 1):
        edge = G.edges[path[i], path[i+1]]
        total_distance += edge.get("distance", 0)
        total_slope += edge.get("slope", 0)
        costs.append(edge.get("cost", 0))
    
    stats = {
        "path_length": len(path),
        "total_weighted_cost": total_cost,
        "total_distance": total_distance,
        "average_slope": total_slope / max(len(path) - 1, 1),
        "average_cost": sum(costs) / max(len(costs), 1) if costs else 0,
        "nodes_explored": len(g_score),
        "weights_used": weights or {"cost": 0.4, "slope": 0.2, "ndvi": 0.2, "distance": 0.2}
    }
    
    return path, total_cost, stats


def find_optimal_start(G: nx.Graph) -> Optional[int]:
    """Find the optimal starting point (highest priority / lowest cost node)."""
    best_node = None
    best_priority = -1
    
    for n, data in G.nodes(data=True):
        priority = data.get("priority", 0)
        if priority > best_priority:
            best_priority = priority
            best_node = n
    
    return best_node


def find_random_goal(G: nx.Graph, start_node: int, min_distance: float = 0) -> Optional[int]:
    """Find a random goal node at least min_distance from start."""
    import random
    
    start_data = G.nodes[start_node]
    candidates = []
    
    for n, data in G.nodes(data=True):
        if n == start_node:
            continue
        dx = data.get("x", 0) - start_data.get("x", 0)
        dy = data.get("y", 0) - start_data.get("y", 0)
        dist = math.hypot(dx, dy)
        if dist >= min_distance:
            candidates.append(n)
    
    return random.choice(candidates) if candidates else None


def generate_spiral_path(G: nx.Graph, center_node: Optional[int] = None) -> Tuple[List[int], float, Dict[str, Any]]:
    """Generate a spiral coverage path starting from center."""
    # 1. Find Center
    if center_node is None:
        # Calculate centroid of all nodes
        xs = [data['x'] for _, data in G.nodes(data=True)]
        ys = [data['y'] for _, data in G.nodes(data=True)]
        if not xs: 
            return [], 0.0, {}
        
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)
        
        # Find closest node to centroid
        min_dist = float('inf')
        center_node = -1
        for n, data in G.nodes(data=True):
            d = math.hypot(data['x'] - cx, data['y'] - cy)
            if d < min_dist:
                min_dist = d
                center_node = n
    else:
        # derive coords from node
        cx = G.nodes[center_node]['x']
        cy = G.nodes[center_node]['y']

    # 2. Sort nodes by distance and angle (rings)
    nodes_info = []
    for n, data in G.nodes(data=True):
        dx = data['x'] - cx
        dy = data['y'] - cy
        dist = math.hypot(dx, dy)
        angle = math.atan2(dy, dx)
        nodes_info.append({
            'id': n,
            'dist': dist,
            'angle': angle
        })
    
    # Sort into rings
    if not nodes_info:
        return [], 0.0, {}
        
    max_dist = max(n['dist'] for n in nodes_info)
    if max_dist == 0: max_dist = 1
    
    num_rings = 20 # Adjustable ring density
    
    # Assign rings
    for n in nodes_info:
        n['ring'] = int((n['dist'] / max_dist) * num_rings)
    
    # Sort: Primary by Ring, Secondary by Angle
    nodes_info.sort(key=lambda k: (k['ring'], k['angle']))
    
    # 3. Create Path (connect sorted nodes)
    # Sampling: Connecting EVERY node is too dense. We sample.
    sample_step = max(1, len(nodes_info) // 500) # Target ~500 waypoints
    sampled_nodes = [n['id'] for n in nodes_info[::sample_step]]
    
    # 4. Calculate Stats
    total_cost = 0.0
    total_slope = 0.0
    total_dist = 0.0
    
    # Just linear summation for the spiral "flight"
    for i in range(len(sampled_nodes) - 1):
        u, v = sampled_nodes[i], sampled_nodes[i+1]
        # In a generic graph, u and v might not be connected directly if we sample
        # For a drone, we assume straight line flight between waypoints
        u_data = G.nodes[u]
        v_data = G.nodes[v]
        d = math.hypot(u_data['x'] - v_data['x'], u_data['y'] - v_data['y'])
        total_dist += d
        # Slope approximated
        s = abs(u_data.get('slope',0) + v_data.get('slope',0))/2
        total_slope += s * d # Weighted by distance
        
    avg_slope = total_slope / total_dist if total_dist > 0 else 0
    
    stats = {
        "path_length": len(sampled_nodes),
        "total_distance": total_dist,
        "average_slope": avg_slope,
        "type": "Spiral Coverage"
    }
    
    return sampled_nodes, 0.0, stats


def optimize_route_demo(
    G: nx.Graph,
    start_node: Optional[int] = None,
    goal_node: Optional[int] = None,
    weights: Dict[str, float] = None
) -> Dict[str, Any]:
    """Run a demo route optimization.
    
    Args:
        G: Multi-dimensional graph
        start_node: Optional starting node (auto-detect if None)
        goal_node: Optional goal node (auto-detect if None)
        weights: Factor weights
        
    Returns:
        Complete optimization results
    """
    # Auto-detect start (highest priority)
    if start_node is None:
        start_node = find_optimal_start(G)
        if start_node is None:
            return {"error": "Could not find start node"}
        logger.info(f"Auto-selected start node: {start_node} (highest priority)")
    
    # Auto-detect goal (random far node)
    if goal_node is None:
        goal_node = find_random_goal(G, start_node, min_distance=100)
        if goal_node is None:
            # Fallback: just pick a different node
            for n in G.nodes():
                if n != start_node:
                    goal_node = n
                    break
        if goal_node is None:
            return {"error": "Could not find goal node"}
        logger.info(f"Auto-selected goal node: {goal_node}")
    
    # Run A*
    path, total_cost, stats = astar_multifactor(G, start_node, goal_node, weights)
    
    if not path:
        return {"error": "No path found", "stats": stats}
    
    # Get path node details
    path_details = []
    for nid in path:
        data = G.nodes[nid]
        path_details.append({
            "node_id": nid,
            "x": data.get("x"),
            "y": data.get("y"),
            "cost": data.get("cost"),
            "priority": data.get("priority"),
            "slope": data.get("slope"),
            "ndvi": data.get("ndvi")
        })
    
    return {
        "start_node": start_node,
        "goal_node": goal_node,
        "path": path,
        "path_details": path_details,
        "total_cost": total_cost,
        "statistics": stats
    }


def compare_weight_strategies(
    G: nx.Graph,
    start_node: int,
    goal_node: int
) -> Dict[str, Any]:
    """Compare different weight strategies for the same route.
    
    Returns comparison of different factor weighting approaches.
    """
    strategies = {
        "balanced": {"cost": 0.25, "slope": 0.25, "ndvi": 0.25, "distance": 0.25},
        "cost_focused": {"cost": 0.7, "slope": 0.1, "ndvi": 0.1, "distance": 0.1},
        "slope_aware": {"cost": 0.2, "slope": 0.6, "ndvi": 0.1, "distance": 0.1},
        "vegetation_aware": {"cost": 0.2, "slope": 0.1, "ndvi": 0.6, "distance": 0.1},
        "shortest_path": {"cost": 0.1, "slope": 0.1, "ndvi": 0.1, "distance": 0.7}
    }
    
    results = {}
    for name, weights in strategies.items():
        path, cost, stats = astar_multifactor(G, start_node, goal_node, weights)
        results[name] = {
            "weights": weights,
            "path_length": len(path),
            "total_cost": cost,
            "total_distance": stats.get("total_distance", 0),
            "average_slope": stats.get("average_slope", 0)
        }
    
    return {
        "start": start_node,
        "goal": goal_node,
        "strategies": results
    }


def path_to_coordinates(G: nx.Graph, path: List[int]) -> List[Tuple[float, float]]:
    """Convert path node IDs to coordinate list."""
    coords = []
    for nid in path:
        data = G.nodes[nid]
        coords.append((data.get("x", 0), data.get("y", 0)))
    return coords


if __name__ == "__main__":
    import sys
    import json
    from multidim_graph import build_multidim_graph, save_graph
    
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    # Default test paths
    cost_path = "out_demo_plan/rasters/cost.tif"
    slope_path = "out_demo_plan/rasters/slope.tif"
    ndvi_path = "out_demo_plan/rasters/ndvi.tif"
    
    # Build graph
    logger.info("Building multi-dimensional graph...")
    G, meta = build_multidim_graph(
        cost_path=cost_path,
        slope_path=slope_path,
        ndvi_path=ndvi_path,
        node_spacing=10,
        connectivity=8
    )
    
    # Run demo optimization
    logger.info("Running route optimization demo...")
    result = optimize_route_demo(G)
    
    print("\n=== Route Optimization Results ===")
    print(json.dumps({k: v for k, v in result.items() if k != "path_details"}, indent=2, default=str))
    
    if "path" in result and len(result["path"]) > 0:
        # Compare strategies
        comparison = compare_weight_strategies(G, result["start_node"], result["goal_node"])
        print("\n=== Strategy Comparison ===")
        print(json.dumps(comparison, indent=2, default=str))
