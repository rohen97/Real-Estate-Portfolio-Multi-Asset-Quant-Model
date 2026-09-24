from __future__ import annotations
import math,numpy as np
def bearing(dx,dy):return (math.degrees(math.atan2(dx,dy))+360)%360
def viewshed(viewpoint_height_m,surrounding_buildings:list[dict],bins=360,view_premium_share=.05,current_value_m=0):
 horizon=np.full(bins,-90.,dtype=float);contributors=[]
 for building in surrounding_buildings:
  distance=max(1,float(building['distance_m']));height=float(building.get('height_m') or 0);width=max(1,float(building.get('width_m') or 20));angle=math.degrees(math.atan2(height-viewpoint_height_m,distance));az=float(building.get('bearing_deg') if building.get('bearing_deg') is not None else bearing(float(building.get('dx_m',0)),float(building.get('dy_m',distance))));half=math.degrees(math.atan2(width/2,distance));start=int((az-half)%360);end=int((az+half)%360);indices=list(range(start,end+1)) if start<=end else list(range(start,bins))+list(range(0,end+1))
  for idx in indices:horizon[idx]=max(horizon[idx],angle)
  contributors.append({'id':building.get('id'),'distance_m':distance,'height_m':height,'bearing_deg':az,'obstruction_angle_deg':round(angle,3),'angular_width_deg':round(half*2,3)})
 blocked=float(np.mean(horizon>0));severe=float(np.mean(horizon>10));open_sky=float(np.mean(horizon<=0));loss=current_value_m*view_premium_share*(.6*blocked+.4*severe);return {'blocked_azimuth_share':round(blocked,4),'severely_blocked_share':round(severe,4),'open_sky_share':round(open_sky,4),'view_premium_loss_m':round(loss,3),'horizon_angles_deg':np.round(horizon,2).tolist(),'contributors':sorted(contributors,key=lambda x:x['obstruction_angle_deg'],reverse=True),'method':'Angular screening viewshed; replace assumed envelopes with surveyed building geometry for decision use'}
