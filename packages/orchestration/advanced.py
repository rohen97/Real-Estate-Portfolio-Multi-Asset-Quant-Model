from __future__ import annotations
from pathlib import Path
import math
from shapely.geometry import box,mapping
from packages.orchestration.engine import inputs_for_asset,zone_match
from packages.zoning.engine import calculate_capacity
from packages.zoning.envelope3d import EnvelopeInputs,generate_envelopes
from packages.zoning.viewshed import viewshed,bearing
from packages.zoning.ura import surrounding_development_context
from packages.actions.enbloc import EnBlocInputs,evaluate_enbloc
from packages.actions.detailed_cashflow import DetailedActionInputs,evaluate_detailed_action
ROOT=Path(__file__).resolve().parents[2]
def synthetic_site_polygon(latitude,longitude,area_sqm,aspect=1.5):
 width=math.sqrt(area_sqm*aspect);depth=area_sqm/width;dx=width/(111320*math.cos(math.radians(latitude)))/2;dy=depth/110540/2;return mapping(box(longitude-dx,latitude-dy,longitude+dx,latitude+dy))
def analyse_asset(asset):
 zoning,economics,notes,status,quality=inputs_for_asset(asset);capacity=calculate_capacity(zoning).__dict__;polygon=synthetic_site_polygon(asset['latitude'],asset['longitude'],zoning.site_area_sqm,zoning.aspect_ratio);envelope=generate_envelopes(EnvelopeInputs(site_geojson=polygon,legal_gpr=zoning.legal_gpr,height_limit_m=zoning.height_max_m,site_coverage_max=zoning.site_coverage_max,setback_m=max(zoning.side_setback_m,zoning.front_setback_m),floor_to_floor_m=3.6));zone=zone_match(asset);context=surrounding_development_context(ROOT/'data/processed/ura_mp2025.sqlite',asset['latitude'],asset['longitude'],500,zone.get('objectid') if zone else None);buildings=[]
 for item in context.get('candidates',[]):
  gpr=float(item.get('gpr') or 1.4);buildings.append({'id':item.get('objectid'),'distance_m':max(1,item.get('distance_m',1)),'height_m':gpr*12,'width_m':min(100,max(15,item.get('width_m',25))),'dx_m':item.get('dx_m',0),'dy_m':item.get('dy_m',item.get('distance_m',1))})
 view=viewshed(viewpoint_height_m=30,surrounding_buildings=buildings,current_value_m=economics.current_value_m);preferred=envelope.get('preferred') or {};approved=preferred.get('gross_gfa_sqm',zoning.current_gfa_sqm);cash=evaluate_detailed_action(DetailedActionInputs(action='Redevelop',current_value_m=economics.current_value_m,current_noi_m=economics.current_noi_m,site_area_sqm=zoning.site_area_sqm,current_gfa_sqm=zoning.current_gfa_sqm,approved_gfa_sqm=approved,nla_efficiency=zoning.gross_to_net_efficiency,market_value_per_nla_sqm=zoning.completed_value_per_nla,construction_cost_per_gfa_sqm=zoning.construction_cost_per_gfa,lbc_rate_per_sqm=None,approval_probability=zoning.approval_probability,tenant_relocation_m=economics.current_noi_m*.5,demolition_m=max(1,economics.current_value_m*.015)));segments=' '.join(asset.get('segments',[])).lower();owners=120 if 'residential' in segments else 1;enbloc=evaluate_enbloc(EnBlocInputs(current_strata_value_m=economics.current_value_m,site_area_sqm=zoning.site_area_sqm,existing_gfa_sqm=zoning.current_gfa_sqm,legal_gpr=zoning.legal_gpr,nla_efficiency=zoning.gross_to_net_efficiency,sale_price_per_nla_sqm=zoning.completed_value_per_nla,construction_cost_per_gfa_sqm=zoning.construction_cost_per_gfa,lbc_rate_per_sqm=None,tenure_remaining_years=(asset.get('tenure_hint') or {}).get('remaining_years'),owners_count=owners,tenant_cost_m=economics.current_noi_m*.5));return {'asset_id':asset['asset_id'],'input_status':status,'input_quality':quality,'notes':notes,'site_polygon':polygon,'capacity':capacity,'development_envelope':envelope,'viewshed':view,'enbloc':enbloc,'redevelopment_cashflow':cash,'verification_required':True}
