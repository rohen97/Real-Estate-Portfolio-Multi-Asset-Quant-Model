from __future__ import annotations
VERSION='legacy-scorecard-2025.11-frozen'
WEIGHTS={'financial':.35,'operational':.25,'market':.25,'sustainability':.15}
THRESHOLD=70.0
def current_performance(financial,operational):return (financial*WEIGHTS['financial']+operational*WEIGHTS['operational'])/(WEIGHTS['financial']+WEIGHTS['operational'])
def future_potential(market,sustainability):return (market*WEIGHTS['market']+sustainability*WEIGHTS['sustainability'])/(WEIGHTS['market']+WEIGHTS['sustainability'])
def quadrant(current,future,threshold=THRESHOLD):
 if current>=threshold and future>=threshold:return 'Retain'
 if current>=threshold and future<threshold:return 'Retrofit'
 if current<threshold and future>=threshold:return 'Repurpose'
 return 'Release'
def score(financial,operational,market,sustainability,threshold=THRESHOLD):
 current=current_performance(financial,operational);future=future_potential(market,sustainability);return {'version':VERSION,'financial':financial,'operational':operational,'market':market,'sustainability':sustainability,'current_performance':round(current,4),'future_potential':round(future,4),'threshold':threshold,'quadrant':quadrant(current,future,threshold)}
def normalize(value,low,high,higher_is_better=True):
 if high<=low:raise ValueError('Benchmark high must exceed low')
 result=max(0,min(100,(value-low)/(high-low)*100));return result if higher_is_better else 100-result
