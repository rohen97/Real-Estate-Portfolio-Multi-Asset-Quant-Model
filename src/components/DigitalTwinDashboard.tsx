import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Building2, CircleDollarSign, Database, Gauge, Search, ShieldCheck } from 'lucide-react';
import { DigitalTwinCharts } from './Visuals';

const money = (value: unknown) => typeof value === 'number' ? `S$${value.toFixed(1)}m` : '—';
const pct = (value: unknown) => typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '—';

function SummaryCard({ icon: Icon, label, value, detail, color }: { icon: any; label: string; value: string; detail: string; color: string }) {
  return <div className="col-sm-6 col-xl-3"><div className="card twin-summary-card"><div className="card-body"><div className="d-flex align-items-center"><span className={`avatar avatar-md bg-${color}-lt me-3`}><Icon size={21}/></span><div className="flex-fill"><div className="text-secondary text-uppercase small fw-semibold">{label}</div><div className="h2 mb-0 mt-1">{value}</div></div></div><div className="text-secondary small mt-3">{detail}</div></div></div></div>;
}

export default function DigitalTwinDashboard({ api, staticMode = false }: { api: string; staticMode?: boolean }) {
  const [data, setData] = useState<any>();
  const [environmentId, setEnvironmentId] = useState('base');
  const [search, setSearch] = useState('');
  const [action, setAction] = useState('All');
  const [error, setError] = useState('');

  useEffect(() => {
    fetch(staticMode ? import.meta.env.BASE_URL + 'data/digital_twin_dashboard.json' : api + '/digital-twins/dashboard')
      .then(response => {
        if (!response.ok) throw new Error('Digital-twin dashboard unavailable');
        return response.json();
      })
      .then(setData)
      .catch(reason => setError(String(reason)));
  }, [api, staticMode]);

  const environment = data?.environments?.find((item: any) => item.id === environmentId);
  const filtered = useMemo(() => {
    const query = search.toLowerCase();
    return (data?.assets || []).filter((asset: any) => {
      const result = asset.environments?.[environmentId];
      const matchesSearch = !query || `${asset.name} ${asset.segment} ${asset.planning_area}`.toLowerCase().includes(query);
      const matchesAction = action === 'All' || result?.recommended_action === action;
      return matchesSearch && matchesAction;
    });
  }, [data, environmentId, search, action]);

  if (error) return <div className="alert alert-danger" role="alert"><AlertTriangle size={20}/><div>{error}</div></div>;
  if (!data) return <div className="card"><div className="card-body text-center py-6"><div className="spinner-border text-primary mb-3"/><div className="text-secondary">Loading digital twins…</div></div></div>;
  if (data.status === 'not_run') return <div className="alert alert-warning" role="alert">Run <code>scripts/build_digital_twin_dashboard.py</code> to generate the digital-twin portfolio.</div>;

  const summary = data.portfolio_summary;
  const portfolio = environment?.portfolio || {};
  return <div className="digital-twin-page">
    <div className="alert alert-warning d-flex align-items-start" role="alert"><AlertTriangle className="me-2 flex-shrink-0" size={20}/><div><strong>Synthetic software validation</strong><div className="small mt-1">Real Far East identity, location and zoning are retained. Financial, lease and outcome fields are generated and must not be treated as verified investment results.</div></div></div>

    <div className="row row-cards mb-4">
      <SummaryCard icon={Building2} label="Portfolio twins" value={String(summary.assets)} detail="Real Far East asset anchors" color="blue"/>
      <SummaryCard icon={Database} label="Real context coverage" value={pct(summary.average_real_context_pct)} detail="Identity, location, segment and zoning" color="azure"/>
      <SummaryCard icon={ShieldCheck} label="Verified underwriting" value={pct(summary.verified_underwriting_pct)} detail="Financial fields remain synthetic" color="orange"/>
      <SummaryCard icon={Gauge} label="Fragile decisions" value={String(summary.fragile_assets)} detail="Action changes across environments" color="red"/>
    </div>

    <div className="card mb-4"><div className="card-header"><div><div className="card-title">Market environment</div><div className="text-secondary small">Switch assumptions to test the portfolio response</div></div></div><div className="card-body"><div className="btn-list">
      {data.environments.map((item: any) => <button key={item.id} className={`btn ${environmentId === item.id ? 'btn-primary' : 'btn-outline-secondary'}`} onClick={() => setEnvironmentId(item.id)}>{item.label}</button>)}
    </div></div></div>

    <div className="card mb-4 environment-overview"><div className="card-body"><div className="row align-items-center g-4"><div className="col-lg-5"><div className="subheader">Selected environment</div><h2 className="mt-1 mb-2">{environment.label}</h2><p className="text-secondary mb-0">{environment.description}</p></div><div className="col-lg-7"><div className="row g-3">
      <div className="col-6"><div className="datagrid-item"><div className="datagrid-title">Expected portfolio NPV</div><div className="datagrid-content text-primary fw-bold">{money(portfolio.portfolio_expected_npv_m)}</div></div></div>
      <div className="col-6"><div className="datagrid-item"><div className="datagrid-title">Simulated realised NPV</div><div className="datagrid-content fw-bold">{money(portfolio.portfolio_simulated_realised_npv_m)}</div></div></div>
      <div className="col-6"><div className="datagrid-item"><div className="datagrid-title">P10–P90 coverage</div><div className="datagrid-content fw-bold">{pct(environment.p10_p90_coverage)}</div></div></div>
      <div className="col-6"><div className="datagrid-item"><div className="datagrid-title">Capital required</div><div className="datagrid-content fw-bold">{money(portfolio.capital_required_m)}</div></div></div>
    </div></div></div></div></div>

    <DigitalTwinCharts data={data}/>

    <div className="row row-cards mb-4">
      <div className="col-lg-5"><div className="card h-100"><div className="card-header"><h3 className="card-title">Environment assumptions</h3></div><div className="card-body"><div className="datagrid">
        <div className="datagrid-item"><div className="datagrid-title">Rent change</div><div className="datagrid-content">{pct(environment.assumptions.rent_change)}</div></div>
        <div className="datagrid-item"><div className="datagrid-title">Cap-rate shift</div><div className="datagrid-content">{pct(environment.assumptions.cap_rate_shift)}</div></div>
        <div className="datagrid-item"><div className="datagrid-title">Construction costs</div><div className="datagrid-content">{environment.assumptions.construction_cost_multiplier.toFixed(2)}×</div></div>
        <div className="datagrid-item"><div className="datagrid-title">Approval multiplier</div><div className="datagrid-content">{environment.assumptions.approval_multiplier.toFixed(2)}×</div></div>
        <div className="datagrid-item"><div className="datagrid-title">Simulation accuracy</div><div className="datagrid-content">{pct(environment.correct_action_rate_vs_simulation)}</div></div>
        <div className="datagrid-item"><div className="datagrid-title">Mean simulated regret</div><div className="datagrid-content">{money(environment.mean_decision_regret_m)}</div></div>
      </div></div></div></div>
      <div className="col-lg-7"><div className="card h-100"><div className="card-header"><h3 className="card-title">Five-year capital plan</h3><div className="card-actions"><span className="badge bg-green-lt">Feasible</span></div></div><div className="table-responsive"><table className="table table-vcenter card-table"><thead><tr><th>Year</th><th>Capex</th><th>Released</th><th>NOI disruption</th><th>Projects</th></tr></thead><tbody>
        {(portfolio.annual_plan || []).map((year: any) => <tr key={year.year}><td><span className="badge bg-blue-lt">Year {year.year}</span></td><td>{money(year.capex_m)}</td><td className="text-green">{money(year.capital_released_m)}</td><td>{money(year.noi_disruption_m)}</td><td>{year.active_projects}</td></tr>)}
      </tbody></table></div></div></div>
    </div>

    <div className="card">
      <div className="card-header"><div><h3 className="card-title">Digital-twin decisions</h3><div className="text-secondary small mt-1">{filtered.length} assets shown for {environment.label.toLowerCase()}</div></div><div className="card-actions twin-filters"><div className="input-icon"><span className="input-icon-addon"><Search size={16}/></span><input className="form-control" value={search} onChange={event => setSearch(event.target.value)} placeholder="Search asset, segment or area"/></div><select className="form-select" value={action} onChange={event => setAction(event.target.value)}>{['All','Hold','Retrofit','Repurpose','Redevelop','Sell'].map(value => <option key={value}>{value}</option>)}</select></div></div>
      <div className="table-responsive twin-table"><table className="table table-vcenter table-striped card-table"><thead><tr><th>Asset</th><th>Segment</th><th>Planning area</th><th>Recommendation</th><th>Expected NPV</th><th>P10–P90</th><th>Loss probability</th><th>Stability</th><th>Data</th></tr></thead><tbody>
        {filtered.slice(0, 177).map((asset: any) => { const result = asset.environments[environmentId]; return <tr key={asset.asset_id}><td><div className="d-flex align-items-center"><span className="avatar avatar-sm bg-blue-lt me-2"><CircleDollarSign size={16}/></span><div><div className="fw-semibold">{asset.name}</div><div className="text-secondary small">{asset.asset_id}</div></div></div></td><td>{asset.segment}</td><td>{asset.planning_area}</td><td><span className="badge bg-blue-lt">{result.recommended_action}</span></td><td className="fw-semibold">{money(result.expected_npv_m)}</td><td>{money(result.p10_m)} – {money(result.p90_m)}</td><td><span className={`badge ${result.probability_of_loss > .4 ? 'bg-red-lt' : result.probability_of_loss > .2 ? 'bg-yellow-lt' : 'bg-green-lt'}`}>{pct(result.probability_of_loss)}</span></td><td><div className="d-flex align-items-center gap-2"><div className="progress progress-sm flex-fill"><div className={`progress-bar ${asset.fragile ? 'bg-yellow' : 'bg-green'}`} style={{width:pct(asset.stability_score)}}/></div><span className="small">{pct(asset.stability_score)}</span></div>{asset.fragile && <div className="text-warning small mt-1">Review</div>}</td><td><span className="badge bg-azure-lt me-1">Real context</span><span className="badge bg-orange-lt">Synthetic financials</span></td></tr> })}
      </tbody></table></div>
    </div>
  </div>;
}
