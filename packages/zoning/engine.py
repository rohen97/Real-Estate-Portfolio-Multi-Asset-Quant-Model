from __future__ import annotations
from dataclasses import dataclass,asdict
import math
import numpy as np

@dataclass
class ZoningAssumptions:
 site_area_sqm:float
 current_gfa_sqm:float
 legal_gpr:float
 site_coverage_max:float=.45
 height_max_m:float=80
 floor_to_floor_m:float=3.6
 front_setback_m:float=7.5
 rear_setback_m:float=7.5
 side_setback_m:float=4.5
 aspect_ratio:float=1.5
 gross_to_net_efficiency:float=.78
 de_facto_factor:float=.92
 approval_probability:float=.62
 construction_cost_per_gfa:float=4200
 completed_value_per_nla:float=9500
 professional_and_finance_cost_rate:float=.18
 contingency_rate:float=.1
 source_vintage:str='URA SPACE Master Plan 2025 - project-specific verification required'

@dataclass
class CapacityResult:
 statutory_gfa_sqm:float
 geometric_gfa_sqm:float
 physical_gfa_sqm:float
 de_facto_gfa_sqm:float
 expected_approved_gfa_sqm:float
 economic_gfa_sqm:float
 unused_economic_gfa_sqm:float
 buildable_footprint_sqm:float
 storeys_by_height:int
 binding_constraints:list[str]
 sensitivities:dict[str,float]
 residual_value_m:float
 p10_gfa_sqm:float
 p50_gfa_sqm:float
 p90_gfa_sqm:float
 verification_required:bool
 methodology_version:str='sg-capacity-0.2'

def calculate_capacity(x:ZoningAssumptions,seed=20260922)->CapacityResult:
 width=math.sqrt(x.site_area_sqm*x.aspect_ratio);depth=x.site_area_sqm/width
 buildable_width=max(0,width-2*x.side_setback_m);buildable_depth=max(0,depth-x.front_setback_m-x.rear_setback_m)
 footprint_by_setbacks=buildable_width*buildable_depth;footprint=min(footprint_by_setbacks,x.site_area_sqm*x.site_coverage_max)
 storeys=max(1,int(x.height_max_m//x.floor_to_floor_m));statutory=x.site_area_sqm*x.legal_gpr;geometric=footprint*storeys;physical=min(statutory,geometric);de_facto=physical*x.de_facto_factor;expected=de_facto*x.approval_probability
 gross_value_per_gfa=x.completed_value_per_nla*x.gross_to_net_efficiency;all_in_cost=x.construction_cost_per_gfa*(1+x.professional_and_finance_cost_rate+x.contingency_rate);margin=max(0,gross_value_per_gfa-all_in_cost)
 economic=de_facto if margin>0 else x.current_gfa_sqm;unused=max(0,economic-x.current_gfa_sqm);residual=unused*margin/1e6
 binding=[]
 if statutory<=geometric+1:binding.append('plot_ratio')
 if footprint==x.site_area_sqm*x.site_coverage_max:binding.append('site_coverage')
 if footprint==footprint_by_setbacks:binding.append('setbacks')
 if geometric<statutory:binding.append('height_or_geometry')
 rng=np.random.default_rng(seed);draws=np.clip(rng.beta(max(1,x.approval_probability*18),max(1,(1-x.approval_probability)*18),4000),.05,.99)*rng.normal(x.de_facto_factor,.06,4000)*physical
 sensitivities={}
 for name,delta in [('legal_gpr',.1),('site_coverage_max',.05),('height_max_m',3.6),('front_setback_m',-1),('side_setback_m',-1),('approval_probability',.05)]:
  y=ZoningAssumptions(**asdict(x));setattr(y,name,max(.01,getattr(y,name)+delta));
  if name=='approval_probability':value=de_facto*y.approval_probability
  else:
   w=math.sqrt(y.site_area_sqm*y.aspect_ratio);d=y.site_area_sqm/w;fp=min(max(0,w-2*y.side_setback_m)*max(0,d-y.front_setback_m-y.rear_setback_m),y.site_area_sqm*y.site_coverage_max);value=min(y.site_area_sqm*y.legal_gpr,fp*max(1,int(y.height_max_m//y.floor_to_floor_m)))*y.de_facto_factor*y.approval_probability
  sensitivities[name]=round(value-expected,1)
 return CapacityResult(round(statutory,1),round(geometric,1),round(physical,1),round(de_facto,1),round(expected,1),round(economic,1),round(unused,1),round(footprint,1),storeys,binding,sensitivities,round(residual,2),round(float(np.quantile(draws,.1)),1),round(float(np.quantile(draws,.5)),1),round(float(np.quantile(draws,.9)),1),True)

def insufficient_capacity(reason:str)->dict:
 return {'status':'insufficient_data','reason':reason,'required_inputs':['verified lot/site area','current GFA','current URA MP2025 zoning/GPR','height and setback controls','current use and tenure'],'verification_required':True}
