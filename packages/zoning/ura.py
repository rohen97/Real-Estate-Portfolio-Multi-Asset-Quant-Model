from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import sqlite3,time,math
import httpx
from shapely.geometry import Point,shape,mapping,box
from shapely import wkb
MP2025_LAYER='https://maps.ura.gov.sg/arcgis/rest/services/MP25/Updated_Landuse_gaz/MapServer/45'
MP2025_QUERY=MP2025_LAYER+'/query'
MP2025_SPACE='https://eservice.ura.gov.sg/maps/index.html?service=mp'
SOURCE_VINTAGE='URA SPACE Master Plan 2025 - approved amendments incorporated'

def _request(client,url,params,attempts=6,post=False):
 for attempt in range(attempts):
  response=client.post(url,data=params) if post else client.get(url,params=params)
  if response.status_code in (429,502,503,504):time.sleep(min(30,2**attempt));continue
  response.raise_for_status();payload=response.json()
  if 'error' in payload:raise RuntimeError(payload['error'])
  return payload
 raise RuntimeError(f'URA request failed after {attempts} attempts: {url}')

def build_mp2025_index(db_path:Path,batch_size=1000)->dict:
 db_path.parent.mkdir(parents=True,exist_ok=True);retrieved=datetime.now(timezone.utc).isoformat()
 with httpx.Client(timeout=120,follow_redirects=True,headers={'User-Agent':'Mozilla/5.0','Referer':MP2025_SPACE,'Accept':'application/json,text/plain,*/*'}) as client:
  ids=_request(client,MP2025_QUERY,{'where':'1=1','returnIdsOnly':'true','f':'json'}).get('objectIds',[]);ids=sorted(ids)
  with sqlite3.connect(db_path) as conn:
   conn.executescript('drop table if exists zones; drop table if exists metadata; create table zones(objectid integer primary key,lu_desc text,lu_text text,lu_dt_desc text,gpr_text text,gpr real,height_max text,gpr_min text,region text,planning_area text,subzone text,last_modified integer,minx real,miny real,maxx real,maxy real,geom blob,source_vintage text,source_url text); create index zones_bbox on zones(minx,maxx,miny,maxy); create table metadata(key text primary key,value text);')
   count=0
   for offset in range(0,len(ids),batch_size):
    chunk=ids[offset:offset+batch_size];collection=_request(client,MP2025_QUERY,{'objectIds':','.join(map(str,chunk)),'outFields':'*','returnGeometry':'true','outSR':'4326','f':'geojson'},post=True)
    for feature in collection.get('features',[]):
     geometry=shape(feature['geometry']);props=feature.get('properties',{});gpr_text=str(props.get('GPR') or '')
     try:gpr=float(props.get('GPR_NUM') if props.get('GPR_NUM') is not None else gpr_text)
     except:gpr=None
     minx,miny,maxx,maxy=geometry.bounds
     conn.execute('insert or replace into zones values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(props.get('OBJECTID') or feature.get('id'),props.get('LU_DESC'),props.get('LU_TEXT'),props.get('LU_DT_DESC'),gpr_text,gpr,str(props.get('WHI_Q_MX') or ''),str(props.get('GPR_B_MN') or ''),props.get('REGION_N'),props.get('PLN_AREA_N'),props.get('SUBZONE_N'),props.get('LST_MDF_DT'),minx,miny,maxx,maxy,sqlite3.Binary(wkb.dumps(geometry)),SOURCE_VINTAGE,MP2025_SPACE));count+=1
    conn.commit()
   metadata={'source':MP2025_SPACE,'arcgis_layer':MP2025_LAYER,'source_vintage':SOURCE_VINTAGE,'retrieved_at':retrieved,'feature_count':str(count)}
   conn.executemany('insert into metadata values(?,?)',metadata.items());conn.commit()
 return {'features':count,'database':str(db_path),'source':MP2025_SPACE,'arcgis_layer':MP2025_LAYER,'retrieved_at':retrieved,'current_plan_verification_required':True}

def _row_dict(row):return {k:row[k] for k in ['objectid','lu_desc','lu_text','lu_dt_desc','gpr_text','gpr','height_max','gpr_min','region','planning_area','subzone','last_modified','source_vintage','source_url']}
def lookup_zone(db_path:Path,latitude:float,longitude:float,snap_distance_m=40)->dict:
 point=Point(longitude,latitude);point_matches=[];nearby=[];metadata={};degree_buffer=snap_distance_m/111320
 if db_path.exists():
  with sqlite3.connect(db_path) as conn:
   conn.row_factory=sqlite3.Row
   try:metadata={row['key']:row['value'] for row in conn.execute('select key,value from metadata')}
   except sqlite3.OperationalError:metadata={}
   rows=conn.execute('select * from zones where minx<=? and maxx>=? and miny<=? and maxy>=?',(longitude+degree_buffer,longitude-degree_buffer,latitude+degree_buffer,latitude-degree_buffer)).fetchall()
   for row in rows:
    geometry=wkb.loads(row['geom']);distance_m=geometry.distance(point)*111320
    item=_row_dict(row);item['distance_m']=round(distance_m,1)
    if geometry.covers(point):point_matches.append(item)
    if distance_m<=snap_distance_m and row['lu_desc'] not in ('ROAD','WATERBODY'):nearby.append(item)
 point_matches.sort(key=lambda x:(x['lu_desc']=='ROAD',x['distance_m']));nearby.sort(key=lambda x:x['distance_m'])
 matches=point_matches;method='point_in_polygon';review=False;snap=None
 if not point_matches or all(x['lu_desc']=='ROAD' for x in point_matches):
  if nearby:matches=[nearby[0]];method='nearest_non_road';review=True;snap=nearby[0]['distance_m']
  else:method='unmatched';review=True
 if matches and matches[0]['lu_desc'] in ('RESERVE SITE','TRANSPORT FACILITIES','OPEN SPACE'):review=True
 return {'latitude':latitude,'longitude':longitude,'matches':matches,'original_point_matches':point_matches,'nearby_candidates':nearby[:5],'match_method':method,'snap_distance_m':snap,'spatial_review_required':review,'metadata':metadata,'current_statutory_plan':'Master Plan 2025','current_plan_url':MP2025_SPACE,'current_plan_verification_required':True,'warning':'Matched against the live URA SPACE MP2025 land-use service. Nearest-polygon snapping is only a review aid; title-lot geometry, written permission, SDCPs and project-specific controls require professional verification.'}
def surrounding_development_context(db_path:Path,latitude:float,longitude:float,radius_m=500,current_objectid=None)->dict:
 point=Point(longitude,latitude);degree_buffer=radius_m/111320;candidates=[]
 if not db_path.exists():return {'status':'unavailable','radius_m':radius_m,'candidates':[]}
 with sqlite3.connect(db_path) as conn:
  conn.row_factory=sqlite3.Row
  rows=conn.execute('select * from zones where minx<=? and maxx>=? and miny<=? and maxy>=?',(longitude+degree_buffer,longitude-degree_buffer,latitude+degree_buffer,latitude-degree_buffer)).fetchall()
  for row in rows:
   if current_objectid is not None and row['objectid']==current_objectid:continue
   geometry=wkb.loads(row['geom']);distance_m=geometry.distance(point)*111320
   if distance_m>radius_m:continue
   gpr=float(row['gpr']) if row['gpr'] is not None else None;land=(row['lu_desc'] or '').upper()
   if any(x in land for x in ['ROAD','WATERBODY']):continue
   centroid=geometry.centroid;dx=(centroid.x-longitude)*111320*math.cos(math.radians(latitude));dy=(centroid.y-latitude)*110540;candidates.append({'objectid':row['objectid'],'land_use':row['lu_desc'],'gpr':gpr,'distance_m':round(distance_m,1),'planning_area':row['planning_area'],'subzone':row['subzone'],'longitude':centroid.x,'latitude':centroid.y,'dx_m':round(dx,1),'dy_m':round(dy,1),'width_m':round(math.sqrt(max(geometry.area,1e-12))*111320,1)})
 intensity=0;high_density=0;developable=0;weighted_gpr=[]
 for c in candidates:
  if c['gpr'] is not None:
   weight=max(0,1-c['distance_m']/radius_m);weighted_gpr.append((c['gpr'],weight));intensity+=max(0,c['gpr']-1.4)*weight;high_density+=int(c['gpr']>=2.8);developable+=1
 view_risk=min(.95,1-math.exp(-.035*intensity)) if intensity else 0;avg=sum(g*w for g,w in weighted_gpr)/max(sum(w for _,w in weighted_gpr),1e-9) if weighted_gpr else None;supply=min(1,(high_density/25)+(developable/120))
 return {'status':'available','radius_m':radius_m,'candidate_polygons':len(candidates),'developable_polygons':developable,'high_density_polygons':high_density,'maximum_gpr':max((c['gpr'] for c in candidates if c['gpr'] is not None),default=None),'distance_weighted_gpr':round(avg,3) if avg is not None else None,'view_block_probability':round(view_risk,4),'supply_pressure_index':round(supply,4),'candidates':sorted(candidates,key=lambda x:x['distance_m'])[:25],'source':'URA SPACE Master Plan 2025 surrounding polygons','verification_required':True}

def lookup_title_boundary(db_path:Path,boundary_geojson:dict)->dict:
 geometry=shape(boundary_geojson.get('geometry',boundary_geojson));minx,miny,maxx,maxy=geometry.bounds;overlaps=[];metadata={}
 with sqlite3.connect(db_path) as conn:
  conn.row_factory=sqlite3.Row
  try:metadata={row['key']:row['value'] for row in conn.execute('select key,value from metadata')}
  except sqlite3.OperationalError:metadata={}
  for row in conn.execute('select * from zones where minx<=? and maxx>=? and miny<=? and maxy>=?',(maxx,minx,maxy,miny)):
   zone=wkb.loads(row['geom']);intersection=zone.intersection(geometry)
   if not intersection.is_empty:
    share=intersection.area/max(geometry.area,1e-15);item=_row_dict(row);item['boundary_overlap_share']=round(share,6);overlaps.append(item)
 overlaps.sort(key=lambda x:x['boundary_overlap_share'],reverse=True);coverage=sum(x['boundary_overlap_share'] for x in overlaps);primary=overlaps[0] if overlaps else None;resolved=bool(primary and primary['boundary_overlap_share']>=.8)
 return {'matches':[primary] if primary else [],'boundary_overlaps':overlaps,'match_method':'title_boundary_overlap','boundary_coverage':round(coverage,6),'spatial_review_required':not resolved,'metadata':metadata,'current_statutory_plan':'Master Plan 2025','current_plan_url':MP2025_SPACE,'current_plan_verification_required':True,'warning':'Title-boundary overlap resolves address-centroid ambiguity, but written permission, SDCPs and project-specific controls still require professional verification.'}

def enrich_assets(assets:list[dict],db_path:Path)->list[dict]:
 for asset in assets:
  if asset.get('country')=='Singapore' and asset.get('latitude') is not None and db_path.exists():
   asset['ura_zoning']=lookup_zone(db_path,asset['latitude'],asset['longitude']);asset['zoning_exception']=asset['ura_zoning'].get('spatial_review_required',False)
  elif asset.get('country')=='Singapore':asset['ura_zoning']={'matches':[],'current_plan_verification_required':True,'warning':'No verified coordinate available for MP2025 lookup.'}
 return assets

LAND_USE_COLORS={'RESIDENTIAL':'#f6e58d','RESIDENTIAL WITH COMMERCIAL AT 1ST STOREY':'#f8c291','COMMERCIAL':'#1f618d','COMMERCIAL & RESIDENTIAL':'#e67e22','HOTEL':'#c0392b','WHITE':'#ecf0f1','BUSINESS 1':'#6c5ce7','BUSINESS 2':'#4834d4','BUSINESS PARK':'#8e44ad','OPEN SPACE':'#58b368','PARK':'#159957','NATURE RESERVE':'#006b3c','EDUCATIONAL INSTITUTION':'#d4a373','CIVIC & COMMUNITY INSTITUTION':'#b08968','HEALTH & MEDICAL CARE':'#ff7675','TRANSPORT FACILITIES':'#636e72','ROAD':'#dfe6e9','RESERVE SITE':'#bdc3c7','WATERBODY':'#74b9ff'}
def land_use_color(value):
 name=(value or '').upper();return LAND_USE_COLORS.get(name,'#95a5a6')
def zoning_map_geojson(db_path:Path,latitude:float,longitude:float,radius_m=750,limit=700):
 point=Point(longitude,latitude);delta=radius_m/111320;bounds=box(longitude-delta,latitude-delta,longitude+delta,latitude+delta);features=[]
 if db_path.exists():
  with sqlite3.connect(db_path) as conn:
   conn.row_factory=sqlite3.Row;rows=conn.execute('select * from zones where minx<=? and maxx>=? and miny<=? and maxy>=? limit ?',(longitude+delta,longitude-delta,latitude+delta,latitude-delta,limit*3)).fetchall()
   for row in rows:
    geometry=wkb.loads(row['geom'])
    if not geometry.intersects(bounds):continue
    clipped=geometry.intersection(bounds).simplify(.000003,preserve_topology=True)
    if clipped.is_empty:continue
    features.append({'type':'Feature','geometry':mapping(clipped),'properties':{'objectid':row['objectid'],'land_use':row['lu_desc'],'detailed_use':row['lu_dt_desc'],'gpr':row['gpr'],'gpr_text':row['gpr_text'],'region':row['region'],'planning_area':row['planning_area'],'subzone':row['subzone'],'fill_color':land_use_color(row['lu_desc']),'source':row['source_vintage']}})
    if len(features)>=limit:break
 else:
  uses=[('RESIDENTIAL',2.8),('COMMERCIAL',4.2),('PARK',None),('BUSINESS 1',2.5),('HOTEL',3.5),('RESIDENTIAL WITH COMMERCIAL AT 1ST STOREY',2.1),('OPEN SPACE',None),('WHITE',None),('CIVIC & COMMUNITY INSTITUTION',None)];cell=delta/3
  for index,(use,gpr) in enumerate(uses):
   row=index//3;col=index%3;minx=longitude-delta+col*2*cell;miny=latitude-delta+row*2*cell;poly=box(minx,miny,minx+2*cell,miny+2*cell);features.append({'type':'Feature','geometry':mapping(poly),'properties':{'objectid':900000+index,'land_use':use,'detailed_use':'Fictional public demo polygon','gpr':gpr,'gpr_text':str(gpr) if gpr else 'EVA','region':'DEMO REGION','planning_area':'DEMO PLANNING AREA','subzone':'DEMO SUBZONE','fill_color':land_use_color(use),'source':'Fictional public demo'}})
 asset_feature={'type':'Feature','geometry':{'type':'Point','coordinates':[longitude,latitude]},'properties':{'feature_type':'asset','land_use':'Selected asset','fill_color':'#000000'}}
 return {'type':'FeatureCollection','features':features+[asset_feature],'properties':{'center':[longitude,latitude],'radius_m':radius_m,'polygon_count':len(features),'source':'URA SPACE Master Plan 2025' if db_path.exists() else 'Fictional public demo','retrieved_at':'2026-09-23'}}
