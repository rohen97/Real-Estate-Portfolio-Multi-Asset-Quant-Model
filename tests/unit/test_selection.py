from packages.selection.engine import evaluate_selection,enbloc_option,lease_decay,transformation_exposure
ACTIONS=[{'action':'Hold','expected_npv_m':5,'probability_of_loss':.15},{'action':'Retrofit','expected_npv_m':12,'probability_of_loss':.2},{'action':'Repurpose','expected_npv_m':18,'probability_of_loss':.3},{'action':'Redevelop','expected_npv_m':22,'probability_of_loss':.4},{'action':'Sell','expected_npv_m':7,'probability_of_loss':.05}]
CAPACITY={'statutory_gfa_sqm':30000,'unused_economic_gfa_sqm':12000,'residual_value_m':30}
def test_proxy_assets_are_not_given_transaction_signal():
 asset={'segments':['Residential'],'synthetic_financials':True,'tenure_hint':{'type':'Freehold'},'latitude':1.3,'longitude':103.8,'ura_zoning':{'spatial_review_required':False}};r=evaluate_selection(asset,CAPACITY,ACTIONS,{'view_block_probability':.2,'supply_pressure_index':.3},{'indicators':{'price_qoq':.01}},120,5.8,transformation_zones=[]);assert r['signal']=='Data Required / Monitor';assert len(r['action_comparison'])==5
def test_false_synthetic_flag_does_not_bypass_evidence_gate():
 asset={'segments':['Residential'],'synthetic_financials':False,'tenure_hint':{'type':'Freehold'},'latitude':1.3,'longitude':103.8,'ura_zoning':{'spatial_review_required':False}};r=evaluate_selection(asset,CAPACITY,ACTIONS,{'view_block_probability':.05,'supply_pressure_index':.05},{'indicators':{'price_qoq':.015}},120,7,.078,5,[]);assert r['signal']=='Data Required / Monitor';assert r['annual_expected_alpha'] is None;assert r['expected_total_return'] is None;assert r['readiness']['missing']
def test_lease_decay_and_enbloc_are_explicit():
 asset={'segments':['Residential'],'tenure_hint':{'type':'99-year leasehold','remaining_years':35}};assert lease_decay(asset,100)['penalty_m']>0;assert enbloc_option(asset,CAPACITY,100)['collective_sale_applicable']
def test_transformation_is_time_discounted():
 asset={'latitude':1.334,'longitude':103.743};zones=[{'name':'JLD','latitude':1.334,'longitude':103.743,'influence_radius_km':5,'target_year':2035,'delivery_probability':.8,'potential_value_uplift':.09,'source':'test'}];r=transformation_exposure(asset,zones,100);assert 0<r['value_m']<9
