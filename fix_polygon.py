import json

with open('inputs/map.geojson', 'r') as f:
    data = json.load(f)

# Close the polygon ring
if data['features']:
    for feat in data['features']:
        if feat['geometry']['type'] == 'Polygon':
            rings = feat['geometry']['coordinates']
            for ring in rings:
                # Close the ring: add first point at the end if not already closed
                if ring[0] != ring[-1]:
                    ring.append(ring[0])

# Write back
with open('inputs/map.geojson', 'w') as f:
    json.dump(data, f, indent=2)

print('Fixed polygon ring closure')
