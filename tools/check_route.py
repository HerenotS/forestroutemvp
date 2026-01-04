import os
import json
import geopandas as gpd
import xml.etree.ElementTree as ET

geojson_path = 'out_demo/routes/route.geojson'
kml_path = 'out_demo/routes/route.kml'
aoi_path = 'out_demo/inputs/aoi.geojson'

out = {}

for p in [geojson_path, kml_path, aoi_path]:
    out[p] = {'exists': os.path.exists(p)}

if not out[geojson_path]['exists']:
    print('MISSING GEOJSON')
    raise SystemExit(1)

if not out[kml_path]['exists']:
    print('MISSING KML')
    raise SystemExit(1)

# GeoJSON
gdf = gpd.read_file(geojson_path)
out['geojson'] = {}
out['geojson']['crs'] = str(gdf.crs)
out['geojson']['n_features'] = len(gdf)
geom_types = list(gdf.geom_type.unique())
out['geojson']['geom_types'] = geom_types
# count coordinates
coord_count = 0
for geom in gdf.geometry:
    if geom is None:
        continue
    if geom.geom_type == 'Point':
        coord_count += 1
    else:
        try:
            coord_count += len(list(geom.coords))
        except Exception:
            # for Multi geometries
            for part in geom:
                try:
                    coord_count += len(list(part.coords))
                except Exception:
                    pass
out['geojson']['coord_count'] = coord_count
minx, miny, maxx, maxy = gdf.total_bounds
out['geojson']['bounds'] = [float(minx), float(miny), float(maxx), float(maxy)]

# AOI
ag = gpd.read_file(aoi_path)
aoi_bounds = list(map(float, ag.total_bounds))
out['aoi_bounds'] = aoi_bounds

# overlap test
def bbox_overlap(b1, b2):
    return (min(b1[2], b2[2]) > max(b1[0], b2[0])) and (min(b1[3], b2[3]) > max(b1[1], b2[1]))

out['overlaps'] = bbox_overlap(out['geojson']['bounds'], aoi_bounds)

# KML parse: count coordinates in <coordinates> tags
try:
    tree = ET.parse(kml_path)
    root = tree.getroot()
    # find all coordinates text
    coords_texts = [elem.text for elem in root.iter() if elem.tag.endswith('}coordinates') or elem.tag == 'coordinates']
    kml_coords = 0
    for txt in coords_texts:
        if not txt:
            continue
        parts = txt.strip().split()
        kml_coords += len(parts)
    out['kml'] = {'coords_tags': len(coords_texts), 'coord_count': kml_coords}
except Exception as e:
    out['kml'] = {'error': str(e)}

print(json.dumps(out, indent=2))
