import heapq
from typing import List, Tuple

import numpy as np


def _heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def astar(cost_grid: np.ndarray, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
    """A* on 2D cost grid. Returns path as list of (row, col).

    cost_grid: movement cost for stepping on a cell. NaNs treated as high cost.
    """
    rows, cols = cost_grid.shape
    def in_bounds(p):
        r, c = p
        return 0 <= r < rows and 0 <= c < cols

    start = (int(start[0]), int(start[1]))
    goal = (int(goal[0]), int(goal[1]))

    frontier = []
    heapq.heappush(frontier, (0.0, start))
    came_from = {start: None}
    cost_so_far = {start: 0.0}

    neighbors = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    while frontier:
        _, current = heapq.heappop(frontier)
        if current == goal:
            break
        for dr, dc in neighbors:
            nr, nc = current[0] + dr, current[1] + dc
            if not in_bounds((nr, nc)):
                continue
            move_cost = float(cost_grid[nr, nc]) if not np.isnan(cost_grid[nr, nc]) else 1e6
            # diagonal penalty
            step_cost = move_cost * (1.4142 if dr != 0 and dc != 0 else 1.0)
            new_cost = cost_so_far[current] + step_cost
            neighbor = (nr, nc)
            if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                cost_so_far[neighbor] = new_cost
                priority = new_cost + _heuristic(goal, neighbor)
                heapq.heappush(frontier, (priority, neighbor))
                came_from[neighbor] = current

    # reconstruct
    if goal not in came_from:
        return []
    path = []
    cur = goal
    while cur is not None:
        path.append(cur)
        cur = came_from[cur]
    path.reverse()
    return path


def optimize_route_segments(waypoints_utm: List[Tuple[float, float]], cost: np.ndarray, meta: dict) -> List[Tuple[float, float]]:
    """For each consecutive waypoint pair, run A* on cost grid. Convert to UTM meters using meta transform.

    Returns list of (lon, lat) in WGS84? Actually returns UTM coordinates (x,y) matching input UTM.
    """
    from rasterio.transform import rowcol
    from rasterio.transform import Affine

    transform = meta.get("transform")
    if isinstance(transform, list):
        transform = Affine(*transform)
    elif not isinstance(transform, Affine):
        transform = Affine(*transform)

    out_pts = []
    if not waypoints_utm:
        return out_pts

    # Helper to map utm coord to row,col
    def to_rc(xy):
        x, y = xy
        row, col = rowcol(transform, x, y)
        return int(row), int(col)

    for i in range(len(waypoints_utm) - 1):
        a = waypoints_utm[i]
        b = waypoints_utm[i + 1]
        start = to_rc(a)
        goal = to_rc(b)
        path_rc = astar(cost, start, goal)
        # convert back to utm x,y centers
        for r, c in path_rc:
            x = transform.c + c * transform.a + transform.a / 2.0
            y = transform.f + r * transform.e + transform.e / 2.0
            out_pts.append((x, y))
    return out_pts
