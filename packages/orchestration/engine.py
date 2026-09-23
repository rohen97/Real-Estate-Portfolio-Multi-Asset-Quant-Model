from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json
from packages.zoning.engine import ZoningAssumptions,calculate_capacity
from packages.zoning.approval import approval_path
from packages.valuation.engine import AssetEconomics,proxy_economics,dcf,value_actions
from packages.scenarios.engine import simulate_actions
from packages.market.public_data import load_snapshot,context_for_asset
from packages.zoning.ura import surrounding_development_context
from packages.selection.engine import evaluate_selection,load_transformation_zones
ROOT=Path(__file__).resolve().parents[2]
def zone_match(asset):
 matches=asset.get('ura_zoning',{}).get('matches',[]);return next((x for x in matches if x.get('gpr')),matches[0] if matches else None)
def compatible_zone(asset,match):
 if not match:return False
 land=(match.get('lu_desc') or '').upper();segments=' '.join(asset.get('segments',[])).lower()
 if any(x in land for x in ['ROAD','WATERBODY','RESERVE SITE','OPEN SPACE','PARK','EDUCATIONAL INSTITUTION','TRANSPORT FACILITIES']):return False
 allowed=[]
 if any(x in segments for x in ['commercial','office','medical']):allowed+=['COMMERCIAL','COMMERCIAL & RESIDENTIAL','RESIDENTIAL WITH COMMERCIAL','BUSINESS','WHITE']
 if any(x in segments for x in ['industrial','factory','warehouse']):allowed+=['BUSINESS','INDUSTRIAL','WHITE']
 if 'mall' in segments:allowed+=['COMMERCIAL','COMMERCIAL & RESIDENTIAL','WHITE']
 if 'hotel' in segments or 'serviced residence' in segments:allowed+=['HOTEL','COMMERCIAL','WHITE','RESIDENTIAL']
 if 'residential' in segments:allowed+=['RESIDENTIAL','WHITE','COMMERCIAL & RESIDENTIAL','RESIDENTIAL WITH COMMERCIAL']
 if allowed:return any(x in land for x in set(allowed))
 return True
def inputs_for_asset(asset):
 match=zone_match(asset);obs=asset.get('observed_inputs');segments=' '.join(asset.get('segments',[])).lower();zone_ok=compatible_zone(asset,match);spatial_review=asset.get('ura_zoning',{}).get('spatial_review_required',False)
 if obs:
  gpr=float(match['gpr']) if zone_ok and match.get('gpr') else 4.2 if 'commercial' in segments or 'mall' in segments else 2.5 if 'industrial' in segments else 2.1
  z=ZoningAssumptions(site_area_sqm=obs['site_area_sqm'],current_gfa_sqm=obs['existing_gfa_sqm'],legal_gpr=gpr,site_coverage_max=obs.get('site_coverage_max') or (.48 if 'commercial' in segments else .55 if 'industrial' in segments else .4),height_max_m=obs.get('height_limit_m') or (120 if gpr>=4 else 80),front_setback_m=obs.get('front_setback_m') or 7.5,rear_setback_m=obs.get('rear_setback_m') or 7.5,side_setback_m=obs.get('side_setback_m') or 4.5,approval_probability=.62)
  e=AssetEconomics(current_value_m=obs['current_valuation_m'],current_noi_m=obs['noi_m'],occupancy=obs['occupancy'],interest_rate=obs.get('interest_rate') or .04 if hasattr(AssetEconomics,'interest_rate') else .04,source_quality='verified company underwriting input') if False else AssetEconomics(current_value_m=obs['current_valuation_m'],current_noi_m=obs['noi_m'],occupancy=obs['occupancy'],source_quality='verified company underwriting input')
  notes=[]
  if not obs.get('zoning_verified'):notes.append('Title boundary/current use not fully verified; planning capacity remains provisional')
  if spatial_review:notes.append('Coordinate required nearest-polygon or special-use review')
  if not zone_ok:notes.append('MP2025 land-use match is incompatible or non-developable; legal GPR uses a visible asset-class proxy')
  return z,e,notes,'observed_run','high - verified underwriting input'
 size=asset.get('size_from_sqft');area=(size*.092903/.72 if size else 6500 if 'mall' in segments or 'hotel' in segments else 4200 if 'commercial' in segments else 2600);gpr=float(match['gpr']) if zone_ok and match.get('gpr') else 4.2 if 'commercial' in segments or 'mall' in segments else 2.5 if 'industrial' in segments else 2.1;current_gfa=area*gpr*.72;coverage=.48 if 'commercial' in segments else .55 if 'industrial' in segments else .4;height=120 if gpr>=4 else 80
 notes=['site area proxy','current GFA proxy','company valuation, NOI, tenure, leases, debt and capex required']
 if spatial_review:notes.append('Coordinate required nearest-polygon or special-use review')
 if not zone_ok:notes.append('MP2025 land-use match is incompatible or non-developable; GPR uses asset-class proxy')
 return ZoningAssumptions(site_area_sqm=area,current_gfa_sqm=current_gfa,legal_gpr=gpr,site_coverage_max=coverage,height_max_m=height,approval_probability=.62),proxy_economics(asset),notes, 'provisional_proxy_run','low - portfolio workbook is a catalogue, not an underwriting dataset'
