from __future__ import annotations
from datetime import date
from pathlib import Path
import json,math
CURRENT_YEAR=2026
def haversine_km(lat1,lon1,lat2,lon2):
 r=6371;phi1=math.radians(lat1);phi2=math.radians(lat2);dphi=math.radians(lat2-lat1);dlambda=math.radians(lon2-lon1);a=math.sin(dphi/2)**2+math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2;return 2*r*math.asin(math.sqrt(a))
def transformation_exposure(asset,zones,current_value_m,discount_rate=.078):
 if asset.get('latitude') is None:return {'value_m':0,'exposures':[],'quality':'unavailable'}
 exposures=[];total=0
 for z in zones:
  distance=haversine_km(asset['latitude'],asset['longitude'],z['latitude'],z['longitude']);proximity=max(0,1-distance/z['influence_radius_km']);years=max(1,z['target_year']-CURRENT_YEAR);value=current_value_m*z['potential_value_uplift']*z['delivery_probability']*proximity/(1+discount_rate)**years
  if proximity>0:exposures.append({'zone':z['name'],'distance_km':round(distance,2),'proximity_factor':round(proximity,4),'target_year':z['target_year'],'delivery_probability':z['delivery_probability'],'discounted_value_m':round(value,3),'source':z['source']});total+=value
 return {'value_m':round(total,3),'exposures':exposures,'quality':'screening_geofence'}
def lease_decay(asset,current_value_m):
 hint=asset.get('tenure_hint') or {};remaining=hint.get('remaining_years');kind=hint.get('type','Unknown')
 if kind=='Freehold':return {'penalty_m':0,'factor':0,'remaining_years':None,'tenure':kind,'quality':hint.get('source')}
 if remaining is None:return {'penalty_m':round(current_value_m*.015,3),'factor':.015,'remaining_years':None,'tenure':kind,'quality':'unknown commencement; uncertainty penalty'}
 factor=0 if remaining>=80 else .01 if remaining>=60 else .04 if remaining>=40 else .1 if remaining>=25 else .2
 return {'penalty_m':round(current_value_m*factor,3),'factor':factor,'remaining_years':remaining,'tenure':kind,'quality':hint.get('source')}
def enbloc_option(asset,capacity,current_value_m,spatial_review=False):
 segments=' '.join(asset.get('segments',[])).lower();is_strata='residential' in segments and 'landed' not in segments;statutory=max(float(capacity.get('statutory_gfa_sqm',0)),1);unused=max(0,float(capacity.get('unused_economic_gfa_sqm',0)));underutilisation=min(1,unused/statutory);tenure=asset.get('tenure_hint',{}).get('type','Unknown');tenure_factor=.9 if tenure=='Freehold' else .65 if '99' in tenure else .45;residual=max(0,float(capacity.get('residual_value_m',0)));developer_margin=max(0,(residual-current_value_m*.08)/max(current_value_m,1));logit=-2.3+3.2*underutilisation+1.1*tenure_factor+1.5*min(1,developer_margin)-1.1*int(spatial_review);probability=1/(1+math.exp(-logit)) if is_strata else .05*underutilisation;option=residual*probability
 return {'probability':round(probability,4),'option_value_m':round(option,3),'underutilisation':round(underutilisation,4),'tenure_factor':tenure_factor,'collective_sale_applicable':is_strata,'warning':'Screening probability only. Owner consent, Land Betterment Charge, acquisition premium and technical feasibility require project evidence.'}
