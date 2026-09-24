from __future__ import annotations
import numpy as np
class ConformalIntervalCalibrator:
 def fit(self,actual,p10,p90,target_coverage=.8):
  actual=np.asarray(actual,float);p10=np.asarray(p10,float);p90=np.asarray(p90,float);miss=np.maximum(p10-actual,actual-p90);self.adjustment=float(np.quantile(miss,target_coverage));self.target_coverage=target_coverage;return self
 def transform(self,p10,p50,p90):return {'p10':float(p10-self.adjustment),'p50':float(p50),'p90':float(p90+self.adjustment)}
 def coverage(self,actual,p10,p90):
  actual=np.asarray(actual,float);return float(np.mean((actual>=np.asarray(p10))&(actual<=np.asarray(p90))))
