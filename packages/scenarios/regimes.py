from __future__ import annotations
from pathlib import Path
import joblib,numpy as np,pandas as pd
from sklearn.mixture import GaussianMixture
def fit_regimes(records:list[dict],columns:list[str],output:Path,n_regimes=3):
 frame=pd.DataFrame(records)[columns].dropna()
 if len(frame)<40:return {'status':'blocked','observations':len(frame),'reason':'At least 40 complete time observations required'}
 model=GaussianMixture(n_components=n_regimes,covariance_type='full',n_init=20,random_state=20260924).fit(frame);labels=model.predict(frame);rent_index=columns.index('rent_growth') if 'rent_growth' in columns else 0;order=np.argsort(model.means_[:,rent_index]);names={int(order[0]):'Contraction',int(order[-1]):'Expansion'}
 for idx in range(n_regimes):names.setdefault(idx,'Stable / transition')
 transition=np.ones((n_regimes,n_regimes))
 for a,b in zip(labels,labels[1:]):transition[a,b]+=1
 transition/=transition.sum(axis=1,keepdims=True);artifact={'model':model,'columns':columns,'regime_names':names,'transition':transition,'observations':len(frame)};output.parent.mkdir(parents=True,exist_ok=True);joblib.dump(artifact,output);return {'status':'trained','observations':len(frame),'regimes':[{'id':i,'name':names[i],'mean':model.means_[i].tolist(),'covariance':model.covariances_[i].tolist(),'weight':float(model.weights_[i])} for i in range(n_regimes)],'transition':transition.tolist(),'artifact':str(output)}
def predict_regime(model_path:Path,features:dict):
 artifact=joblib.load(model_path);x=np.array([[features[c] for c in artifact['columns']]],float);prob=artifact['model'].predict_proba(x)[0];idx=int(np.argmax(prob));return {'regime':artifact['regime_names'][idx],'probability':float(prob[idx]),'probabilities':{artifact['regime_names'][i]:float(p) for i,p in enumerate(prob)},'transition_from_regime':artifact['transition'][idx].tolist()}
