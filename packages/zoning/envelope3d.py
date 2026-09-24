from __future__ import annotations
from dataclasses import dataclass
import math
from shapely.geometry import shape,Polygon,mapping
from shapely.affinity import translate
@dataclass
class EnvelopeInputs:
 site_geojson:dict;legal_gpr:float;height_limit_m:float;site_coverage_max:float;setback_m:float=7.5;tower_spacing_m:float=24;floor_to_floor_m:float=3.6;core_loss_rate:float=.18;parking_spaces_per_100sqm:float=.8;parking_area_per_space_sqm:float=32;access_area_rate:float=.06;daylight_depth_m:float=18

def to_local(geom):
 c=geom.centroid;lat=c.y;scale_x=111320*math.cos(math.radians(lat));scale_y=110540;coords=[((x-c.x)*scale_x,(y-c.y)*scale_y) for x,y in geom.exterior.coords];return Polygon(coords),c,scale_x,scale_y
def to_wgs(local,center,scale_x,scale_y):return {'type':'Polygon','coordinates':[[(x/scale_x+center.x,y/scale_y+center.y) for x,y in local.exterior.coords]]}
def generate_envelopes(x:EnvelopeInputs,max_towers=4):
 source=shape(x.site_geojson.get('geometry',x.site_geojson));site,center,sx,sy=to_local(source);site_area=site.area;buildable=site.buffer(-x.setback_m);buildable=buildable if not buildable.is_empty else site;coverage_limit=site_area*x.site_coverage_max;legal_gfa=site_area*x.legal_gpr;max_storeys=max(1,int(x.height_limit_m//x.floor_to_floor_m));options=[]
 minx,miny,maxx,maxy=buildable.bounds
 for towers in range(1,max_towers+1):
  available_width=maxx-minx-(towers-1)*x.tower_spacing_m
  if available_width<=10:continue
  plate_width=available_width/towers;plate_depth=min(maxy-miny,x.daylight_depth_m*2);plate=min(coverage_limit/towers,plate_width*plate_depth);side=math.sqrt(max(plate,1));footprints=[]
  for i in range(towers):
   cx=minx+side/2+i*(side+x.tower_spacing_m);cy=(miny+maxy)/2;poly=Polygon([(cx-side/2,cy-side/2),(cx+side/2,cy-side/2),(cx+side/2,cy+side/2),(cx-side/2,cy+side/2)]).intersection(buildable)
   if not poly.is_empty:footprints.append(poly)
  total_plate=sum(p.area for p in footprints);storeys=min(max_storeys,max(1,int(math.ceil(legal_gfa/max(total_plate,1)))));gross=min(legal_gfa,total_plate*storeys);parking_spaces=gross/100*x.parking_spaces_per_100sqm;parking_area=parking_spaces*x.parking_area_per_space_sqm;net=gross*(1-x.core_loss_rate-x.access_area_rate);daylight_score=min(1,(sum(p.length for p in footprints)*x.daylight_depth_m)/max(gross,1));efficiency=net/max(gross,1);score=net*.001+daylight_score*10-efficiency*0+min(0,(max_storeys-storeys))*2
  options.append({'towers':len(footprints),'storeys':storeys,'height_m':round(storeys*x.floor_to_floor_m,2),'floorplate_sqm':round(total_plate,2),'gross_gfa_sqm':round(gross,2),'net_area_sqm':round(net,2),'efficiency':round(efficiency,4),'parking_spaces':round(parking_spaces),'parking_area_sqm':round(parking_area,2),'daylight_score':round(daylight_score,4),'binding_constraints':[v for v,b in [('GPR',gross>=legal_gfa*.999),('Height',storeys>=max_storeys),('Coverage',total_plate>=coverage_limit*.99),('Setbacks',buildable.area<site.area*.8)] if b],'footprints_geojson':[to_wgs(p,center,sx,sy) for p in footprints],'boxes':[{'x':round(p.centroid.x,2),'y':round(p.centroid.y,2),'footprint_sqm':round(p.area,2),'height_m':round(storeys*x.floor_to_floor_m,2)} for p in footprints],'score':score})
 return {'site_area_sqm':round(site_area,2),'legal_gfa_sqm':round(legal_gfa,2),'buildable_footprint_sqm':round(buildable.area,2),'max_storeys':max_storeys,'options':sorted(options,key=lambda o:o['score'],reverse=True),'preferred':max(options,key=lambda o:o['score']) if options else None,'method':'Screening-level 3D envelope; requires architect, surveyor, parking, fire access and daylight verification'}
