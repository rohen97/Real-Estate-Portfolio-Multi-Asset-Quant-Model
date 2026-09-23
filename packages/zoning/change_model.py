from __future__ import annotations
from pathlib import Path
import joblib
import numpy as np,pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import roc_auc_score,average_precision_score,brier_score_loss
from sklearn.model_selection import GroupKFold
from packages.zoning.features import NUMERIC_FEATURES,CATEGORICAL_FEATURES
from packages.zoning.challenger import encode_frame
def train_change_model(rows:list[dict],output_dir:Path,synthetic=False):
 frame=pd.DataFrame(rows);x,medians=encode_frame(frame);y=frame['changed'].astype(int);groups=frame.get('planning_area',pd.Series(['Unknown']*len(frame)));folds=[]
 for train,test in GroupKFold(min(5,len(set(groups)))).split(x,y,groups):
  m=LGBMClassifier(n_estimators=220,learning_rate=.035,num_leaves=15,max_depth=5,class_weight='balanced',verbosity=-1,random_state=20260923).fit(x.iloc[train],y.iloc[train]);p=m.predict_proba(x.iloc[test])[:,1];folds.append({'roc_auc':float(roc_auc_score(y.iloc[test],p)) if len(set(y.iloc[test]))>1 else None,'average_precision':float(average_precision_score(y.iloc[test],p)),'brier':float(brier_score_loss(y.iloc[test],p)),'observations':len(test)})
 model=LGBMClassifier(n_estimators=300,learning_rate=.03,num_leaves=15,max_depth=5,class_weight='balanced',verbosity=-1,random_state=20260923).fit(x,y);artifact={'model':model,'columns':list(x.columns),'medians':medians,'folds':folds,'synthetic_training':synthetic,'target':'probability of zoning/GPR change'};output_dir.mkdir(parents=True,exist_ok=True);joblib.dump(artifact,output_dir/'rezoning_probability.joblib');return {'status':'trained','observations':len(frame),'positive_rate':float(y.mean()),'spatial_folds':folds,'artifact':str(output_dir/'rezoning_probability.joblib'),'synthetic_training':synthetic}
def predict_change(model_path:Path,record:dict):
 artifact=joblib.load(model_path);x,_=encode_frame(pd.DataFrame([record]),artifact['columns'],artifact['medians']);p=float(artifact['model'].predict_proba(x)[0,1]);return {'change_probability':round(p,5),'signal':'High' if p>=.65 else 'Medium' if p>=.35 else 'Low','synthetic_training':artifact['synthetic_training'],'target':artifact['target']}
