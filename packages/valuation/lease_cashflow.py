from __future__ import annotations
from datetime import date,datetime
import math
def as_date(value):
 if isinstance(value,date):return value
 return datetime.fromisoformat(str(value)).date()
def lease_cashflow(leases:list[dict],as_of=date(2026,9,23),horizon_years=10,rent_growth=.025,opex_ratio=.3,renewal_probability=.65,downtime_months=4,discount_rate=.078,exit_cap_rate=.05):
 years=[as_of.year+i for i in range(1,horizon_years+1)];gross={y:0. for y in years};occupied_area={y:0. for y in years};total_area=sum(float(x.get('Area sqm') or 0) for x in leases)
 for lease in leases:
  area=float(lease.get('Area sqm') or 0);passing=float(lease.get('Passing Rent SGD pa') or 0)/1e6;market=float(lease.get('Market Rent SGD pa') or passing*1e6)/1e6;expiry=as_date(lease['Lease Expiry'])
  credit={'A':.995,'BBB':.985,'BB':.955}.get(str(lease.get('Tenant Credit Grade')), .97);collection=float(lease.get('Collection %') or credit)
  for idx,y in enumerate(years,1):
   if date(y,12,31)<=expiry:rent=passing*(1+rent_growth)**idx;occ=1
   else:
    market_y=market*(1+rent_growth)**idx;availability=max(0,1-downtime_months/12);rent=renewal_probability*passing*(1+rent_growth)**idx+(1-renewal_probability)*market_y*availability;occ=renewal_probability+(1-renewal_probability)*availability
   gross[y]+=rent*collection;occupied_area[y]+=area*occ
 noi={y:gross[y]*(1-opex_ratio) for y in years};terminal=noi[years[-1]]*(1+rent_growth)/exit_cap_rate;cashflows=[noi[y] for y in years];cashflows[-1]+=terminal;pv=sum(v/(1+discount_rate)**i for i,v in enumerate(cashflows,1));return {'years':years,'gross_rent_m':[round(gross[y],3) for y in years],'noi_m':[round(noi[y],3) for y in years],'occupancy':[round(occupied_area[y]/total_area,4) if total_area else None for y in years],'terminal_value_m':round(terminal,3),'present_value_m':round(pv,3),'assumptions':{'rent_growth':rent_growth,'opex_ratio':opex_ratio,'renewal_probability':renewal_probability,'downtime_months':downtime_months,'discount_rate':discount_rate,'exit_cap_rate':exit_cap_rate}}
