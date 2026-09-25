import { useEffect, useState } from 'react';
import { AdvancedDevelopmentCharts } from './Visuals';
const money = (value: any) => typeof value === 'number' && Number.isFinite(value) ? `S$${value.toFixed(2)}m` : 'Unavailable';
const pct = (value: any) => typeof value === 'number' && Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : 'Unavailable';
export default function AdvancedDevelopment({ assetId, api }: { assetId: string; api: string }) {
  const [data, setData] = useState<any>(), [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController(); setData(undefined); setError('');
    fetch(api + '/assets/' + encodeURIComponent(assetId) + '/advanced-analysis', { signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error('Advanced analysis is unavailable for this asset.'); return response.json(); })
      .then(setData).catch(reason => { if (reason.name !== 'AbortError') setError(reason.message); });
    return () => controller.abort();
  }, [assetId, api]);
  if (error) return <div className="warning" role="alert">{error}</div>;
  if (!data) return <div className="chart-loading">Loading advanced development analysis…</div>;
  const envelope = data.development_envelope?.preferred, cash = data.redevelopment_cashflow || {}, view = data.viewshed || {}, enbloc = data.enbloc || {};
  const viewAvailable = view.status !== 'unavailable' && !!view.contributors?.length;
  return <><div className="metrics"><div className="metric"><span>Conceptual envelope</span><strong>{envelope ? `${envelope.towers} towers` : 'No feasible envelope'}</strong><small>{envelope ? `${envelope.storeys} storeys; ${envelope.net_area_sqm?.toLocaleString()} sqm net` : 'Review supplied geometry and planning controls'}</small></div><div className="metric"><span>Incremental redevelopment NPV</span><strong>{money(cash.incremental_npv_m ?? cash.npv_m)}</strong><small>{cash.npv_basis || 'Valuation basis unavailable'}</small></div><div className="metric"><span>View premium loss</span><strong>{viewAvailable ? money(view.view_premium_loss_m) : 'Unavailable'}</strong><small>{viewAvailable ? pct(view.blocked_azimuth_share) + ' modelled obstruction' : 'Surrounding geometry is missing'}</small></div><div className="metric"><span>Decision readiness</span><strong>{data.decision_ready && cash.decision_ready ? 'Evidence ready' : 'Incomplete inputs'}</strong><small>{cash.valuation_status || data.valuation_status || 'Verification required'}</small></div></div>
    <div className="warning">Conceptual geometry and cash flows are screening outputs. Missing LBC, title/tenure charges, surveyed geometry, approval and financing evidence can change the decision. {view.interpretation}</div>
    <section><h2>Valuation interpretation</h2><p>{cash.npv_basis}. Hold value is the counterfactual; project and equity NPVs use different cash flows and must not be added together.</p><p>Expected project NPV {money(cash.project_npv_m)}; Hold NPV {money(cash.hold_npv_m)}; equity NPV {money(cash.equity_npv_m)}. Equity IRR {pct(cash.irr_annual)} — {cash.irr_basis || 'basis unavailable'}.</p><p>Missing decision evidence: {(cash.decision_blockers || []).join('; ') || 'Refer to input verification status.'}</p><p>Excluded costs: {(cash.excluded_costs || []).join(', ') || 'Check project-specific taxes and charges.'}</p><p>{cash.financing_basis}</p></section>
    <AdvancedDevelopmentCharts data={data}/><section><h2>Collective-sale screening</h2><p>Maximum modelled land value {money(enbloc.maximum_land_value_m)}; illustrative success probability {pct(enbloc.success_probability)}. These assumptions are not evidence of actual owner consent, executable pricing or statutory approval.</p></section></>;
}
