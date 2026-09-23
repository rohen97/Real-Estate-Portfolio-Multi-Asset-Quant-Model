from __future__ import annotations
from pathlib import Path
from typing import TypedDict,Literal
import json
from langgraph.graph import StateGraph,START,END
from packages.orchestration.engine import run_asset,run_portfolio
from packages.optimisation.engine import optimise_portfolio
ROOT=Path(__file__).resolve().parents[2]
class AssetDecisionState(TypedDict,total=False):
 asset_id:str;asset:dict;evidence:dict;zoning:dict;model_result:dict;review_required:bool;review_status:str;errors:list[str]
class PortfolioDecisionState(TypedDict,total=False):
 assets:list[dict];model_results:list[dict];optimisation:dict;audit:dict;errors:list[str]
def _portfolio_rows():
 path=ROOT/'data/processed/portfolio.json';path=path if path.exists() else ROOT/'data/examples/demo_portfolio.json';return json.loads(path.read_text())
def load_asset(state:AssetDecisionState):
 rows=_portfolio_rows();asset=next((x for x in rows if x['asset_id']==state['asset_id']),None);return {'asset':asset,'errors':[] if asset else ['Asset not found']}
def validate_evidence(state:AssetDecisionState):
 asset=state.get('asset');return {'evidence':{'source_rows':asset.get('source_rows',[]) if asset else [],'observed_inputs':bool(asset and asset.get('observed_inputs')),'catalogue_only':bool(asset and asset.get('synthetic_financials',True))}}
def resolve_zoning(state:AssetDecisionState):
 asset=state.get('asset') or {};z=asset.get('ura_zoning',{});return {'zoning':{'matches':z.get('matches',[]),'match_method':z.get('match_method'),'spatial_review_required':z.get('spatial_review_required',True),'current_plan':z.get('current_statutory_plan','Master Plan 2025')}}
def evaluate_economics(state:AssetDecisionState):
 asset=state.get('asset');result=run_asset(asset) if asset else {};return {'model_result':result,'review_required':bool(result.get('verification_required',True))}
def review_route(state:AssetDecisionState)->Literal['review','complete']:
 return 'review' if state.get('review_required',True) else 'complete'
def human_review(state:AssetDecisionState):return {'review_status':'pending_human_review'}
def complete_asset(state:AssetDecisionState):return {'review_status':'model_complete'}
def create_asset_graph():
 graph=StateGraph(AssetDecisionState);graph.add_node('load_asset',load_asset);graph.add_node('validate_evidence',validate_evidence);graph.add_node('resolve_mp2025_zoning',resolve_zoning);graph.add_node('evaluate_economics',evaluate_economics);graph.add_node('human_review_gate',human_review);graph.add_node('complete',complete_asset);graph.add_edge(START,'load_asset');graph.add_edge('load_asset','validate_evidence');graph.add_edge('validate_evidence','resolve_mp2025_zoning');graph.add_edge('resolve_mp2025_zoning','evaluate_economics');graph.add_conditional_edges('evaluate_economics',review_route,{'review':'human_review_gate','complete':'complete'});graph.add_edge('human_review_gate',END);graph.add_edge('complete',END);return graph.compile()
def load_portfolio(state:PortfolioDecisionState):return {'assets':_portfolio_rows(),'errors':[]}
def evaluate_portfolio(state:PortfolioDecisionState):return {'model_results':run_portfolio(state['assets'])}
def optimise_actions(state:PortfolioDecisionState):
 rows=[x for x in state['model_results'] if x.get('country')=='Singapore' and x.get('actions')];actions=[{'asset_id':x['asset_id'],'name':x['name'],'base_noi_m':x.get('economics',{}).get('current_noi_m',0),'actions':x['actions']} for x in rows];return {'optimisation':optimise_portfolio(actions)}
def audit_portfolio(state:PortfolioDecisionState):
 results=state.get('model_results',[]);return {'audit':{'assets':len(results),'observed_assets':sum(x.get('model_status')=='observed_run' for x in results),'proxy_assets':sum(x.get('model_status')=='provisional_proxy_run' for x in results),'review_required':sum(x.get('verification_required',False) for x in results),'model_version':'economic-model-v2-selection-0.2'}}
def create_portfolio_graph():
 graph=StateGraph(PortfolioDecisionState);graph.add_node('load_portfolio',load_portfolio);graph.add_node('evaluate_asset_twins',evaluate_portfolio);graph.add_node('multi_period_optimisation',optimise_actions);graph.add_node('audit_and_governance',audit_portfolio);graph.add_edge(START,'load_portfolio');graph.add_edge('load_portfolio','evaluate_asset_twins');graph.add_edge('evaluate_asset_twins','multi_period_optimisation');graph.add_edge('multi_period_optimisation','audit_and_governance');graph.add_edge('audit_and_governance',END);return graph.compile()
