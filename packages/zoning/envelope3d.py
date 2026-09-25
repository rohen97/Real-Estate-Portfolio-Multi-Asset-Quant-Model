from __future__ import annotations
from dataclasses import dataclass
import math
from shapely.geometry import shape,Polygon,mapping
from shapely.affinity import scale
from shapely.ops import transform
@dataclass
class EnvelopeInputs:
 site_geojson:dict;legal_gpr:float;height_limit_m:float;site_coverage_max:float;setback_m:float=7.5;tower_spacing_m:float=24;floor_to_floor_m:float=3.6;core_loss_rate:float=.18;parking_spaces_per_100sqm:float=.8;parking_area_per_space_sqm:float=32;access_area_rate:float=.06;daylight_depth_m:float=18

def to_local(geom):
 c=geom.centroid;lat=c.y;scale_x=111320*math.cos(math.radians(lat));scale_y=110540
 return transform(lambda x,y,z=None:((x-c.x)*scale_x,(y-c.y)*scale_y),geom),c,scale_x,scale_y

def to_wgs(local,center,scale_x,scale_y):
 return mapping(transform(lambda x,y,z=None:(x/scale_x+center.x,y/scale_y+center.y),local))

def generate_envelopes(x:EnvelopeInputs,max_towers=4):
 source=shape(x.site_geojson.get('geometry',x.site_geojson))
 if source.is_empty or not source.is_valid or source.geom_type not in ('Polygon','MultiPolygon'):raise ValueError('A valid polygonal site is required')
 values=(x.legal_gpr,x.height_limit_m,x.site_coverage_max,x.setback_m,x.tower_spacing_m,x.floor_to_floor_m,x.core_loss_rate,x.access_area_rate,x.daylight_depth_m)
 if not all(math.isfinite(v) and v>=0 for v in values) or x.floor_to_floor_m<=0 or not 0<x.site_coverage_max<=1 or x.core_loss_rate+x.access_area_rate>=1:raise ValueError('Invalid physical envelope parameters')
 site,center,sx,sy=to_local(source);site_area=site.area;buildable=site.buffer(-x.setback_m);coverage_limit=site_area*x.site_coverage_max;legal_gfa=site_area*x.legal_gpr;max_storeys=int(x.height_limit_m//x.floor_to_floor_m);options=[]
 if buildable.is_empty or max_storeys<1 or legal_gfa<=0:return {'site_area_sqm':round(site_area,2),'legal_gfa_sqm':round(legal_gfa,2),'buildable_footprint_sqm':0 if buildable.is_empty else round(buildable.area,2),'max_storeys':max_storeys,'options':[],'preferred':None,'status':'no_feasible_envelope','decision_ready':False,'method':'Setback, height or GPR constraints prevent a feasible screening envelope'}
 minx,miny,maxx,maxy=buildable.bounds
 for towers in range(1,max_towers+1):
  available_width=maxx-minx-(towers-1)*x.tower_spacing_m
  if available_width<=10:continue
  plate_width=available_width/towers;plate_depth=min(maxy-miny,x.daylight_depth_m*2);plate=min(coverage_limit/towers,plate_width*plate_depth);side=math.sqrt(max(plate,1));footprints=[]
  for i in range(towers):
   cx=minx+side/2+i*(side+x.tower_spacing_m);cy=(miny+maxy)/2;poly=Polygon([(cx-side/2,cy-side/2),(cx+side/2,cy-side/2),(cx+side/2,cy+side/2),(cx-side/2,cy+side/2)]).intersection(buildable)
   if not poly.is_empty:
    if poly.geom_type=='MultiPolygon':poly=max(poly.geoms,key=lambda part:part.area)
    if poly.geom_type=='Polygon' and poly.area>1:footprints.append(poly)
  total_plate=sum(p.area for p in footprints)
  if not footprints or total_plate<=0:continue
  if total_plate>legal_gfa:
   ratio=math.sqrt(legal_gfa/total_plate)*.999999;footprints=[scale(p,xfact=ratio,yfact=ratio,origin='centroid').intersection(buildable) for p in footprints];total_plate=sum(p.area for p in footprints)
  storeys=min(max_storeys,int(legal_gfa/total_plate+1e-9));gross=total_plate*storeys;parking_spaces=gross/100*x.parking_spaces_per_100sqm;parking_area=parking_spaces*x.parking_area_per_space_sqm;net=gross*(1-x.core_loss_rate-x.access_area_rate);daylight_score=min(1,(sum(p.length for p in footprints)*x.daylight_depth_m)/max(gross,1));efficiency=net/max(gross,1);score=net*.001+daylight_score*10-efficiency*0+min(0,(max_storeys-storeys))*2
  options.append({'towers':len(footprints),'storeys':storeys,'height_m':round(storeys*x.floor_to_floor_m,2),'floorplate_sqm':round(total_plate,2),'gross_gfa_sqm':round(gross,2),'net_area_sqm':round(net,2),'efficiency':round(efficiency,4),'parking_spaces':round(parking_spaces),'parking_area_sqm':round(parking_area,2),'daylight_score':round(daylight_score,4),'binding_constraints':[v for v,b in [('GPR',gross>=legal_gfa*.999),('Height',storeys>=max_storeys),('Coverage',total_plate>=coverage_limit*.99),('Setbacks',buildable.area<site.area*.8)] if b],'footprints_geojson':[to_wgs(p,center,sx,sy) for p in footprints],'boxes':[{'x':round(p.centroid.x,2),'y':round(p.centroid.y,2),'footprint_sqm':round(p.area,2),'height_m':round(storeys*x.floor_to_floor_m,2)} for p in footprints],'score':score})
 return {'site_area_sqm':round(site_area,2),'legal_gfa_sqm':round(legal_gfa,2),'buildable_footprint_sqm':round(buildable.area,2),'max_storeys':max_storeys,'options':sorted(options,key=lambda o:o['score'],reverse=True),'preferred':max(options,key=lambda o:o['score']) if options else None,'status':'screening_only','decision_ready':False,'method':'Screening-level 3D envelope; requires architect, surveyor, parking, fire access and daylight verification'}
