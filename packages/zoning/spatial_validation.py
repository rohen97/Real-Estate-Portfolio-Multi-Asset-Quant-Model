from __future__ import annotations
import numpy as np
from sklearn.metrics import balanced_accuracy_score,f1_score,log_loss,precision_recall_fscore_support,confusion_matrix
from sklearn.model_selection import StratifiedGroupKFold
def multiclass_brier(y_true,probabilities,classes):
 index={c:i for i,c in enumerate(classes)};onehot=np.zeros_like(probabilities)
 for row,label in enumerate(y_true):onehot[row,index[label]]=1
 return float(np.mean(np.sum((probabilities-onehot)**2,axis=1)))
def spatial_cross_validate(model_factory,x,y,groups,n_splits=5):
 unique=np.unique(groups);splits=min(n_splits,len(unique));
 if splits<2:return {'status':'blocked','reason':'At least two spatial groups required'}
 fold_metrics=[];all_true=[];all_pred=[]
 for fold,(train,test) in enumerate(StratifiedGroupKFold(splits,shuffle=True,random_state=20260923).split(x,y,groups),1):
  model=model_factory();model.fit(x.iloc[train],y.iloc[train]);pred=model.predict(x.iloc[test]);prob=model.predict_proba(x.iloc[test]);classes=list(model.classes_);p,r,f,_=precision_recall_fscore_support(y.iloc[test],pred,average='macro',zero_division=0);metrics={'fold':fold,'test_groups':sorted(set(groups.iloc[test])),'balanced_accuracy':float(balanced_accuracy_score(y.iloc[test],pred)),'macro_precision':float(p),'macro_recall':float(r),'macro_f1':float(f),'log_loss':float(log_loss(y.iloc[test],prob,labels=classes)),'brier':multiclass_brier(y.iloc[test].tolist(),prob,classes),'observations':len(test)};fold_metrics.append(metrics);all_true.extend(y.iloc[test]);all_pred.extend(pred)
 return {'status':'validated','folds':fold_metrics,'mean_macro_f1':float(np.mean([x['macro_f1'] for x in fold_metrics])),'mean_balanced_accuracy':float(np.mean([x['balanced_accuracy'] for x in fold_metrics])),'confusion_matrix':confusion_matrix(all_true,all_pred).tolist(),'labels':sorted(set(y)),'validation':'grouped spatial cross-validation'}
