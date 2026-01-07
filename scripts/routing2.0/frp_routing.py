"""
Routing Module

Multi-factor A* pathfinding on the multi-dimensional graph.
Supports weighted optimization considering:
- Cost (terrain difficulty)
- Slope (steepness)
- NDVI (vegetation)
- Distance
- Priority (inverse of cost)
"""

import math
import logging
from typing import Dict, Tuple, Optional, Any, List

import networkx as nx

logger = logging.getLogger("frp.routing")


def euclidean_heuristic(node_data_a: Dict, node_data_b: Dict) -> float:
    """Euclidean distance heuristic for A*."""
    dx = node_data_a.get("x", 0) - node_data_b.get("x", 0)
    dy = node_data_a.get("y", 0) - node_data_b.get("y", 0)
    return math.hypot(dx, dy)


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
    
    # Get edge values
    cost = edge_data.get("cost", 1.0)
    slope = edge_data.get("slope", 0.0)
    ndvi = edge_data.get("ndvi", 0.5)
    distance = edge_data.get("distance", 1.0)
    
    # Normalize inputs
    # Slope: assume 0-45 degree range usually, can be higher
    slope_factor = min(slope / 45.0, 1.0) if slope >= 0 else 0.0
    
    # NDVI: -1 to 1 -> 0 to 1
    ndvi_normalized = (ndvi + 1) / 2.0
    # Logic: If we want to stay in forest (High NDVI), then Low Cost.
    ndvi_penalty = 1.0 - ndvi_normalized
    
    combined = (
        weights.get("cost", 0.4) * cost +
        weights.get("slope", 0.2) * slope_factor +
        weights.get("ndvi", 0.2) * ndvi_penalty
    )
    
    # Scale by distance so short hops are cheaper than long hops
    # But 'cost' etc are unitless 0-1 factors. Distance is meters.
    # Standard A*: cost = distance * weight.
    # Here: cost = distance * (1.0 + combined_factors)
    return distance * (1.0 + combined * 5.0) 


def find_path_astar_multidim(
    G: nx.Graph,
    start_node: Any,
    end_node: Any,
    weights: Dict[str, float] = None
) -> List[Any]:
    """Find path using A* with multi-factor weights."""
    
    def heuristic(u, v):
        return euclidean_heuristic(G.nodes[u], G.nodes[v])

    def weight_func(u, v, d):
        return compute_edge_weight(d, weights)

    try:
        path = nx.astar_path(G, start_node, end_node, heuristic=heuristic, weight=weight_func)
        return path
    except nx.NetworkXNoPath:
        logger.error("No path found between %s and %s", start_node, end_node)
        return []
    except Exception as e:
        logger.error("Error in A*: %s", e)
        return []

