#!/usr/bin/env python
"""Check what coordinates are in the generated HTML files."""
import re
from pathlib import Path

# Read the HTML
html_path = Path("test_coord_debug/3d_model/test_terrain.html")
content = html_path.read_text(encoding="utf-8")

# Find x array patterns
x_pattern = r'"x":\[\[([^\]]+)\]'
y_pattern = r'"y":\[\[([^\]]+)\]'
z_pattern = r'"z":\[\[([^\]]+)\]'

print("="*60)
print("Checking 3D Model HTML for coordinate values")
print("="*60)

x_match = re.search(x_pattern, content)
if x_match:
    vals = x_match.group(1).split(",")[:5]
    print(f"\nX values (first 5): {vals}")
    print(f"  These should be Longitudes like -99.xxx")

y_match = re.search(y_pattern, content)
if y_match:
    vals = y_match.group(1).split(",")[:5]
    print(f"\nY values (first 5): {vals}")
    print(f"  These should be Latitudes like 19.xxx")

z_match = re.search(z_pattern, content)
if z_match:
    vals = z_match.group(1).split(",")[:5]
    print(f"\nZ values (first 5): {vals}")
    print(f"  These should be Altitudes like 2200-2800")

# Also look for axis labels
xaxis_match = re.search(r'"xaxis_title":\s*"([^"]+)"', content)
yaxis_match = re.search(r'"yaxis_title":\s*"([^"]+)"', content)
zaxis_match = re.search(r'"zaxis_title":\s*"([^"]+)"', content)

print("\nAxis Labels:")
if xaxis_match:
    print(f"  X axis: {xaxis_match.group(1)}")
if yaxis_match:
    print(f"  Y axis: {yaxis_match.group(1)}")
if zaxis_match:
    print(f"  Z axis: {zaxis_match.group(1)}")
