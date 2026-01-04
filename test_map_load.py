import json
from shapely.geometry import shape
import geopandas as gpd

with open('inputs/map.geojson') as f:
    data = json.load(f)
    
print(f'Features: {len(data.get("features", []))}')

if data.get('features'):
    feat = data['features'][0]
    geom_dict = feat.get('geometry', {})
    print(f'Geom type: {geom_dict.get("type")}')
    
    try:
        geom = shape(geom_dict)
        print(f'Shapely valid: {geom.is_valid}')
        print(f'Bounds: {geom.bounds}')
    except Exception as e:
        print(f'Shapely error: {e}')

# Try geopandas
try:
    gdf = gpd.read_file('inputs/map.geojson')
    print(f'GeoDataFrame: {len(gdf)} records')
except Exception as e:
    print(f'GeoDataFrame error: {e}')
