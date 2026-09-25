"""Angular geometric screen: missing geometry is not evidence of an open view."""
from __future__ import annotations
import math
import numpy as np


def bearing(dx,dy):
 return (math.degrees(math.atan2(dx,dy))+360)%360


def viewshed(viewpoint_height_m,surrounding_buildings:list[dict],bins=360,view_premium_share=.05,current_value_m=0):
 if not isinstance(bins,int) or bins<4 or bins>3600:raise ValueError('bins must be an integer from 4 to 3600')
 if not all(math.isfinite(v) for v in (viewpoint_height_m,view_premium_share,current_value_m)) or not 0<=view_premium_share<=1 or current_value_m<0:raise ValueError('Invalid viewshed parameters')
 horizon=np.full(bins,-90.,dtype=float);azimuths=np.arange(bins)*360/bins;contributors=[];missing=0
 for building in surrounding_buildings:
  try:
   distance=float(building['distance_m']);height=float(building['height_m']);width=float(building.get('width_m',20))
   if not all(math.isfinite(v) for v in (distance,height,width)) or distance<=0 or height<0 or width<=0:raise ValueError('Invalid building geometry')
   az=float(building['bearing_deg']) if building.get('bearing_deg') is not None else bearing(float(building.get('dx_m',0)),float(building.get('dy_m',distance)))
   if not math.isfinite(az):raise ValueError('Invalid bearing')
  except (KeyError,TypeError,ValueError):missing+=1;continue
  angle=math.degrees(math.atan2(height-viewpoint_height_m,distance));half=math.degrees(math.atan2(width/2,distance));angular_distance=np.abs((azimuths-az+180)%360-180);mask=angular_distance<=half
  horizon[mask]=np.maximum(horizon[mask],angle)
  contributors.append({'id':building.get('id'),'distance_m':distance,'height_m':height,'bearing_deg':az%360,'obstruction_angle_deg':round(angle,3),'angular_width_deg':round(half*2,3)})
 if not contributors:
  return {'status':'unavailable','blocked_azimuth_share':None,'severely_blocked_share':None,'open_sky_share':None,'view_premium_loss_m':None,'horizon_angles_deg':[],'contributors':[],'missing_buildings':missing,'method':'No usable surrounding-building geometry; an open view has not been established'}
 blocked=float(np.mean(horizon>0));severe=float(np.mean(horizon>10));loss=current_value_m*view_premium_share*(.6*blocked+.4*severe)
 return {'status':'partial_screening' if missing else 'screening_only','blocked_azimuth_share':round(blocked,4),'severely_blocked_share':round(severe,4),'open_sky_share':round(float(np.mean(horizon<=0)),4),'view_premium_loss_m':round(loss,3),'horizon_angles_deg':np.round(horizon,2).tolist(),'contributors':sorted(contributors,key=lambda x:x['obstruction_angle_deg'],reverse=True),'missing_buildings':missing,'method':'Angular screening of supplied geometry only; open-sky share is conditional on a complete building inventory'}
