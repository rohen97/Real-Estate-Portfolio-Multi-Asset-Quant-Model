from __future__ import annotations
from datetime import date,datetime
from typing import Literal
from pydantic import BaseModel,Field,model_validator
class EvidenceRecord(BaseModel):
 evidence_id:str;asset_id:str|None=None;field:str;value:float|str|bool|None;unit:str|None=None;source:str;source_type:str;observation_date:date|None=None;publication_date:date|None=None;effective_date:date|None=None;quality:float=Field(ge=0,le=1);verification_status:Literal['unverified','in_review','verified','rejected']='unverified';reviewer:str|None=None;model_version:str|None=None
class AssetCore(BaseModel):
 asset_id:str;name:str;country:str;address:str|None=None;segments:list[str]=[];ownership_entity:str|None=None;ownership_pct:float|None=Field(default=None,ge=0,le=1);title_lot:str|None=None;tenure:str|None=None;site_area_sqm:float|None=Field(default=None,gt=0);existing_gfa_sqm:float|None=Field(default=None,gt=0);nla_sqm:float|None=Field(default=None,gt=0)
 @model_validator(mode='after')
 def areas(self):
  if self.existing_gfa_sqm and self.nla_sqm and self.nla_sqm>self.existing_gfa_sqm:raise ValueError('NLA cannot exceed GFA')
  return self
class FinancialPeriod(BaseModel):
 asset_id:str;fiscal_year:int;revenue_m:float;gross_rent_m:float=0;other_income_m:float=0;opex_m:float;noi_m:float;occupancy:float=Field(ge=0,le=1);valuation_m:float|None=None;cap_rate:float|None=None;maintenance_capex_m:float=0;verified:bool=False
class LeaseRecord(BaseModel):
 asset_id:str;tenant_id:str;tenant_name:str;use:str;area_sqm:float=Field(gt=0);passing_rent_pa:float=Field(ge=0);market_rent_pa:float|None=None;lease_start:date;lease_expiry:date;break_date:date|None=None;credit_grade:str|None=None;collection_rate:float|None=Field(default=None,ge=0,le=1);verified:bool=False
class PlanningEvent(BaseModel):
 application_id:str;asset_id:str;submission_date:date;decision_date:date|None=None;stage:str;outcome:str|None=None;submitted_gfa_sqm:float|None=None;approved_gfa_sqm:float|None=None;redesign_required:bool|None=None;conditions_count:int=0;decision_reference:str|None=None;verified:bool=False
class CapexProject(BaseModel):
 project_id:str;asset_id:str;action:str;category:str;start_date:date;end_date:date|None=None;budget_m:float=Field(ge=0);spent_m:float=Field(ge=0);committed_m:float=Field(ge=0);success_probability:float=Field(ge=0,le=1);income_disruption_m:float=Field(ge=0);status:str;verified:bool=False
class ModelPrediction(BaseModel):
 asset_id:str;target:str;point:float;p10:float;p50:float;p90:float;model_version:str;features_version:str;as_of:date;source_quality:str
class DecisionRecord(BaseModel):
 decision_id:str;asset_id:str;recommended_action:str;approved_action:str|None=None;reviewer:str|None=None;timestamp:datetime;model_version:str;data_snapshot_id:str;assumptions:dict;constraints:dict;overrides:dict;open_conditions:list[str];rationale:str

class OperationalESGPeriod(BaseModel):
 asset_id:str;fiscal_year:int;energy_use_intensity:float|None=None;carbon_intensity:float|None=None;water_intensity:float|None=None;waste_diversion:float|None=Field(default=None,ge=0,le=1);equipment_downtime_hours:float|None=None;hvac_cop:float|None=None;response_time_hours:float|None=None;certification:str|None=None;rent_collection_rate:float|None=Field(default=None,ge=0,le=1);lease_renewal_rate:float|None=Field(default=None,ge=0,le=1);tenant_default_rate:float|None=Field(default=None,ge=0,le=1);verified:bool=False
