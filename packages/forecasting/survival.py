from __future__ import annotations
from pathlib import Path
import joblib
import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
class ApprovalSurvivalModel:
 def fit(self,rows):
  features=[];targets=[];durations={}
  for r in rows:
   if not r.get('Stage') or not r.get('Outcome'):continue
   outcome=str(r['Outcome']).lower();targets.append(int(outcome in ('approved','granted','completed')));features.append({'stage':r['Stage'],'redesign':str(r.get('Redesign Required','')).lower()=='yes','conditions':float(r.get('Conditions Count') or 0)})
   try:
    from datetime import datetime
    months=(datetime.fromisoformat(str(r['Decision Date']))-datetime.fromisoformat(str(r['Submission Date']))).days/30.4375;durations.setdefault(r['Stage'],[]).append(months)
   except:pass
  if len(targets)<25:return {'status':'blocked','observations':len(targets)}
  self.vectorizer=DictVectorizer(sparse=False);x=self.vectorizer.fit_transform(features);self.model=LogisticRegression(max_iter=2000,class_weight='balanced',random_state=20260923).fit(x,targets);self.durations={k:{'mean':float(np.mean(v)),'p90':float(np.quantile(v,.9)),'count':len(v)} for k,v in durations.items()};return {'status':'trained','observations':len(targets),'stages':self.durations}
 def predict_stage(self,stage,redesign=False,conditions=0):
  x=self.vectorizer.transform([{'stage':stage,'redesign':redesign,'conditions':conditions}]);return float(self.model.predict_proba(x)[0,1])
 def save(self,path:Path):path.parent.mkdir(parents=True,exist_ok=True);joblib.dump(self,path)
