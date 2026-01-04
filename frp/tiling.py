from typing import List, Tuple

import math
import numpy as np

def tile_indices(width: int, height: int, tile_size: int) -> List[Tuple[int, int, int, int]]:
    """Return list of tiles as (col_off, row_off, w, h) covering a raster of width,height."""
    tiles = []
    nx = math.ceil(width / tile_size)
    ny = math.ceil(height / tile_size)
    for iy in range(ny):
        for ix in range(nx):
            col = ix * tile_size
            row = iy * tile_size
            w = min(tile_size, width - col)
            h = min(tile_size, height - row)
            tiles.append((col, row, w, h))
    return tiles
