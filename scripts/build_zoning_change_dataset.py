import sys,json,argparse,sqlite3
from pathlib import Path
from shapely import wkb
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from packages.zoning.ura import lookup_zone
from packages.zoning.taxonomy import core_class,gpr_band
p=argparse.ArgumentParser();p.add_argument('--old-db',required=True);p.add_argument('--new-db',default='data/processed/ura_mp2025.sqlite');p.add_argument('--output',default='data/observed/zoning_change_training.json');p.add_argument('--limit',type=int,default=20000);a=p.parse_args();old=Path(a.old_db);new=ROOT/a.new_db;rows=[]
with sqlite3.connect(old) as conn:
 conn.row_factory=sqlite3.Row
 for row in conn.execute('select * from zones limit ?',(a.limit,)):
  geom=wkb.loads(row['geom']);point=geom.representative_point();current=lookup_zone(new,point.y,point.x);match=(current.get('matches') or [{}])[0];old_core=core_class(row['lu_desc']);new_core=core_class(match.get('lu_desc'));old_gpr=row['gpr'];new_gpr=match.get('gpr');rows.append({'asset_id':f'HIST-{row["objectid"]}','latitude':point.y,'longitude':point.x,'planning_area':row['planning_area'] or 'Unknown','subzone':row['subzone'] or 'Unknown','observed_lulc':'Unknown','conservation_status':'Unknown','site_area_sqm':None,'compactness':float(4*3.14159265*geom.area/max(geom.length**2,1e-15)),'aspect_ratio':1,'building_height_m':None,'building_density':None,'road_density':None,'impervious_fraction':None,'vegetation_fraction':None,'water_fraction':None,'population_density':None,'employment_density':None,'distance_mrt_m':None,'distance_road_m':None,'distance_park_m':None,'distance_commercial_m':None,'neighbor_mean_gpr_250m':old_gpr,'neighbor_mean_gpr_500m':old_gpr,'neighbor_mean_gpr_1000m':old_gpr,'neighbor_high_density_share_500m':0,'neighbor_residential_share_500m':0,'neighbor_commercial_share_500m':0,'neighbor_industrial_share_500m':0,'old_land_use':row['lu_desc'],'new_land_use':match.get('lu_desc'),'old_gpr':old_gpr,'new_gpr':new_gpr,'changed':int(old_core!=new_core or gpr_band(old_gpr)!=gpr_band(new_gpr))})
out=ROOT/a.output;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rows,indent=2),encoding='utf-8');print(json.dumps({'rows':len(rows),'changed':sum(x['changed'] for x in rows),'output':str(out)},indent=2))
