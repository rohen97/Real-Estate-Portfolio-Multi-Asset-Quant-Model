from __future__ import annotations
from collections import Counter
import math
from shapely.geometry import shape
from packages.zoning.taxonomy import core_class
NUMERIC_FEATURES=['latitude','longitude','site_area_sqm','compactness','aspect_ratio','building_height_m','building_density','road_density','impervious_fraction','vegetation_fraction','water_fraction','population_density','employment_density','distance_mrt_m','distance_road_m','distance_park_m','distance_commercial_m','neighbor_mean_gpr_250m','neighbor_mean_gpr_500m','neighbor_mean_gpr_1000m','neighbor_high_density_share_500m','neighbor_residential_share_500m','neighbor_commercial_share_500m','neighbor_industrial_share_500m']
CATEGORICAL_FEATURES=['observed_lulc','conservation_status']
def geometry_features(geojson):
 if not geojson:return {'site_area_sqm':None,'compactness':None,'aspect_ratio':None}
 geom=shape(geojson.get('geometry',geojson));area=max(geom.area,1e-15);perimeter=max(geom.length,1e-15);minx,miny,maxx,maxy=geom.bounds;width=maxx-minx;height=maxy-miny;return {'site_area_sqm':None,'compactness':float(4*math.pi*area/(perimeter**2)),'aspect_ratio':float(max(width,height)/max(min(width,height),1e-15))}
def feature_record(asset,external=None,neighbors=None,title_boundary=None):
 external=external or {};neighbors=neighbors or [];geom=geometry_features(title_boundary);lat=asset.get('latitude');lon=asset.get('longitude');record={'asset_id':asset.get('asset_id'),'latitude':lat,'longitude':lon,'planning_area':(asset.get('ura_zoning',{}).get('matches') or [{}])[0].get('planning_area','Unknown'),'subzone':(asset.get('ura_zoning',{}).get('matches') or [{}])[0].get('subzone','Unknown'),'observed_lulc':external.get('observed_lulc','Unknown'),'conservation_status':external.get('conservation_status','Unknown'),**geom}
 for key in ['building_height_m','building_density','road_density','impervious_fraction','vegetation_fraction','water_fraction','population_density','employment_density','distance_mrt_m','distance_road_m','distance_park_m','distance_commercial_m']:record[key]=external.get(key)
 for radius in (250,500,1000):
  subset=[n for n in neighbors if float(n.get('distance_m',1e9))<=radius and n.get('gpr') is not None];record[f'neighbor_mean_gpr_{radius}m']=sum(float(x['gpr']) for x in subset)/len(subset) if subset else None
 subset=[n for n in neighbors if float(n.get('distance_m',1e9))<=500];cores=Counter(core_class(x.get('land_use')) for x in subset);total=max(len(subset),1);record['neighbor_high_density_share_500m']=sum(1 for x in subset if x.get('gpr') is not None and float(x['gpr'])>=2.8)/total;record['neighbor_residential_share_500m']=cores['Residential']/total;record['neighbor_commercial_share_500m']=(cores['Commercial']+cores['Mixed Use'])/total;record['neighbor_industrial_share_500m']=cores['Industrial']/total
 return record
