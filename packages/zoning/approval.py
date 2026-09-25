from __future__ import annotations
import numpy as np
STAGES=[('Pre-application',.94,2.5),('Planning submission',.86,5),('Technical clearances',.82,6),('Committee/public review',.88,4),('Conditions discharge',.93,4),('Building permission',.97,3)]
def approval_path(overrides:dict|None=None,seed=20260922,draws=5000):
 if not isinstance(draws,int) or draws<1:raise ValueError('draws must be a positive integer')
 overrides=overrides or {}
 if any(not np.isfinite(float(p)) or not 0<=float(p)<=1 for p in overrides.values()):raise ValueError('Stage probabilities must lie between zero and one')
 rng=np.random.default_rng(seed);paths=np.ones(draws,dtype=bool);months=np.zeros(draws);stages=[];cumulative=1
 for name,p,mean_months in STAGES:
  p=float(overrides.get(name,p));duration=np.maximum(.25,rng.lognormal(np.log(mean_months)-.5*.45**2,.45,draws));passed=rng.random(draws)<p;active=paths.copy();months[active]+=duration[active];paths&=passed;cumulative*=p;stages.append({'stage':name,'conditional_probability':p,'cumulative_probability':round(cumulative,4),'expected_months':mean_months})
 return {'stages':stages,'overall_probability':round(float(paths.mean()),4),'p50_months':round(float(np.quantile(months,.5)),1),'p90_months':round(float(np.quantile(months,.9)),1),'redesign_probability':round(1-float(paths.mean()),4),'failure_probability':round(1-float(paths.mean()),4),'seed':seed,'duration_basis':'time to success or stopping failure, not successful-completion duration','p50_success_months':round(float(np.quantile(months[paths],.5)),1) if paths.any() else None,'p90_success_months':round(float(np.quantile(months[paths],.9)),1) if paths.any() else None,'probability_source':'uncalibrated stage assumptions','redesign_probability_status':'legacy alias for failure; redesign itself is not estimated'}
