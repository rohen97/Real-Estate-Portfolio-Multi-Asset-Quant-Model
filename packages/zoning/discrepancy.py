from __future__ import annotations
from packages.zoning.taxonomy import core_class,gpr_band
def compare_zoning(legal_land_use,legal_gpr,prediction,observed_lulc=None,current_use=None):
 legal_core=core_class(legal_land_use);pred_core=prediction.get('core',{}).get('prediction');pred_gpr=prediction.get('gpr_band',{}).get('prediction');reasons=[];severity=0
 if prediction.get('core',{}).get('abstain'):reasons.append('Core zoning model abstained');severity=max(severity,1)
 if pred_core and pred_core!=legal_core:reasons.append(f'Legal core {legal_core} differs from challenger {pred_core}');severity=max(severity,2)
 if legal_gpr is not None and pred_gpr and pred_gpr!=gpr_band(legal_gpr):reasons.append(f'Legal GPR band {gpr_band(legal_gpr)} differs from challenger {pred_gpr}');severity=max(severity,1)
 compat={'building':{'Residential','Commercial','Mixed Use','Industrial','Hotel','Institutional'},'road':{'Transport'},'paved':{'Transport','Commercial','Industrial','Special'},'vegetation':{'Open Space','Residential'},'water':{'Open Space','Transport'},'construction':{'Residential','Commercial','Mixed Use','Industrial','Hotel','Institutional'},'vacant_land':set()};
 if observed_lulc and observed_lulc!='Unknown' and compat.get(observed_lulc,set()) and legal_core not in compat[observed_lulc]:reasons.append('Observed physical land cover differs from legal zoning');severity=max(severity,2)
 if current_use and current_use.lower() not in (legal_core.lower(),(legal_land_use or '').lower()):reasons.append('Current asset use requires compatibility review');severity=max(severity,2)
 return {'legal_land_use':legal_land_use,'legal_core':legal_core,'legal_gpr':legal_gpr,'predicted_core':pred_core,'predicted_subtype':prediction.get('subtype',{}).get('prediction'),'predicted_gpr_band':pred_gpr,'observed_lulc':observed_lulc,'current_use':current_use,'severity':severity,'status':'review' if severity>=2 else 'monitor' if severity else 'consistent','reasons':reasons,'prediction_confidence':prediction.get('core',{}).get('confidence'),'prediction_entropy':prediction.get('core',{}).get('entropy')}
def feature_collection(rows):
 features=[]
 for row in rows:
  if row.get('longitude') is None or row.get('latitude') is None:continue
  features.append({'type':'Feature','geometry':{'type':'Point','coordinates':[row['longitude'],row['latitude']]},'properties':{k:v for k,v in row.items() if k not in ('longitude','latitude')}})
 return {'type':'FeatureCollection','features':features}
