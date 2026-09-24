from __future__ import annotations
from datetime import date
def progressive(value,brackets):
 remaining=max(0,float(value));tax=0
 for amount,rate in brackets:
  taxable=remaining if amount is None else min(remaining,amount);tax+=taxable*rate;remaining-=taxable
  if remaining<=0:break
 return tax
def buyer_stamp_duty(value_sgd,residential_share=1.0):
 residential_share=min(1,max(0,residential_share));res=value_sgd*residential_share;non=value_sgd-res;res_tax=progressive(res,[(180000,.01),(180000,.02),(640000,.03),(500000,.04),(1500000,.05),(None,.06)]);non_tax=progressive(non,[(180000,.01),(180000,.02),(640000,.03),(500000,.04),(None,.05)]);return {'total_sgd':int(res_tax+non_tax),'residential_sgd':int(res_tax),'non_residential_sgd':int(non_tax),'effective_date':'2023-02-15','source':'IRAS BSD rates'}
def seller_stamp_duty(value_sgd,acquisition_date:date,disposal_date:date,residential_share=1.0):
 if disposal_date<=acquisition_date:return {'total_sgd':0,'rate':0}
 years=(disposal_date-acquisition_date).days/365.25;rate=0
 if acquisition_date>=date(2025,7,4):rate=.16 if years<=1 else .12 if years<=2 else .08 if years<=3 else .04 if years<=4 else 0
 elif acquisition_date>=date(2017,3,11):rate=.12 if years<=1 else .08 if years<=2 else .04 if years<=3 else 0
 return {'total_sgd':int(value_sgd*residential_share*rate),'rate':rate,'holding_years':years,'source':'IRAS residential SSD rules'}
def land_betterment_charge(additional_gfa_sqm,rate_per_sqm,charge_fraction=.7):
 if rate_per_sqm is None:return {'status':'required','total_sgd':None,'warning':'LBC sector/use-group rate must be supplied from the current SLA table'}
 value=max(0,additional_gfa_sqm)*max(0,rate_per_sqm)*charge_fraction;return {'status':'calculated','total_sgd':value,'charge_fraction':charge_fraction,'rate_per_sqm':rate_per_sqm,'source':'SLA Land Betterment Charge table; verify current sector and use group'}
