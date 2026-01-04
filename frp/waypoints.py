from typing import List, Tuple

import numpy as np
from shapely.geometry import LineString, Point


def lines_to_waypoints(lines: List[LineString], spacing: float = 50.0) -> List[Tuple[float, float]]:
    """Convert list of LineString (UTM coords) to a sequence of waypoints (x,y in meters).

    Spacing is distance between consecutive waypoints along a line.
    """
    pts = []
    for line in lines:
        length = line.length
        if length == 0:
            continue
        n = max(1, int(length // spacing))
        for i in range(n + 1):
            frac = i / n
            p = line.interpolate(frac, normalized=True)
            pts.append((p.x, p.y))
    return pts