def evaluate_selection(asset,capacity,actions,surroundings,market_context,current_value_m,current_noi_m,required_return=.078,holding_years=5,transformation_zones=None):
 transformation_zones=transformation_zones or [];spatial_review=asset.get('ura_zoning',{}).get('spatial_review_required',False);enbloc=enbloc_option(asset,capacity,current_value_m,spatial_review);transform=transformation_exposure(asset,transformation_zones,current_value_m,required_return);lease=lease_decay(asset,current_value_m);segments=' '.join(asset.get('segments',[])).lower();view_sensitive=any(x in segments for x in ['residential','hotel','serviced residence']);view_probability=float(surroundings.get('view_block_probability',0)) if surroundings else 0;view_penalty=current_value_m*view_probability*(.045 if view_sensitive else .012);supply_index=float(surroundings.get('supply_pressure_index',0)) if surroundings else 0;market=market_context.get('indicators',{}) if market_context else {};momentum=float(market.get('price_qoq',0) or 0);supply_penalty=current_value_m*max(0,supply_index*.04-momentum*.5)
 multipliers={'Hold':(1,1,1),'Retrofit':(.8,1,.9),'Repurpose':(.3,1,.7),'Redevelop':(0,1,.4),'Sell':(0,.3,0)};adjusted=[]
 for action in actions:
  name=action['action'];enbloc_mult,transform_mult,penalty_mult=multipliers.get(name,(0,0,1));base=float(action.get('expected_npv_m',action.get('incremental_npv_m',0)));value=base+enbloc['option_value_m']*enbloc_mult+transform['value_m']*transform_mult-(view_penalty+supply_penalty+lease['penalty_m'])*penalty_mult;adjusted.append({'action':name,'base_action_npv_m':round(base,3),'adjusted_selection_npv_m':round(value,3),'probability_of_loss':float(action.get('probability_of_loss',0)),'adjustments':{'enbloc_m':round(enbloc['option_value_m']*enbloc_mult,3),'transformation_m':round(transform['value_m']*transform_mult,3),'view_supply_lease_penalty_m':round((view_penalty+supply_penalty+lease['penalty_m'])*penalty_mult,3)}})
 best=max(adjusted,key=lambda x:x['adjusted_selection_npv_m']-.3*max(0,x['probability_of_loss']*current_value_m*.1));selection_npv=best['adjusted_selection_npv_m'];operating_yield=current_noi_m/max(current_value_m,1);market_return=max(-.05,min(.12,momentum*4));incremental_return=selection_npv/max(current_value_m,1)/holding_years;expected_total_return=operating_yield+market_return+incremental_return;annual_alpha=expected_total_return-required_return;prob_loss=best['probability_of_loss'];acquisition_signal='Buy' if annual_alpha>=.02 and prob_loss<.35 else 'Avoid' if annual_alpha<0 else 'Watch';portfolio_signal='Sell / Release' if best['action']=='Sell' or annual_alpha<-.01 else 'Invest / Retain' if annual_alpha>=.015 and prob_loss<.35 else 'Retain / Monitor';signal='Data Required / Monitor' if asset.get('synthetic_financials',True) else portfolio_signal;reasons=[]
 if enbloc['option_value_m']>1:reasons.append('Positive redevelopment/en-bloc option value')
 if transform['value_m']>1:reasons.append('Discounted transformation-zone exposure')
 if view_penalty>1:reasons.append('Surrounding high-density/view-loss risk')
 if supply_penalty>1:reasons.append('Future competing-supply pressure')
 if lease['penalty_m']>1:reasons.append('Lease-decay or tenure uncertainty')
 if spatial_review:reasons.append('Title-lot zoning review required')
 return {'signal':signal,'preferred_action':best['action'],'selection_npv_m':round(selection_npv,3),'annual_expected_alpha':round(annual_alpha,5),'expected_total_return':round(expected_total_return,5),'operating_yield':round(operating_yield,5),'market_return':round(market_return,5),'incremental_action_return':round(incremental_return,5),'required_return':required_return,'acquisition_signal':acquisition_signal,'portfolio_signal':portfolio_signal,'action_npv_m':best['base_action_npv_m'],'action_comparison':adjusted,'zoning_option_value_m':round(float(capacity.get('residual_value_m',0)),3),'enbloc':enbloc,'transformation':transform,'view_risk':{'probability':round(view_probability,4),'penalty_m':round(view_penalty,3)},'supply_pressure':{'index':round(supply_index,4),'penalty_m':round(supply_penalty,3),'market_momentum_qoq':momentum},'lease_decay':lease,'probability_of_loss':prob_loss,'reasons':reasons,'quality':'provisional' if asset.get('synthetic_financials',True) else 'observed','warning':'Selection signal is an economic screening output, not a transaction instruction.'}

def load_transformation_zones(root:Path):
 path=root/'data/public/transformation_zones.json';return json.loads(path.read_text()) if path.exists() else []
