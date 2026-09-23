from pathlib import Path
import json,pytest
from packages.data.portfolio import load_source_workbook,merge_assets
from packages.zoning.engine import ZoningAssumptions,calculate_capacity
from packages.zoning.approval import approval_path
from packages.zoning.ura import lookup_zone
from packages.valuation.engine import AssetEconomics,dcf,value_actions
from packages.scenarios.engine import simulate_actions
from packages.optimisation.engine import optimise_portfolio
ROOT=Path(__file__).resolve().parents[2]
WORKBOOK=Path(r'C:\Users\RohenVeeraKumaran\Downloads\Far_East_Asset_List.xlsx')
@pytest.mark.skipif(not WORKBOOK.exists(),reason="Private portfolio workbook not available in public CI")
def test_real_portfolio_ingestion():
 assets=merge_assets(load_source_workbook(WORKBOOK));assert len(assets)==260;assert sum(x['country']=='Singapore' for x in assets)==177
def test_capacity_ladder_and_binding_constraints():
 r=calculate_capacity(ZoningAssumptions(10000,18000,3.5));assert r.statutory_gfa_sqm>=r.physical_gfa_sqm>=r.de_facto_gfa_sqm;assert r.p10_gfa_sqm<r.p90_gfa_sqm;assert r.binding_constraints
def test_approval_path_is_reproducible():assert approval_path(seed=7)==approval_path(seed=7)
def test_action_cashflows_and_risk():
 e=AssetEconomics(120,5.8);c=calculate_capacity(ZoningAssumptions(9000,18900,3.5)).__dict__;actions=value_actions(e,c);risk=simulate_actions(actions,seed=7);assert len(risk)==5;assert all(x['cvar_95_m']>=x['var_95_m'] for x in risk)
def test_milp_selects_one_action_per_asset():
 e=AssetEconomics(120,5.8);c=calculate_capacity(ZoningAssumptions(9000,18900,3.5)).__dict__;actions=simulate_actions(value_actions(e,c),draws=500,seed=7);items=[{'asset_id':f'A{i}','name':f'Asset {i}','actions':actions} for i in range(3)];r=optimise_portfolio(items,300,3,.67,.3,20);assert r['feasible'];assert len(r['selections'])==3
@pytest.mark.skipif(not (ROOT/'data/processed/ura_mp2025.sqlite').exists(),reason="Full URA index not included in public repository")
def test_ura_index_and_current_plan_gate():
 db=ROOT/'data/processed/ura_mp2025.sqlite';result=lookup_zone(db,1.340,103.817);assert result['current_plan_verification_required'];assert result['current_statutory_plan']=='Master Plan 2025'

def test_public_market_snapshot():
 import json
 path=ROOT/'data/public/singapore_market_snapshot.json';path=path if path.exists() else ROOT/'data/examples/demo_market_snapshot.json';snapshot=json.loads(path.read_text());assert snapshot['land_use_allocation_hectares']['Total']==73800;assert snapshot['market_indicators']['industrial']['price_qoq']>0

@pytest.mark.skipif(not (ROOT/'data/processed/ura_mp2025.sqlite').exists(),reason="Full URA index not included in public repository")
def test_title_boundary_lookup():
 from packages.zoning.ura import lookup_title_boundary
 polygon={'type':'Polygon','coordinates':[[[103.8169,1.3399],[103.8171,1.3399],[103.8171,1.3401],[103.8169,1.3401],[103.8169,1.3399]]]}
 result=lookup_title_boundary(ROOT/'data/processed/ura_mp2025.sqlite',polygon);assert result['match_method']=='title_boundary_overlap';assert 'boundary_overlaps' in result
