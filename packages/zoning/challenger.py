from __future__ import annotations
from pathlib import Path
import json,math
import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import log_loss
from packages.zoning.features import NUMERIC_FEATURES,CATEGORICAL_FEATURES
from packages.zoning.spatial_validation import spatial_cross_validate,multiclass_brier
from scipy.optimize import minimize_scalar
from packages.zoning.taxonomy import core_class,gpr_band
def encode_frame(frame,fit_columns=None,medians=None):
 x=frame.copy();medians=medians or {}
 for c in NUMERIC_FEATURES:
  if c not in x:x[c]=np.nan
  x[c]=pd.to_numeric(x[c],errors='coerce');medians[c]=float(x[c].median()) if c not in medians and x[c].notna().any() else medians.get(c,0.);x[c]=x[c].fillna(medians[c])
 for c in CATEGORICAL_FEATURES:
  if c not in x:x[c]='Unknown'
  x[c]=x[c].fillna('Unknown').astype(str)
 x=pd.get_dummies(x[NUMERIC_FEATURES+CATEGORICAL_FEATURES],columns=CATEGORICAL_FEATURES,dtype=float)
 if fit_columns is not None:x=x.reindex(columns=fit_columns,fill_value=0.)
 return x,medians
def factory():return LGBMClassifier(n_estimators=250,learning_rate=.035,num_leaves=23,max_depth=6,min_child_samples=12,class_weight='balanced',reg_lambda=2,verbosity=-1,random_state=20260923)
def entropy(prob):
 p=np.clip(np.asarray(prob,float),1e-12,1);return float(-(p*np.log(p)).sum()/math.log(len(p))) if len(p)>1 else 0
def apply_temperature(probabilities,temperature):
 logits=np.log(np.clip(np.asarray(probabilities,float),1e-12,1))/max(float(temperature),1e-3);logits-=logits.max(axis=1,keepdims=True);scaled=np.exp(logits);return scaled/scaled.sum(axis=1,keepdims=True)
def fit_calibrated(x,y,groups):
 unique=sorted(set(groups));cal_groups=set(unique[-max(2,int(len(unique)*.2)):]);cal_mask=groups.isin(cal_groups);train_mask=~cal_mask;model=factory().fit(x[train_mask],y[train_mask]);raw=model.predict_proba(x[cal_mask]);classes=list(model.classes_);target=y[cal_mask].tolist()
 def objective(t):return log_loss(target,apply_temperature(raw,t),labels=classes)
 temperature=float(minimize_scalar(objective,bounds=(.35,3.5),method='bounded').x) if cal_mask.sum() else 1.;scaled=apply_temperature(raw,temperature) if cal_mask.sum() else raw;metrics={'temperature':temperature,'calibration_groups':sorted(cal_groups),'observations':int(cal_mask.sum()),'log_loss_before':float(log_loss(target,raw,labels=classes)) if cal_mask.sum() else None,'log_loss_after':float(log_loss(target,scaled,labels=classes)) if cal_mask.sum() else None,'brier_after':multiclass_brier(target,scaled,classes) if cal_mask.sum() else None};return model,temperature,metrics
def train(rows:list[dict],output_dir:Path,synthetic=False):
 frame=pd.DataFrame(rows);frame['core_label']=frame['legal_land_use'].map(core_class);frame['subtype_label']=frame['legal_land_use'].fillna('Unknown');frame['gpr_label']=frame.get('legal_gpr',pd.Series([None]*len(frame))).map(gpr_band);x,medians=encode_frame(frame);groups=frame.get('planning_area',pd.Series(['Unknown']*len(frame))).fillna('Unknown');validation=spatial_cross_validate(factory,x,frame['core_label'],groups,5);core,core_temp,core_cal=fit_calibrated(x,frame['core_label'],groups);subtype,sub_temp,sub_cal=fit_calibrated(x,frame['subtype_label'],groups);gpr,gpr_temp,gpr_cal=fit_calibrated(x,frame['gpr_label'],groups);output_dir.mkdir(parents=True,exist_ok=True);artifact={'core':core,'subtype':subtype,'gpr_band':gpr,'temperatures':{'core':core_temp,'subtype':sub_temp,'gpr_band':gpr_temp},'calibration':{'core':core_cal,'subtype':sub_cal,'gpr_band':gpr_cal},'columns':list(x.columns),'medians':medians,'validation':validation,'synthetic_training':synthetic,'taxonomy_version':'sg-zoning-taxonomy-0.2','abstain_confidence':.5,'abstain_entropy':.82};joblib.dump(artifact,output_dir/'zoning_challenger.joblib');importance=sorted([{'feature':f,'importance':float(v)} for f,v in zip(x.columns,core.feature_importances_)],key=lambda z:z['importance'],reverse=True);(output_dir/'zoning_feature_importance.json').write_text(json.dumps(importance,indent=2),encoding='utf-8');return {'status':'trained','observations':len(frame),'classes':list(core.classes_),'validation':validation,'top_features':importance[:20],'artifact':str(output_dir/'zoning_challenger.joblib'),'synthetic_training':synthetic}
def predict(model_path:Path,record:dict):
 artifact=joblib.load(model_path);x,_=encode_frame(pd.DataFrame([record]),artifact['columns'],artifact['medians']);result={}
 for key in ('core','subtype','gpr_band'):
  model=artifact[key];prob=apply_temperature(model.predict_proba(x),artifact.get('temperatures',{}).get(key,1.))[0];order=np.argsort(prob)[::-1];top=[{'label':str(model.classes_[i]),'probability':round(float(prob[i]),5)} for i in order[:3]];result[key]={'prediction':top[0]['label'],'confidence':top[0]['probability'],'entropy':round(entropy(prob),5),'top3':top,'abstain':top[0]['probability']<artifact['abstain_confidence'] or entropy(prob)>artifact['abstain_entropy']}
 result['model_validation']=artifact['validation'];result['probability_calibration']=artifact.get('calibration');result['synthetic_training']=artifact['synthetic_training'];return result
