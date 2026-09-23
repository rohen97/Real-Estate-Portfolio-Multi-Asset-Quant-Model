from packages.domain.model import assets,zoning,valuations,scenario,action_cases,recommendation,key
def test_deterministic():assert assets(42)==assets(42)
def test_zoning():
 z=zoning(assets()[0]);assert z['legal_gfa_sqm']>z['attainable_gfa_sqm'] and z['unused_capacity_sqm']>0
def test_valuations():assert set(valuations(assets()[0]))>={'dcf_m','comparable_m','ml_challenger_m','reconciled_m'}
def test_scenario_reproducibility():assert scenario(assets()[0],{'seed':7})==scenario(assets()[0],{'seed':7})
def test_cvar():
 r=scenario(assets()[0],{});assert r['cvar_95']>=r['var_95']
def test_action_reconciliation():assert {x['action']:x for x in action_cases(assets()[0],{})}['Redevelop']['expected_npv_m']==21.3
def test_cache():assert key({'a':1})!=key({'a':2})
