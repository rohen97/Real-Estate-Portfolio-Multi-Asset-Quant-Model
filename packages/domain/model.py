from __future__ import annotations
import hashlib,json,math
import numpy as np
MASTER_SEED=20260922
ACTIONS=['Hold','Retrofit','Repurpose','Redevelop','Sell']
NAMES=['Harbour Junction','Northbank Offices','Orchard Arcade','Tuas Logistics Hub','Pine Residences','Bayfront Suites','Civic Exchange','Riverside Mall','Garden Court','Eastern Distribution Park']
TYPES=['Mixed use','Office','Retail','Logistics','Residential','Hospitality','Office','Retail','Residential','Logistics']
LEGACY={'FE-001':(82.9167,84.375),'FE-002':(66.6667,77.5),'FE-003':(42.9167,44.375),'FE-004':(68.3333,66.25),'FE-005':(54.1667,43.125)}
def assets(seed=MASTER_SEED):
 r=np.random.default_rng(seed);out=[]
 for i in range(10):
  aid=f'FE-{i+1:03d}';land=float(r.integers(7000,30000));cur=round(float(r.uniform(1.2,3.2)),2);legal=round(cur+float(r.uniform(.3,1.8)),2);att=round(cur+(legal-cur)*float(r.uniform(.55,.9)),2);value=round(float(r.uniform(55,230)),1);occ=round(float(r.uniform(.72,.98)),3);noi=round(value*float(r.uniform(.038,.06)),2);lc,lf=LEGACY.get(aid,(round(float(r.uniform(45,90)),4),round(float(r.uniform(45,90)),4)))
  out.append(dict(asset_id=aid,name=NAMES[i],property_type=TYPES[i],location=f'Illustrative district {i+1}',current_value_m=value,appraisal_value_m=round(value*r.uniform(.95,1.08),1),land_area_sqm=land,current_gfa_sqm=round(land*cur),current_plot_ratio=cur,legal_plot_ratio=legal,attainable_plot_ratio=att,occupancy=occ,noi_m=noi,market_rent_growth=round(float(r.uniform(.01,.045)),4),cap_rate=round(float(r.uniform(.04,.058)),4),approval_probability=round(float(r.uniform(.42,.82)),3),approval_months=int(r.integers(14,38)),data_quality=round(float(r.uniform(.67,.96)),3),legacy_scores=dict(published_current=lc+2.5,published_future=lf-1.25,corrected_current=lc,corrected_future=lf),synthetic=True))
 out[0].update(current_value_m=120.,appraisal_value_m=121.5,current_plot_ratio=2.1,legal_plot_ratio=3.5,attainable_plot_ratio=3.16,occupancy=.84,noi_m=5.8,approval_probability=.62,approval_months=24,cap_rate=.0475,market_rent_growth=.028,data_quality=.88);out[0]['current_gfa_sqm']=round(out[0]['land_area_sqm']*2.1);return out
def evidence(aid):
 a=next(x for x in assets() if x['asset_id']==aid);x=[dict(field='appraisal_value_m',value=a['appraisal_value_m'],source='Synthetic valuation report',observed_at='2026-08-31',quality=.91,status='verified'),dict(field='legal_plot_ratio',value=a['legal_plot_ratio'],source='Illustrative planning register',observed_at='2026-09-01',quality=.84,status='review' if aid=='FE-001' else 'verified')]
 if aid=='FE-001':x.append(dict(field='legal_plot_ratio',value=3.2,source='Synthetic consultant memo',observed_at='2026-09-10',quality=.72,status='conflict'))
 return x
def zoning(a):
 legal=a['land_area_sqm']*a['legal_plot_ratio'];att=a['land_area_sqm']*a['attainable_plot_ratio'];unused=max(0,att-a['current_gfa_sqm']);return dict(legal_gfa_sqm=round(legal),attainable_gfa_sqm=round(att),unused_capacity_sqm=round(unused),option_value_m=round(unused*1850*a['approval_probability']/1e6,1))
