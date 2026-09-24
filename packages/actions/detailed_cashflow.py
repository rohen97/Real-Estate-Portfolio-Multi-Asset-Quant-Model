from __future__ import annotations
from dataclasses import dataclass
from datetime import date
import math
import numpy as np
from scipy.optimize import brentq
from packages.economics.singapore_costs import buyer_stamp_duty,seller_stamp_duty,land_betterment_charge
@dataclass
class DetailedActionInputs:
 action:str;current_value_m:float;current_noi_m:float;site_area_sqm:float;current_gfa_sqm:float;approved_gfa_sqm:float;nla_efficiency:float;market_value_per_nla_sqm:float;construction_cost_per_gfa_sqm:float;professional_fee_rate:float=.12;contingency_rate:float=.08;interest_rate:float=.045;loan_to_cost:float=.6;construction_months:int=36;predevelopment_months:int=9;lease_up_months:int=18;tenant_relocation_m:float=0;demolition_m:float=0;marketing_rate:float=.02;sale_cost_rate:float=.025;approval_probability:float=.65;lbc_rate_per_sqm:float|None=None;residential_share:float=1;acquisition_date:date=date(2020,1,1);start_date:date=date(2026,9,24)
def s_curve(months):
 x=np.arange(1,months+1);weights=np.sin(np.pi*x/(months+1))**1.7;return weights/weights.sum()
def irr(cashflows):
 def f(r):return sum(v/(1+r)**i for i,v in enumerate(cashflows))
 try:return brentq(f,-.99,10)
 except:return None
def evaluate_detailed_action(x:DetailedActionInputs,discount_rate=.078):
 additional=max(0,x.approved_gfa_sqm-x.current_gfa_sqm);construction=additional*x.construction_cost_per_gfa_sqm/1e6;fees=construction*x.professional_fee_rate;contingency=construction*x.contingency_rate;lbc=land_betterment_charge(additional,x.lbc_rate_per_sqm);lbc_m=(lbc['total_sgd']/1e6) if lbc.get('total_sgd') is not None else 0;total_development=construction+fees+contingency+x.tenant_relocation_m+x.demolition_m+lbc_m;months=x.predevelopment_months+x.construction_months+x.lease_up_months+12;cash=np.zeros(months+1);cash[0]-=x.current_value_m if x.action=='Acquire' else 0;bsd=buyer_stamp_duty(x.current_value_m*1e6,x.residential_share)['total_sgd']/1e6 if x.action=='Acquire' else 0;cash[0]-=bsd;cash[x.predevelopment_months:x.predevelopment_months+x.construction_months]-=total_development*s_curve(x.construction_months);debt_balance=0;interest_cost=0
 for month in range(1,months+1):
  draw=max(0,-cash[month])*x.loan_to_cost;debt_balance+=draw;interest=debt_balance*x.interest_rate/12;cash[month]-=interest;interest_cost+=interest
 operation_start=x.predevelopment_months+x.construction_months;stabilised_noi=x.approved_gfa_sqm*x.nla_efficiency*x.market_value_per_nla_sqm*.045/1e6
 for month in range(operation_start+1,months+1):
  progress=min(1,(month-operation_start)/max(1,x.lease_up_months));cash[month]+=stabilised_noi/12*progress
 terminal_nla=x.approved_gfa_sqm*x.nla_efficiency;gross_value=terminal_nla*x.market_value_per_nla_sqm/1e6;net_sale=gross_value*(1-x.marketing_rate-x.sale_cost_rate);cash[-1]+=net_sale-debt_balance;ssd=seller_stamp_duty(net_sale*1e6,x.acquisition_date,date(x.start_date.year+math.ceil(months/12),x.start_date.month,1),x.residential_share)['total_sgd']/1e6;cash[-1]-=ssd;expected_cash=cash.copy();expected_cash[1:]*=x.approval_probability;failure_cost=total_development*(1-x.approval_probability)*.35;expected_cash[min(x.predevelopment_months,len(expected_cash)-1)]-=failure_cost;monthly_rate=(1+discount_rate)**(1/12)-1;npv=sum(v/(1+monthly_rate)**i for i,v in enumerate(expected_cash));monthly_irr=irr(expected_cash.tolist());return {'action':x.action,'monthly_cashflows_m':np.round(expected_cash,4).tolist(),'npv_m':round(float(npv),3),'irr_annual':(1+monthly_irr)**12-1 if monthly_irr is not None else None,'additional_gfa_sqm':additional,'construction_m':round(construction,3),'professional_fees_m':round(fees,3),'contingency_m':round(contingency,3),'lbc':lbc,'buyer_stamp_duty_m':round(bsd,3),'seller_stamp_duty_m':round(ssd,3),'financing_interest_m':round(interest_cost,3),'tenant_relocation_m':x.tenant_relocation_m,'demolition_m':x.demolition_m,'gross_terminal_value_m':round(gross_value,3),'net_sale_proceeds_m':round(net_sale,3),'debt_repayment_m':round(debt_balance,3),'approval_probability':x.approval_probability,'failure_cost_m':round(failure_cost,3),'months':months,'verification_required':lbc['status']!='calculated'}
