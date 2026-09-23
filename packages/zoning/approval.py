from __future__ import annotations
import numpy as np
STAGES=[('Pre-application',.94,2.5),('Planning submission',.86,5),('Technical clearances',.82,6),('Committee/public review',.88,4),('Conditions discharge',.93,4),('Building permission',.97,3)]
def approval_path(overrides:dict|None=None,seed=20260922,draws=5000):
 overrides=overrides or {};rng=np.random.default_rng(seed);paths=np.ones(draws,dtype=bool);months=np.zeros(draws);stages=[];cumulative=1
 for name,p,mean_months in STAGES:
  p=float(overrides.get(name,p));duration=np.maximum(.25,rng.lognormal(np.log(mean_months)-.15,.45,draws));passed=rng.random(draws)<p;active=paths.copy();months[active]+=duration[active];paths&=passed;cumulative*=p;stages.append({'stage':name,'conditional_probability':p,'cumulative_probability':round(cumulative,4),'expected_months':mean_months})
 return {'stages':stages,'overall_probability':round(float(paths.mean()),4),'p50_months':round(float(np.quantile(months,.5)),1),'p90_months':round(float(np.quantile(months,.9)),1),'redesign_probability':round(1-float(paths.mean()),4),'seed':seed}
