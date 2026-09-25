from __future__ import annotations
from datetime import date
from pathlib import Path
import json,math
CURRENT_YEAR=date.today().year
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
def underwriting_readiness(asset, as_of=None):
 """A boolean synthetic flag is not evidence that underlying inputs are verified."""
 as_of=as_of or date.today();obs=asset.get('observed_inputs') or {};missing=[]
 if asset.get('synthetic_financials') is True:missing.append('synthetic_financials')
 for key in ('current_valuation_m','noi_m','site_area_sqm','existing_gfa_sqm'):
  try:
   value=float(obs.get(key));valid=math.isfinite(value) and (value>0 if key!='noi_m' else True)
  except (TypeError,ValueError):valid=False
  if not valid:missing.append(key)
 for key in ('title_lot','tenure','evidence_source','data_owner'):
  if not obs.get(key):missing.append(key)
 if obs.get('verification_status')!='Verified':missing.append('verified_financial_evidence')
 if not obs.get('zoning_verified') or asset.get('ura_zoning',{}).get('spatial_review_required'):missing.append('verified_title_and_planning')
 for key in ('valuation_date','evidence_date'):
  try:
   age=(as_of-date.fromisoformat(str(obs.get(key))[:10])).days
   if not 0<=age<=365:missing.append(key+'_freshness')
  except (TypeError,ValueError):missing.append(key)
 return {'ready':not missing,'missing':missing,'as_of':as_of.isoformat(),'maximum_evidence_age_days':365}


