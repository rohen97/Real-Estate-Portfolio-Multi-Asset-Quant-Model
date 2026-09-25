"""Monthly lease collections with one expiry event and explicit valuation date."""
from __future__ import annotations
from calendar import monthrange
from datetime import date, datetime, timedelta
import math


def as_date(value):
 if isinstance(value,datetime):return value.date()
 if isinstance(value,date):return value
 return datetime.fromisoformat(str(value)).date()


def _month(value,number):
 year,month=divmod(value.year*12+value.month-1+number,12)
 return date(year,month+1,min(value.day,monthrange(year,month+1)[1]))


def _overlap(start,end,lower,upper):
 return max(0,(min(end,upper)-max(start,lower)).days)/(end-start).days


def lease_cashflow(leases:list[dict],as_of=None,horizon_years=10,rent_growth=.025,opex_ratio=.3,renewal_probability=.65,downtime_months=4,discount_rate=.078,exit_cap_rate=.05):
 as_of=as_date(as_of or date.today())
 if not isinstance(horizon_years,int) or not 1<=horizon_years<=100:raise ValueError('A positive integer horizon of at most100years is required')
 if not all(math.isfinite(v) for v in (rent_growth,opex_ratio,renewal_probability,downtime_months,discount_rate,exit_cap_rate)) or rent_growth<=-1 or discount_rate<=-1 or exit_cap_rate<=0 or not 0<=opex_ratio<=1 or not 0<=renewal_probability<=1 or downtime_months<0 or int(downtime_months)!=downtime_months:raise ValueError('Invalid lease cashflow assumptions')
 periods=[(_month(as_of,m),_month(as_of,m+1)) for m in range(horizon_years*12)]
 gross=[0.]*len(periods);occupied=[0.]*len(periods);total_area=0.;sources=[]
 for lease in leases:
  area=float(lease.get('Area sqm') or 0);passing=float(lease.get('Passing Rent SGD pa') or 0)/1e6
  market=float(lease['Market Rent SGD pa'])/1e6 if lease.get('Market Rent SGD pa') is not None else passing
  collection=float(lease['Collection %']) if lease.get('Collection %') is not None else {'A':.995,'BBB':.985,'BB':.955}.get(str(lease.get('Tenant Credit Grade')),.97)
  escalation=float(lease.get('Annual Escalation %') or 0)
  if not all(math.isfinite(v) for v in (area,passing,market,collection,escalation)) or min(area,passing,market)<0 or not 0<=collection<=1 or escalation<=-1:raise ValueError('Invalid lease area, rent, collection or escalation')
  start=as_date(lease['Lease Start']) if lease.get('Lease Start') else as_of
  expiry=as_date(lease['Lease Expiry'])+timedelta(days=1)
  if lease.get('Lease Start') and expiry<=start:raise ValueError('Lease expiry precedes lease start')
  relet=_month(expiry,int(downtime_months));total_area+=area
  sources.append('supplied_collection' if lease.get('Collection %') is not None else 'assumed_credit_collection')
  for m,(lower,upper) in enumerate(periods):
   original=_overlap(lower,upper,start,expiry)
   renewed=_overlap(lower,upper,expiry,date.max)
   relet_share=_overlap(lower,upper,relet,date.max)
   occupancy=original+renewal_probability*renewed+(1-renewal_probability)*relet_share
   passing_rate=passing*(1+escalation)**(m/12)
   market_rate=market*(1+rent_growth)**(m/12)
   gross[m]+=collection*(passing_rate*original+market_rate*(renewal_probability*renewed+(1-renewal_probability)*relet_share))/12
   occupied[m]+=area*occupancy
 monthly_noi=[value*(1-opex_ratio) for value in gross]
 annual_gross=[sum(gross[i:i+12]) for i in range(0,len(gross),12)]
 annual_noi=[sum(monthly_noi[i:i+12]) for i in range(0,len(gross),12)]
 annual_occupancy=[sum(occupied[i:i+12])/12/total_area if total_area else None for i in range(0,len(gross),12)]
 terminal=annual_noi[-1]*(1+rent_growth)/exit_cap_rate
 cashflows=list(monthly_noi);cashflows[-1]+=terminal
 pv=sum(value/(1+discount_rate)**((m+1)/12) for m,value in enumerate(cashflows))
 return {'as_of':as_of.isoformat(),'years':[end.year for _,end in periods[11::12]],'period_ends':[end.isoformat() for _,end in periods[11::12]],'gross_rent_m':[round(v,6) for v in annual_gross],'noi_m':[round(v,6) for v in annual_noi],'occupancy':[round(v,6) if v is not None else None for v in annual_occupancy],'monthly_gross_rent_m':gross,'monthly_noi_m':monthly_noi,'monthly_cashflows_m':cashflows,'terminal_value_m':round(terminal,6),'present_value_m':round(pv,6),'cashflow_basis':'monthly forward periods from as_of, paid at month-end; one expiry/renewal/reletting event per lease','assumptions':{'rent_growth':rent_growth,'contract_escalation':'zero unless Annual Escalation % supplied','renewal_rent':'market rent at renewal, with no renewal downtime','opex_ratio':opex_ratio,'renewal_probability':renewal_probability,'downtime_months':downtime_months,'downtime_frequency':'once at the supplied expiry, not every later year','discount_rate':discount_rate,'exit_cap_rate':exit_cap_rate,'collection_sources':sources},'warning':'Expected lease screen. Subsequent lease expiries, breaks, renewal incentives, re-letting costs, market vacancy and transaction costs require explicit schedules; not included.'}
