import heapq
import math
import time
import logging
from typing import List, Tuple, Optional

import numpy as np


logger = logging.getLogger("frp.astar")


def _heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def astar(cost_grid: np.ndarray, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
    """A* on 2D cost grid. Returns path as list of (row, col)."""
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
            step_cost = move_cost * (1.4142 if dr != 0 and dc != 0 else 1.0)
            new_cost = cost_so_far[current] + step_cost
            neighbor = (nr, nc)
            if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                cost_so_far[neighbor] = new_cost
                priority = new_cost + _heuristic(goal, neighbor)
                heapq.heappush(frontier, (priority, neighbor))
                came_from[neighbor] = current

    if goal not in came_from:
        return []
    path = []
    cur = goal
    while cur is not None:
        path.append(cur)
        cur = came_from[cur]
    path.reverse()
    return path


def _astar_limited(cost_grid: np.ndarray, start: Tuple[int, int], goal: Tuple[int, int], time_limit_s: Optional[float] = None, max_expansions: Optional[int] = None):
    """A* with simple limits: returns (path, expansions, elapsed_seconds)."""
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

    expansions = 0
    t0 = time.time()
    while frontier:
        if time_limit_s is not None and (time.time() - t0) > time_limit_s:
            return [], expansions, time.time() - t0
        _, current = heapq.heappop(frontier)
        expansions += 1
        if max_expansions is not None and expansions > max_expansions:
            return [], expansions, time.time() - t0
        if current == goal:
            break
        for dr, dc in neighbors:
            nr, nc = current[0] + dr, current[1] + dc
            if not in_bounds((nr, nc)):
                continue
            move_cost = float(cost_grid[nr, nc]) if not np.isnan(cost_grid[nr, nc]) else 1e6
            step_cost = move_cost * (1.4142 if dr != 0 and dc != 0 else 1.0)
            new_cost = cost_so_far[current] + step_cost
            neighbor = (nr, nc)
            if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                cost_so_far[neighbor] = new_cost
                priority = new_cost + _heuristic(goal, neighbor)
                heapq.heappush(frontier, (priority, neighbor))
                came_from[neighbor] = current

    if goal not in came_from:
        return [], expansions, time.time() - t0
    path = []
    cur = goal
    while cur is not None:
        path.append(cur)
        cur = came_from[cur]
    path.reverse()
    return path, expansions, time.time() - t0


def optimize_route_segments(waypoints_utm: List[Tuple[float, float]], cost: np.ndarray, meta: dict) -> List[Tuple[float, float]]:
    """Coarse-grid A* planner with limited calls.

    Strategy (minimal intrusive change): group `waypoints_utm` into `num_sweeps` chunks
    (approx), append raw waypoints within each chunk, and run at most one A* to connect
    between consecutive chunks. Also connect start->first and last->end with A*.

    Uses block-min aggregation to build the coarse grid. If the coarse grid exceeds
    a hard cap (300x300) the `node_area_ha` is increased until it fits.

    `meta` may contain: transform, node_area_ha, num_sweeps, time_limit_s, mode.
    Returns list of UTM (x,y) points.
    """
    from rasterio.transform import rowcol
    from rasterio.transform import Affine

    transform = meta.get("transform")
    if isinstance(transform, list):
        transform = Affine(*transform)
    elif not isinstance(transform, Affine):
        transform = Affine(*transform)

    node_area_ha = float(meta.get("node_area_ha", 2.0))
    time_limit_s = float(meta.get("time_limit_s", 1.0))
    num_sweeps = int(meta.get("num_sweeps", 1))
    max_expansions = int(meta.get("max_expansions", 1000000))

    # compute pixel sizes
    pixel_size_x_m = abs(transform.a)
    pixel_size_y_m = abs(transform.e)

    rows, cols = cost.shape

    # helper: build coarse grid given node_area_ha
    def build_coarse(area_ha):
        area_m2 = float(area_ha) * 10000.0
        node_spacing_m = math.sqrt(area_m2)
        step_x = max(1, int(round(node_spacing_m / pixel_size_x_m)))
        step_y = max(1, int(round(node_spacing_m / pixel_size_y_m)))
        coarse_rows = int(math.ceil(rows / step_y))
        coarse_cols = int(math.ceil(cols / step_x))
        # build coarse via block-min
        large_cost = 1e6
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
                coarse[cr, cc] = float(np.min(block))
        return coarse, node_spacing_m, step_x, step_y, coarse_rows, coarse_cols

    # increase area if coarse grid too large
    coarse, node_spacing_m, step_x, step_y, coarse_rows, coarse_cols = build_coarse(node_area_ha)
    while coarse_rows > 300 or coarse_cols > 300:
        node_area_ha *= 2.0
        logger.info("Coarse grid %dx%d too large, increasing node_area_ha -> %.2fha", coarse_rows, coarse_cols, node_area_ha)
        coarse, node_spacing_m, step_x, step_y, coarse_rows, coarse_cols = build_coarse(node_area_ha)

    logger.info("Original cost grid shape: %s", cost.shape)
    logger.info("Node spacing (m): %.3f, step_x=%d, step_y=%d", node_spacing_m, step_x, step_y)
    logger.info("Coarse grid shape: (%d, %d)", coarse_rows, coarse_cols)

    out_pts: List[Tuple[float, float]] = []
    if not waypoints_utm:
        return out_pts

    # helper to map utm coord to full-res row,col
    def to_rc(xy):
        x, y = xy
        row, col = rowcol(transform, x, y)
        return int(row), int(col)

    # helper to map coarse cell to utm center
    def coarse_cell_center(cr, cc):
        r0 = cr * step_y
        r1 = min(rows, (cr + 1) * step_y)
        c0 = cc * step_x
        c1 = min(cols, (cc + 1) * step_x)
        center_r = r0 + ((r1 - r0) / 2.0)
        center_c = c0 + ((c1 - c0) / 2.0)
        x = transform.c + (center_c) * transform.a
        y = transform.f + (center_r) * transform.e
        return x, y

    # grouping: split waypoints into num_sweeps chunks (approx equal)
    total_wp = len(waypoints_utm)
    chunk_size = max(1, int(round(float(total_wp) / max(1, num_sweeps))))
    chunks = [waypoints_utm[i:i+chunk_size] for i in range(0, total_wp, chunk_size)]

    astar_calls = 0
    total_astar_time = 0.0
    fallback_count = 0

    # connect start -> first chunk start
    start_wp = waypoints_utm[0]
    end_wp = waypoints_utm[-1]

    # helper to run coarse A* between two full-res UTM points
    def run_coarse_astar(p_from, p_to):
        nonlocal astar_calls, total_astar_time, fallback_count
        s_r, s_c = to_rc(p_from)
        g_r, g_c = to_rc(p_to)
        cs_r = max(0, min(coarse_rows - 1, int(s_r // step_y)))
        cs_c = max(0, min(coarse_cols - 1, int(s_c // step_x)))
        cg_r = max(0, min(coarse_rows - 1, int(g_r // step_y)))
        cg_c = max(0, min(coarse_cols - 1, int(g_c // step_x)))
        t0 = time.time()
        path_coarse, expansions, elapsed = _astar_limited(coarse, (cs_r, cs_c), (cg_r, cg_c), time_limit_s, max_expansions)
        astar_calls += 1
        total_astar_time += elapsed
        if not path_coarse:
            fallback_count += 1
            logger.warning("A* failed or timed out between %s and %s (elapsed=%.3fs, expansions=%d) — using straight-line fallback", p_from, p_to, elapsed, expansions)
            return []
        # map coarse indices back to utm centers
        pts = [coarse_cell_center(r, c) for r, c in path_coarse]
        return pts

    # connect start -> first chunk
    first_chunk = chunks[0]
    conn = run_coarse_astar(start_wp, first_chunk[0])
    if conn:
        out_pts.extend(conn)
    else:
        out_pts.append(first_chunk[0])

    # for each chunk, append its internal waypoints (full-res) and connect to next chunk with one A*
    for idx, ch in enumerate(chunks):
        # append chunk waypoints directly (converted to UTM are already UTM)
        for p in ch:
            out_pts.append((p[0], p[1]))
        # connect to next chunk
        if idx + 1 < len(chunks):
            next_chunk = chunks[idx + 1]
            conn = run_coarse_astar(ch[-1], next_chunk[0])
            if conn:
                out_pts.extend(conn)
            else:
                # fallback: straight-line (append next chunk start)
                out_pts.append(next_chunk[0])

    # connect last -> end
    if out_pts and (out_pts[-1] != end_wp):
        conn = run_coarse_astar(out_pts[-1], end_wp)
        if conn:
            out_pts.extend(conn)
        else:
            out_pts.append(end_wp)

    logger.info("A* calls: %d, total A* time: %.3fs, fallbacks: %d", astar_calls, total_astar_time, fallback_count)
    return out_pts