def evaluate_selection(asset,capacity,actions,surroundings,market_context,current_value_m,current_noi_m,required_return=.078,holding_years=5,transformation_zones=None,cvar_penalty=.3):
 if not actions:raise ValueError('Selection needs at least one action, including Hold')
 if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (current_value_m,current_noi_m,required_return,cvar_penalty,holding_years)) or current_value_m<=0 or not float(holding_years).is_integer() or holding_years<1 or required_return<=-1 or cvar_penalty<0:raise ValueError('Invalid selection valuation, integer horizon or risk parameters')
 if not any(x.get('action')=='Hold' for x in actions):raise ValueError('Hold counterfactual is required')
 spatial_review=asset.get('ura_zoning',{}).get('spatial_review_required',False)
 enbloc=enbloc_option(asset,capacity,current_value_m,spatial_review)
 transform=transformation_exposure(asset,transformation_zones or [],current_value_m,required_return)
 lease=lease_decay(asset,current_value_m)
 surroundings=surroundings or {};available=surroundings.get('status') not in ('unavailable','not_indexed') and bool(surroundings)
 view_probability=surroundings.get('view_block_probability') if available else None
 supply_index=surroundings.get('supply_pressure_index') if available else None
 market=(market_context or {}).get('indicators',{});momentum=market.get('price_qoq')
 adjusted=[]
 for action in actions:
  base=float(action.get('expected_npv_m',action.get('incremental_npv_m',0)))
  raw_cvar=float(action.get('cvar_95_m',0))
  if not math.isfinite(base) or not math.isfinite(raw_cvar):raise ValueError('Action NPV and CVaR must be finite')
  cvar=max(0.,raw_cvar)
  adjusted.append({'action':action['action'],'base_action_npv_m':round(base,3),'adjusted_selection_npv_m':round(base,3),'cvar_95_m':round(cvar,3),'risk_adjusted_score_m':round(base-cvar_penalty*cvar,3),'probability_of_loss':float(action.get('probability_of_loss',0)),
                   'decision_ready':action.get('decision_ready',False),'adjustments':{'enbloc_m':0.,'transformation_m':0.,'view_supply_lease_penalty_m':0.}})
 ordered=sorted(adjusted,key=lambda x:(-x['risk_adjusted_score_m'],x['action']!='Hold',x['action']))
 best=ordered[0];hold=next(x for x in adjusted if x['action']=='Hold');selection_npv=best['adjusted_selection_npv_m'];incremental=selection_npv-hold['base_action_npv_m']
 annuity_factor=sum((1+required_return)**(-year) for year in range(1,int(holding_years)+1))
 equivalent_yield=incremental/annuity_factor/current_value_m
 readiness=underwriting_readiness(asset)
 action=next(x for x in actions if x['action']==best['action'])
 if action.get('decision_ready') is not True:
  readiness['ready']=False;readiness['missing'].append('verified_action_costs_and_cashflows')
 portfolio_signal='Sell / Release' if best['action']=='Sell' else 'Invest / Retain' if best['action']!='Hold' and best['risk_adjusted_score_m']>hold['risk_adjusted_score_m'] else 'Retain / Monitor'
 signal=portfolio_signal if readiness['ready'] else 'Data Required / Monitor'
 reasons=['Ranking uses expected incremental NPV minus '+str(cvar_penalty)+' times nonnegative loss CVaR, with Hold as the counterfactual.','En-bloc, transformation and spatial screens are hypotheses requiring underwriting; they are not added to action NPV.']
 if not available:reasons.append('Surrounding geometry is unavailable; zero obstruction or supply risk has not been established.')
 if readiness['missing']:reasons.append('Outstanding evidence: '+', '.join(readiness['missing']))
 opportunity={'status':'research_candidate' if incremental>0 else 'no_positive_modelled_uplift','expected_incremental_npv_m':round(incremental,3),'risk_adjusted_margin_over_hold_m':round(best['risk_adjusted_score_m']-hold['risk_adjusted_score_m'],3),'margin_to_runner_up_m':round(best['risk_adjusted_score_m']-ordered[1]['risk_adjusted_score_m'],3) if len(ordered)>1 else None,'break_even_additional_pv_cost_m':round(max(0,incremental),3),'annual_equivalent_incremental_yield':round(equivalent_yield,6),'interpretation':'Modelled opportunity versus Hold, not excess realised return. Additional discounted costs consume the break-even cost allowance one-for-one.'}
 return {'signal':signal,'preferred_action':best['action'],'selection_npv_m':round(selection_npv,3),'risk_adjusted_score_m':best['risk_adjusted_score_m'],'cvar_penalty':cvar_penalty,
         'annual_expected_alpha':None,'alpha_status':'not_estimated_requires_out_of_sample_risk_adjusted_benchmark','expected_total_return':None,'operating_yield':round(current_noi_m/current_value_m,5),'market_return':None,'incremental_action_return':round(equivalent_yield,6),'return_basis':'annual equivalent incremental NPV yield; do not add to NOI yield or historical price growth','required_return':required_return,'acquisition_signal':'Not assessed: transaction price and benchmark evidence required','portfolio_signal':portfolio_signal if readiness['ready'] else 'Data Required / Monitor','action_npv_m':best['base_action_npv_m'],'action_comparison':adjusted,'opportunity':opportunity,'readiness':readiness,
         'zoning_option_value_m':round(float(capacity.get('residual_value_m',0)),3),'enbloc':{**enbloc,'included_in_selection':False},'transformation':{**transform,'included_in_selection':False},'view_risk':{'probability':view_probability,'penalty_m':None,'status':'screening_only' if available else 'unavailable'},'supply_pressure':{'index':supply_index,'penalty_m':None,'market_momentum_qoq':momentum,'status':'screening_only' if available else 'unavailable'},'lease_decay':{**lease,'included_in_selection':False},'probability_of_loss':best['probability_of_loss'],'reasons':reasons,'quality':'verified_underwriting_screen' if readiness['ready'] else 'provisional','warning':'Screening model only. No demonstrated alpha. Unverified option values are excluded to avoid overlap with cash-flow valuation.'}


def load_transformation_zones(root:Path):
 path=root/'data/public/transformation_zones.json';return json.loads(path.read_text()) if path.exists() else []