def run_asset(asset,seed=20260922):
 if asset.get('country')!='Singapore':return {**asset,'model_status':'outside_singapore_scope','zoning':None,'verification_required':True}
 assumptions,economics,notes,status,quality=inputs_for_asset(asset);capacity=calculate_capacity(assumptions,seed);approval=approval_path(seed=seed);base=dcf(economics);actions=simulate_actions(value_actions(economics,capacity.__dict__),seed=seed);preferred=max(actions,key=lambda x:x['expected_npv_m']-.3*max(0,x['cvar_95_m']));required=economics.discount_rate;expected_return=max(-.5,min(.5,(preferred['expected_npv_m']/max(economics.current_value_m,1))/max(preferred['execution_years'],.5)));verification=status!='observed_run' or bool(notes);market_context=context_for_asset(asset,load_snapshot(ROOT));zone=zone_match(asset);surroundings=surrounding_development_context(ROOT/'data/processed/ura_mp2025.sqlite',asset['latitude'],asset['longitude'],500,zone.get('objectid') if zone else None) if asset.get('latitude') is not None else {'status':'unavailable'};selection=evaluate_selection(asset,capacity.__dict__,actions,surroundings,market_context,economics.current_value_m,economics.current_noi_m,required,5,load_transformation_zones(ROOT))
 selected_action=selection['preferred_action'];selected_case=next((x for x in actions if x['action']==selected_action),preferred)
 return {**asset,'market_context':market_context,'surrounding_context':surroundings,'selection':selection,'model_status':status,'input_quality':quality,'proxy_inputs':notes,'zoning_source':asset.get('ura_zoning'),'zoning_model_status':'verified_match' if compatible_zone(asset,zone_match(asset)) and not asset.get('ura_zoning',{}).get('spatial_review_required',False) else 'review_required','statutory_gpr_used':assumptions.legal_gpr,'gpr_source':'MP2025' if compatible_zone(asset,zone_match(asset)) else 'asset_class_proxy','capacity':capacity.__dict__,'approval':approval,'economics':economics.__dict__,'dcf':base,'actions':actions,'recommendation':{'action':selected_action,'management_label':{'Hold':'Retain','Retrofit':'Retrofit','Repurpose':'Repurpose','Redevelop':'Repurpose','Sell':'Release'}[selected_action],'expected_npv_m':selected_case['expected_npv_m'],'probability_of_loss':selected_case['probability_of_loss'],'selection_signal':selection['signal'],'explanation':f"{selected_action} maximises the zoning- and market-adjusted selection NPV. Selection screen: {selection['signal']}. {'Observed company inputs are in use.' if status=='observed_run' else 'Replace proxy inputs before decision use.'}"},'expected_alpha':selection['annual_expected_alpha'],'required_return':required,'model_version':'economic-model-v2-selection-0.2','verification_required':verification,'cache_key':sha256(json.dumps({'asset':asset,'seed':seed},sort_keys=True,default=str).encode()).hexdigest()[:16]}
def run_portfolio(assets,seed=20260922):return [run_asset(asset,seed+i) for i,asset in enumerate(assets)]
