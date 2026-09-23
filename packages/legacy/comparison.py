from __future__ import annotations
from packages.legacy.scorecard import score
def compare(legacy_inputs:list[dict],model_results:list[dict],outcomes:list[dict]|None=None):
 model={x['asset_id']:x for x in model_results};outcome={x['asset_id']:x for x in (outcomes or [])};rows=[]
 for item in legacy_inputs:
  corrected=score(item['financial'],item['operational'],item['market'],item['sustainability']);new=model.get(item['asset_id'],{});label=new.get('recommendation',{}).get('management_label');actual=outcome.get(item['asset_id'],{}).get('action')
  rows.append({**item,'corrected_current':corrected['current_performance'],'corrected_future':corrected['future_potential'],'published_quadrant':score(item['financial'],item['operational'],item['market'],item['sustainability'])['quadrant'] if item.get('published_current') is None else quadrant_from_published(item['published_current'],item['published_future']),'corrected_quadrant':corrected['quadrant'],'economic_action':new.get('recommendation',{}).get('action'),'economic_management_label':label,'expected_npv_m':new.get('recommendation',{}).get('expected_npv_m'),'legacy_vs_economic_agreement':corrected['quadrant']==label,'realised_action':actual,'realised_action_agreement':actual in (new.get('recommendation',{}).get('action'),label)})
 return rows
def quadrant_from_published(current,future,threshold=70):
 if current>=threshold and future>=threshold:return 'Retain'
 if current>=threshold:return 'Retrofit'
 if future>=threshold:return 'Repurpose'
 return 'Release'
