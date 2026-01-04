import heapq
import math
import logging
from typing import List, Tuple

import numpy as np


def _heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


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
    import logging
    from rasterio.transform import rowcol
    from rasterio.transform import Affine

    logger = logging.getLogger("frp.astar")

    transform = meta.get("transform")
    if isinstance(transform, list):
        transform = Affine(*transform)
    elif not isinstance(transform, Affine):
        transform = Affine(*transform)

    out_pts = []
    if not waypoints_utm:
        return out_pts

    # New parameter: node area in hectares controls coarse node spacing.
    # Default behaviour: 2 ha -> ~141.42 m node spacing.
    node_area_ha = float(meta.get("node_area_ha", 2.0))
    # convert to square meters and spacing
    area_m2 = float(node_area_ha) * 10000.0
    node_spacing_m = math.sqrt(area_m2)

    # compute pixel sizes from affine transform (UTM meters)
    transform = meta.get("transform")
    if isinstance(transform, list):
        transform = Affine(*transform)
    elif not isinstance(transform, Affine):
        transform = Affine(*transform)

    pixel_size_x_m = abs(transform.a)
    pixel_size_y_m = abs(transform.e)

    step_x = max(1, int(round(node_spacing_m / pixel_size_x_m)))
    step_y = max(1, int(round(node_spacing_m / pixel_size_y_m)))

    # log shapes and chosen steps
    logger.info("Original cost grid shape: %s", cost.shape)
    # build coarse grid by block-min aggregation (prefer min to preserve low-cost corridors)
    logger.info("Node spacing (m): %.3f, step_x=%d, step_y=%d", node_spacing_m, step_x, step_y)

    rows, cols = cost.shape
    coarse_rows = int(math.ceil(rows / step_y))
    coarse_cols = int(math.ceil(cols / step_x))
    logger.info("Coarse grid shape: (%d, %d)", coarse_rows, coarse_cols)

    # create coarse cost grid
    large_cost = 1e6
    # treat NaNs as very high cost so they don't become minima unless whole block is NaN
    cost_filled = np.where(np.isnan(cost), large_cost, cost)
    coarse = np.full((coarse_rows, coarse_cols), large_cost, dtype=float)
    for cr in range(coarse_rows):
        r0 = cr * step_y
        r1 = min(rows, (cr + 1) * step_y)
        for cc in range(coarse_cols):
            c0 = cc * step_x
            c1 = min(cols, (cc + 1) * step_x)
            block = cost_filled[r0:r1, c0:c1]
            if block.size == 0:
                continue
            # block-min aggregation chosen: preserves low-cost passes and narrow corridors
            block_min = float(np.min(block))
            coarse[cr, cc] = block_min

    # helper to map utm coord to row,col on full-res grid
    def to_rc(xy):
        x, y = xy
        row, col = rowcol(transform, x, y)
        return int(row), int(col)

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

        # map full-res start/goal to coarse indices
        s_r, s_c = start
        g_r, g_c = goal
        cs_r = int(s_r // step_y)
        cs_c = int(s_c // step_x)
        cg_r = int(g_r // step_y)
        cg_c = int(g_c // step_x)

        # clamp to coarse grid bounds
        cs_r = max(0, min(coarse_rows - 1, cs_r))
        cs_c = max(0, min(coarse_cols - 1, cs_c))
        cg_r = max(0, min(coarse_rows - 1, cg_r))
        cg_c = max(0, min(coarse_cols - 1, cg_c))

        path_rc_coarse = astar(coarse, (cs_r, cs_c), (cg_r, cg_c))

        # map coarse path back to full-resolution UTM coordinates by using block centers
        for cr, cc in path_rc_coarse:
            r0 = cr * step_y
            r1 = min(rows, (cr + 1) * step_y)
            c0 = cc * step_x
            c1 = min(cols, (cc + 1) * step_x)
            block_h = r1 - r0
            block_w = c1 - c0
            # center pixel index inside block (floating)
            center_r = r0 + (block_h / 2.0)
            center_c = c0 + (block_w / 2.0)
            # convert to UTM (pixel-center = index + 0.5)
            x = transform.c + (center_c + 0.0) * transform.a + transform.a / 2.0
            y = transform.f + (center_r + 0.0) * transform.e + transform.e / 2.0
            out_pts.append((x, y))
    return out_pts
