from __future__ import annotations
import httpx
BASE='https://www.onemap.gov.sg/api/public/popapi'
SUPPORTED_YEARS={1990,1998,2000,2003,2008,2013,2014,2015,2016,2017,2018,2019}
def _headers(token:str):return {'Authorization':token,'Accept':'application/json'}
def planning_area_names(token:str,year=2019):
 if year not in SUPPORTED_YEARS:raise ValueError(f'OneMap Planning Area API supports {sorted(SUPPORTED_YEARS)}; it is not a Master Plan 2025 zoning source.')
 with httpx.Client(timeout=45,headers=_headers(token)) as client:return client.get(BASE+'/getPlanningareaNames',params={'year':year}).raise_for_status().json()
def planning_area_polygons(token:str,year=2019):
 if year not in SUPPORTED_YEARS:raise ValueError(f'OneMap Planning Area API supports {sorted(SUPPORTED_YEARS)}; it is not a Master Plan 2025 zoning source.')
 with httpx.Client(timeout=90,headers=_headers(token)) as client:return client.get(BASE+'/getPlanningarea',params={'year':year}).raise_for_status().json()
