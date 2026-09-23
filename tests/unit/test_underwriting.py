from packages.data.underwriting_import import validate_asset_row
from packages.orchestration.engine import run_asset
def valid_row():
 return {'Asset ID':'FEO-TEST','Ownership Entity':'Far East Test','Ownership %':1.0,'Title Lot / MK-TS':'TS01-001','Tenure':'Freehold','Site Area sqm':10000,'Existing GFA sqm':22000,'NLA sqm':18000,'Occupancy %':.92,'Current Valuation SGD m':150,'Valuation Date':'2026-06-30','NOI SGD m':7.5,'Passing Rent SGD m pa':10,'Operating Expenses SGD m pa':2.5,'Current Use':'Office','Data Owner':'Asset Management','Evidence Source':'Signed valuation and management accounts','Evidence Date':'2026-06-30','Verification Status':'Verified'}
def test_valid_underwriting_row():
 mapped,errors,warnings=validate_asset_row(valid_row());assert not errors;assert mapped['site_area_sqm']==10000
def test_invalid_relationships_are_rejected():
 row=valid_row();row['NLA sqm']=25000;row['Occupancy %']=1.2;_,errors,_=validate_asset_row(row);codes={x['code'] for x in errors};assert 'relationship' in codes and 'range' in codes
def test_observed_inputs_replace_proxy():
 mapped,errors,_=validate_asset_row(valid_row());assert not errors;mapped['zoning_verified']=True
 asset={'asset_id':'FEO-TEST','name':'Test Asset','country':'Singapore','segments':['Commercial'],'ura_zoning':{'matches':[{'lu_desc':'COMMERCIAL','gpr':4.2}],'spatial_review_required':False},'observed_inputs':mapped}
 result=run_asset(asset,7);assert result['model_status']=='observed_run';assert result['economics']['current_value_m']==150;assert result['economics']['source_quality']=='verified company underwriting input';assert result['gpr_source']=='MP2025'
