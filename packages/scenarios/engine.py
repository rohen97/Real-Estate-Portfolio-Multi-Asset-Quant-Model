from __future__ import annotations
import numpy as np
FACTORS=['rent_growth','vacancy','cap_rate','interest_rate','cost_inflation','approval_delay']
CORRELATION=np.array([[1,-.45,-.55,-.2,.25,-.15],[-.45,1,.35,.2,.1,.25],[-.55,.35,1,.45,.15,.25],[-.2,.2,.45,1,.35,.3],[.25,.1,.15,.35,1,.35],[-.15,.25,.25,.3,.35,1]])
def factor_scenarios(draws=5000,seed=20260922):
 rng=np.random.default_rng(seed);normal=rng.multivariate_normal(np.zeros(6),CORRELATION,draws);tails=rng.standard_t(5,(draws,6))/np.sqrt(5/3);z=.7*normal+.3*tails
 levels=np.column_stack([.025+.025*z[:,0],np.clip(.07+.035*z[:,1],.01,.3),np.clip(.0475+.009*z[:,2],.025,.1),np.clip(.04+.012*z[:,3],.01,.12),np.clip(.035+.025*z[:,4],-.02,.15),np.clip(24+10*z[:,5],3,72)])
 return levels
def simulate_actions(action_values:list[dict],draws=5000,seed=20260922):
 f=factor_scenarios(draws,seed);results=[]
 for i,a in enumerate(action_values):
  rng=np.random.default_rng(seed+100+i);base=a['incremental_npv_m'];development=1 if a['action'] in ('Repurpose','Redevelop') else .35 if a['action']=='Retrofit' else .1
  shock=(f[:,0]-.025)*180*(.5+development)+(f[:,1]-.07)*-90+(f[:,2]-.0475)*-420*(.4+development)+(f[:,3]-.04)*-80*development+(f[:,4]-.035)*-110*development+(f[:,5]-24)*-.12*development+rng.normal(0,2+development*3,draws)
  values=base+shock;loss=-values;var=np.quantile(loss,.95);results.append({**a,'expected_npv_m':round(float(values.mean()),2),'p10_npv_m':round(float(np.quantile(values,.1)),2),'p50_npv_m':round(float(np.quantile(values,.5)),2),'p90_npv_m':round(float(np.quantile(values,.9)),2),'probability_of_loss':round(float((values<0).mean()),4),'var_95_m':round(float(var),2),'cvar_95_m':round(float(loss[loss>=var].mean()),2),'scenario_seed':seed,'draws':draws})
 return results

def scenario_covariance():
 return {'factors':FACTORS,'correlation':CORRELATION.tolist(),'description':'Correlation assumptions for rent growth, vacancy, cap rate, interest rate, cost inflation and approval delay'}
def action_scenario_samples(action_values:list[dict],draws=600,seed=20260922):
 f=factor_scenarios(draws,seed);out={}
 for i,a in enumerate(action_values):
  rng=np.random.default_rng(seed+100+i);base=float(a.get('incremental_npv_m',a.get('expected_npv_m',0)));development=1 if a['action'] in ('Repurpose','Redevelop') else .35 if a['action']=='Retrofit' else .1;shock=(f[:,0]-.025)*180*(.5+development)+(f[:,1]-.07)*-90+(f[:,2]-.0475)*-420*(.4+development)+(f[:,3]-.04)*-80*development+(f[:,4]-.035)*-110*development+(f[:,5]-24)*-.12*development+rng.normal(0,2+development*3,draws);out[a['action']]=np.round(base+shock,3).tolist()
 return {'seed':seed,'draws':draws,'samples':out}
