import json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];rng=np.random.default_rng(20260924);transition=np.array([[.72,.24,.04],[.12,.76,.12],[.04,.28,.68]]);means=np.array([[-.018,.13,.063,.06,.075,38],[.022,.075,.048,.038,.035,24],[.055,.035,.038,.025,.02,16]]);std=np.array([[.025,.03,.009,.012,.025,10],[.018,.02,.006,.008,.015,7],[.025,.015,.006,.006,.012,5]]);state=1;rows=[]
for quarter in range(100):
 state=int(rng.choice(3,p=transition[state]));values=rng.normal(means[state],std[state]);rows.append({'period':f'{2002+quarter//4} Q{quarter%4+1}','regime':['Contraction','Stable','Expansion'][state],'rent_growth':float(values[0]),'vacancy':float(np.clip(values[1],.01,.3)),'cap_rate':float(np.clip(values[2],.025,.1)),'interest_rate':float(np.clip(values[3],.005,.15)),'cost_inflation':float(np.clip(values[4],-.03,.15)),'approval_delay':float(np.clip(values[5],3,72))})
out=ROOT/'data/examples/demo_market_history.json';out.write_text(json.dumps(rows,indent=2),encoding='utf-8');spatial=[]
for area in range(12):
 for t in range(30):
  prior=float(rng.normal(.025,.02));supply=max(0,float(rng.normal(.08,.04)));access=float(rng.uniform(0,1));employment=float(rng.normal(15000,5000));transform=float(rng.uniform(0,.08));neighbor=float(rng.normal(prior,.01));growth=.45*prior-.2*supply+.025*access+.000001*employment+.25*transform+.2*neighbor+rng.normal(0,.012);spatial.append({'planning_area':f'DEMO AREA {area+1}','prior_growth':prior,'vacancy':float(rng.uniform(.03,.15)),'cap_rate':float(rng.uniform(.035,.065)),'interest_rate':float(rng.uniform(.02,.07)),'supply_pipeline':supply,'mrt_accessibility':access,'employment_density':employment,'transformation_exposure':transform,'neighbor_mean_growth':neighbor,'neighbor_high_density_share':float(rng.uniform(0,1)),'rent_growth':growth})
(ROOT/'data/examples/demo_spatial_market_training.json').write_text(json.dumps(spatial,indent=2),encoding='utf-8');print(json.dumps({'market_periods':len(rows),'spatial_rows':len(spatial),'synthetic':True},indent=2))
