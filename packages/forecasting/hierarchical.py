from __future__ import annotations
from collections import defaultdict
import numpy as np
class HierarchicalGrowthModel:
 def __init__(self,prior_strength=8):self.prior_strength=prior_strength;self.global_mean=0;self.segment_means={};self.counts={}
 def fit(self,records):
  values=[];groups=defaultdict(list)
  for r in records:
   g=float(r['growth']);values.append(g);groups[r.get('segment','Unknown')].append(g)
  self.global_mean=float(np.mean(values)) if values else 0
  for segment,x in groups.items():
   n=len(x);self.counts[segment]=n;self.segment_means[segment]=(n*np.mean(x)+self.prior_strength*self.global_mean)/(n+self.prior_strength)
  return self
 def predict(self,segment):return float(self.segment_means.get(segment,self.global_mean))
 def summary(self):return {'global_mean':self.global_mean,'segment_means':self.segment_means,'counts':self.counts,'method':'Empirical Bayes partial pooling'}