def valuations(a):
 d=a['noi_m']*(1+a['market_rent_growth'])/a['cap_rate'];c=(a['appraisal_value_m']*.65+a['current_value_m']*.35)*(1+(a['occupancy']-.85)*.1);m=.52*d+.28*c+.2*a['current_value_m'];r=.5*d+.3*c+.2*m;return dict(dcf_m=round(d,1),comparable_m=round(c,1),ml_challenger_m=round(m,1),reconciled_m=round(r,1),agreement=round(1-np.std([d,c,m])/max(r,1),3))
def scenario(a,p):
 rng=np.random.default_rng(int(p.get('seed',MASTER_SEED))+int(a['asset_id'][-3:]));n=int(p.get('draws',2500));corr=np.array([[1,.45,-.35],[.45,1,-.25],[-.35,-.25,1]]);s=rng.multivariate_normal(np.zeros(3),corr,n);t=rng.standard_t(5,(n,3))/math.sqrt(5/3);q=.65*s+.35*t;ret=.094+q[:,0]*.035-q[:,1]*.018-q[:,2]*.022;loss=-ret;var=float(np.quantile(loss,.95));return dict(expected_return=round(float(ret.mean()),4),required_return=.078,expected_alpha=round(float(ret.mean()-.078-.006-(1-a['data_quality'])*.035),4),var_95=round(var,4),cvar_95=round(float(loss[loss>=var].mean()),4),p10=round(float(np.quantile(ret,.1)),4),p50=round(float(np.quantile(ret,.5)),4),p90=round(float(np.quantile(ret,.9)),4),draws=n,seed=p.get('seed',MASTER_SEED),distribution='Correlated Student-t blend')
def action_cases(a,p):
 base={'Hold':4.2,'Retrofit':10.8,'Repurpose':17.6,'Redevelop':21.3,'Sell':7.1} if a['asset_id']=='FE-001' else {k:round(a['noi_m']*f+zoning(a)['option_value_m']*g,1) for k,f,g in [('Hold',.35,0),('Retrofit',.7,.1),('Repurpose',.8,.45),('Redevelop',.55,.75),('Sell',.5,0)]};stress={'Hold':-4.8,'Retrofit':1.9,'Repurpose':2.8,'Redevelop':-6.4,'Sell':4.3} if a['asset_id']=='FE-001' else {k:round(v-5-(i*2),1) for i,(k,v) in enumerate(base.items())};cap={'Hold':1.5,'Retrofit':13.,'Repurpose':31.,'Redevelop':56.,'Sell':-110.};months={'Hold':3,'Retrofit':15,'Repurpose':26,'Redevelop':42,'Sell':9};adj=(p.get('approval_probability',.62)-.62)*28-(p.get('cap_rate',.0475)-.0475)*600
 return [dict(action=k,expected_npv_m=round(v+(adj if k in ['Repurpose','Redevelop'] else 0),1),stress_npv_m=stress[k],capital_m=cap[k],execution_months=months[k],downside_m=round(v-stress[k],1)) for k,v in base.items()]
def recommendation(a,p):
 c=max((x for x in action_cases(a,p) if x['stress_npv_m']>-8),key=lambda x:x['expected_npv_m']-.25*x['downside_m']);labels={'Hold':'Retain','Retrofit':'Retrofit','Repurpose':'Repurpose','Redevelop':'Repurpose','Sell':'Release'};return {**c,'management_label':labels[c['action']],'explanation':f"{c['action']} creates the strongest risk-adjusted incremental value after capacity, approval risk, capital and downside."}
def optimise(req):
 rem=float(req.get('capital_budget_m',120));sel=[];total=0
 for a in assets():
  choices=sorted(action_cases(a,{}),key=lambda x:x['expected_npv_m']-.35*x['downside_m'],reverse=True);c=next((x for x in choices if x['capital_m']<=rem or x['capital_m']<0),choices[-1]);rem-=max(c['capital_m'],0);total+=c['expected_npv_m'];sel.append({'asset_id':a['asset_id'],'asset_name':a['name'],**c,'reason':'Selected within capital and downside constraints.'})
 return dict(selections=sel,portfolio_expected_npv_m=round(total,1),capital_used_m=round(float(req.get('capital_budget_m',120))-rem,1),capital_remaining_m=round(rem,1),feasible=rem>=0,method='Discrete constrained selection; Monte Carlo supplies risk inputs and is not the optimiser.')
def key(x):return hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()[:16]
