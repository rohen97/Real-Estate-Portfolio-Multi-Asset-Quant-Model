from __future__ import annotations
from collections import defaultdict
from pathlib import Path
import json
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
def load_rows(path:Path):return json.loads(path.read_text()) if path.exists() else []
def calibrate_noi(financials:list[dict]):
 by_asset=defaultdict(list)
 for row in financials:
  try:
   if row.get('Asset ID') and row.get('Fiscal Year') and row.get('NOI SGD m') not in (None,''):by_asset[row['Asset ID']].append(row)
  except:pass
 samples=[]
 for aid,rows in by_asset.items():
  rows=sorted(rows,key=lambda x:int(x['Fiscal Year']))
  for prev,cur in zip(rows,rows[1:]):
   try:samples.append([float(prev['NOI SGD m']),float(prev.get('Occupancy %') or 0),float(prev.get('Cap Rate %') or 0),float(prev.get('Maintenance Capex SGD m') or 0),float(cur['NOI SGD m'])])
   except:pass
 if len(samples)<30:return {'status':'blocked','reason':'At least 30 consecutive asset-year observations are required','observations':len(samples)}
 data=np.array(samples);order=np.arange(len(data));split=max(20,int(len(data)*.8));train,test=data[order[:split]],data[order[split:]];model=Ridge(alpha=1).fit(train[:,:4],train[:,4]);pred=model.predict(test[:,:4]);return {'status':'calibrated','observations':len(samples),'test_observations':len(test),'mae_m':round(float(mean_absolute_error(test[:,4],pred)),4),'intercept':float(model.intercept_),'coefficients':dict(zip(['prior_noi','occupancy','cap_rate','maintenance_capex'],map(float,model.coef_))),'validation':'chronological holdout'}
def calibrate_approval(rows:list[dict]):
 usable=[r for r in rows if r.get('Stage') and r.get('Outcome')]
 if len(usable)<25:return {'status':'blocked','reason':'At least 25 verified planning-stage outcomes are required','observations':len(usable)}
 stages=defaultdict(lambda:{'approved':0,'total':0,'durations':[]})
 for r in usable:
  s=stages[r['Stage']];s['total']+=1;s['approved']+=int(str(r['Outcome']).lower() in ('approved','granted','completed'))
  try:
   from datetime import datetime
   a=datetime.fromisoformat(str(r['Submission Date']));b=datetime.fromisoformat(str(r['Decision Date']));s['durations'].append((b-a).days/30.4375)
  except:pass
 return {'status':'calibrated','stages':{k:{'posterior_probability':round((v['approved']+1)/(v['total']+2),4),'observations':v['total'],'mean_months':round(float(np.mean(v['durations'])),2) if v['durations'] else None} for k,v in stages.items()},'method':'Beta(1,1) posterior with observed stage durations'}
def calibrate_execution(capex:list[dict]):
 completed=[r for r in capex if str(r.get('Project Status','')).lower() in ('completed','closed')]
 if len(completed)<20:return {'status':'blocked','reason':'At least 20 completed projects are required','observations':len(completed)}
 overruns=[]
 for r in completed:
  try:overruns.append((float(r.get('Spent SGD m') or 0)+float(r.get('Committed SGD m') or 0))/float(r['Budget SGD m'])-1)
  except:pass
 return {'status':'calibrated','observations':len(overruns),'mean_cost_overrun':round(float(np.mean(overruns)),4),'p90_cost_overrun':round(float(np.quantile(overruns,.9)),4)} if overruns else {'status':'blocked','reason':'Completed projects lack valid budgets and spend'}
def run_calibration(data_dir:Path,output:Path):
 report={'noi_forecast':calibrate_noi(load_rows(data_dir/'financials.json')),'approval':calibrate_approval(load_rows(data_dir/'planning_history.json')),'execution':calibrate_execution(load_rows(data_dir/'capex.json'))};output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2),encoding='utf-8');return report
