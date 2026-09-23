from __future__ import annotations
from pathlib import Path
import json
import joblib
import numpy as np
from lightgbm import LGBMRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error,mean_squared_error
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
FEATURES=['prior_noi','occupancy','cap_rate','maintenance_capex','prior_valuation','year_index']
def samples(financials:list[dict]):
 by_asset={}
 for row in financials:by_asset.setdefault(row['Asset ID'],[]).append(row)
 x=[];y=[];years=[];asset_ids=[]
 for aid,rows in by_asset.items():
  rows=sorted(rows,key=lambda r:int(r['Fiscal Year']))
  for prev,cur in zip(rows,rows[1:]):
   try:x.append([float(prev['NOI SGD m']),float(prev.get('Occupancy %') or 0),float(prev.get('Cap Rate %') or 0),float(prev.get('Maintenance Capex SGD m') or 0),float(prev.get('Valuation SGD m') or 0),int(cur['Fiscal Year'])-2020]);y.append(float(cur['NOI SGD m']));years.append(int(cur['Fiscal Year']));asset_ids.append(aid)
   except:pass
 return np.asarray(x,float),np.asarray(y,float),np.asarray(years,int),asset_ids
def train_ensemble(financials:list[dict],output_dir:Path,synthetic=False):
 x,y,years,asset_ids=samples(financials)
 if len(y)<30:return {'status':'blocked','observations':len(y),'reason':'At least 30 consecutive observations required'}
 holdout=years==years.max();train=~holdout
 ridge=make_pipeline(StandardScaler(),Ridge(alpha=1)).fit(x[train],y[train]);gbm=LGBMRegressor(n_estimators=180,learning_rate=.035,max_depth=3,num_leaves=15,min_child_samples=8,reg_lambda=2,verbosity=-1,random_state=20260923).fit(x[train],y[train])
 quantiles={q:LGBMRegressor(objective='quantile',alpha=q,n_estimators=160,learning_rate=.04,max_depth=3,num_leaves=15,min_child_samples=8,verbosity=-1,random_state=20260923+int(q*100)).fit(x[train],y[train]) for q in (.1,.5,.9)}
 pred=(ridge.predict(x[holdout])+gbm.predict(x[holdout]))/2;metrics={'mae':float(mean_absolute_error(y[holdout],pred)),'rmse':float(mean_squared_error(y[holdout],pred)**.5),'holdout_year':int(years.max()),'train_rows':int(train.sum()),'test_rows':int(holdout.sum())}
 output_dir.mkdir(parents=True,exist_ok=True);joblib.dump({'ridge':ridge,'gbm':gbm,'quantiles':quantiles,'features':FEATURES,'metrics':metrics,'synthetic_training':synthetic},output_dir/'noi_ensemble.joblib');return {'status':'trained','metrics':metrics,'features':FEATURES,'synthetic_training':synthetic,'artifact':str(output_dir/'noi_ensemble.joblib')}
def predict(model_path:Path,features:dict):
 model=joblib.load(model_path);x=np.array([[float(features[k]) for k in model['features']]]);point=float((model['ridge'].predict(x)[0]+model['gbm'].predict(x)[0])/2);qs={f'p{int(q*100)}':float(m.predict(x)[0]) for q,m in model['quantiles'].items()};ordered=sorted([qs['p10'],qs['p50'],qs['p90']]);return {'point':point,'p10':ordered[0],'p50':ordered[1],'p90':ordered[2],'model_metrics':model['metrics'],'synthetic_training':model['synthetic_training']}
