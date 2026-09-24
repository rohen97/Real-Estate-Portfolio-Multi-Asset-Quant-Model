from __future__ import annotations
from pathlib import Path
import joblib,numpy as np,pandas as pd
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import GroupKFold
FEATURES=['prior_growth','vacancy','cap_rate','interest_rate','supply_pipeline','mrt_accessibility','employment_density','transformation_exposure','neighbor_mean_growth','neighbor_high_density_share']
def train_spatial_market(rows:list[dict],output:Path,target='rent_growth'):
 frame=pd.DataFrame(rows).dropna(subset=[target]);x=frame[FEATURES].apply(pd.to_numeric,errors='coerce').fillna(frame[FEATURES].median(numeric_only=True)).fillna(0);y=frame[target].astype(float);groups=frame['planning_area'].fillna('Unknown');fold=[]
 for train,test in GroupKFold(min(5,len(set(groups)))).split(x,y,groups):
  model=LGBMRegressor(n_estimators=250,learning_rate=.035,num_leaves=15,max_depth=5,reg_lambda=2,verbosity=-1,random_state=20260924).fit(x.iloc[train],y.iloc[train]);pred=model.predict(x.iloc[test]);fold.append({'mae':float(mean_absolute_error(y.iloc[test],pred)),'observations':len(test),'test_areas':sorted(set(groups.iloc[test]))})
 model=LGBMRegressor(n_estimators=300,learning_rate=.03,num_leaves=15,max_depth=5,reg_lambda=2,verbosity=-1,random_state=20260924).fit(x,y);artifact={'model':model,'features':FEATURES,'target':target,'folds':fold};output.parent.mkdir(parents=True,exist_ok=True);joblib.dump(artifact,output);return {'status':'trained','observations':len(frame),'mean_spatial_mae':float(np.mean([z['mae'] for z in fold])),'folds':fold,'artifact':str(output)}
