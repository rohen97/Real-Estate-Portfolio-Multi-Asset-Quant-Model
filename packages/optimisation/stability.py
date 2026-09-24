from __future__ import annotations
from collections import Counter,defaultdict
import copy,numpy as np
from packages.optimisation.multiperiod import optimise_multi_period
def analyse_stability(asset_actions:list[dict],runs=40,seed=20260924,**optimizer_kwargs):
 rng=np.random.default_rng(seed);baseline=optimise_multi_period(asset_actions,**optimizer_kwargs);base={x['asset_id']:x['action'] for x in baseline.get('selections',[])};frequencies=defaultdict(Counter);objectives=[]
 for _ in range(runs):
  perturbed=copy.deepcopy(asset_actions)
  for asset in perturbed:
   for action in asset['actions']:
    action['expected_npv_m']*=float(rng.normal(1,.06));action['cvar_95_m']*=float(max(.7,rng.normal(1,.08)));action['capex_m']*=float(max(.75,rng.normal(1,.08)))
  result=optimise_multi_period(perturbed,**optimizer_kwargs);objectives.append(result.get('portfolio_expected_npv_m'))
  for x in result.get('selections',[]):frequencies[x['asset_id']][x['action']]+=1
 rows=[]
 for aid,counts in frequencies.items():
  total=sum(counts.values());robust,count=counts.most_common(1)[0];rows.append({'asset_id':aid,'baseline_action':base.get(aid),'robust_action':robust,'stability_score':round(count/total,4),'action_frequencies':{k:round(v/total,4) for k,v in counts.items()},'fragile':count/total<.7})
 return {'runs':runs,'assets':rows,'fragile_assets':sum(x['fragile'] for x in rows),'objective_mean_m':float(np.nanmean([x for x in objectives if x is not None])) if objectives else None,'objective_p10_m':float(np.nanquantile([x for x in objectives if x is not None],.1)) if objectives else None,'method':'Monte Carlo assumption perturbation around multi-period optimiser; simulation measures stability and does not replace optimisation'}
