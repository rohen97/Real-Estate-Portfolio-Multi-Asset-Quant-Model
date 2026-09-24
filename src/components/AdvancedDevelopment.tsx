import { useEffect, useState } from 'react';
import { AdvancedDevelopmentCharts } from './Visuals';
const money=(value:any)=>typeof value==='number'?'S$'+value.toFixed(1)+'m':'—';
export default function AdvancedDevelopment({assetId,api}:{assetId:string;api:string}){
 const[data,setData]=useState<any>();const[error,setError]=useState('');
 useEffect(()=>{setError('');fetch(api+'/assets/'+assetId+'/advanced-analysis').then(response=>{if(!response.ok)throw new Error('Advanced analysis unavailable');return response.json()}).then(setData).catch(reason=>setError(String(reason)))},[assetId,api]);
 if(error)return <div className="warning">{error}</div>;
 if(!data)return <div className="chart-loading">Running advanced development analysis…</div>;
 return <><div className="metrics"><div className="metric"><span>Preferred envelope</span><strong>{data.development_envelope?.preferred?.towers||'—'} towers</strong><small>{data.development_envelope?.preferred?.storeys||'—'} storeys</small></div><div className="metric"><span>Envelope net area</span><strong>{data.development_envelope?.preferred?.net_area_sqm?.toLocaleString()||'—'} sqm</strong></div><div className="metric"><span>View premium loss</span><strong>{money(data.viewshed?.view_premium_loss_m)}</strong><small>{((data.viewshed?.blocked_azimuth_share||0)*100).toFixed(1)}% azimuth blocked</small></div><div className="metric"><span>En-bloc probability</span><strong>{((data.enbloc?.success_probability||0)*100).toFixed(1)}%</strong><small>{money(data.enbloc?.maximum_land_value_m)} max land value</small></div></div><div className="warning">Screening-level outputs. LBC rate, surveyed geometry, architecture, daylight, fire access, parking and owner consent require professional verification.</div><AdvancedDevelopmentCharts data={data}/></>
}
