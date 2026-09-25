import { useEffect, useMemo, useState } from 'react';
import { Building2, Database, Landmark, ChartNoAxesCombined, Activity, GitCompareArrows, Scale, FileCheck2, LayoutDashboard, Search, AlertTriangle, Crosshair, BrainCircuit, Workflow, ScanSearch, Blocks } from 'lucide-react';
import { PortfolioCharts, ZoningCharts, ValuationCharts, ScenarioCharts, SelectionCharts, ActionsCharts, OptimiserCharts, ModelDiagnostics, EvidenceCharts, AuditCharts, ZoningPredictionOverview, TwoStageCharts, MarketRegimeCharts, MarketHistoryCharts, StabilityCharts } from './components/Visuals';
import ArchitecturePage from './components/ArchitecturePage';
import ZoningMap from './components/ZoningMap';
import AdvancedDevelopment from './components/AdvancedDevelopment';
import DigitalTwinDashboard from './components/DigitalTwinDashboard';
import { API, STATIC_DEMO, PUBLIC_DEMO, runCalculation } from './config';

const money = (value: any) => typeof value === 'number' && Number.isFinite(value) ? `S$${value.toFixed(2)}m` : 'Not available';
const pct = (value: any) => typeof value === 'number' && Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : 'Not estimated';
const number = (value: any) => typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString() : 'Not available';
const NAV = [['Portfolio', LayoutDashboard], ['Digital Twins', Blocks], ['Asset', Building2], ['Evidence', Database], ['Zoning', Landmark], ['Zoning ML', ScanSearch], ['Development', Blocks], ['Selection', Crosshair], ['Valuation', ChartNoAxesCombined], ['Scenario', Activity], ['Actions', GitCompareArrows], ['Optimiser', Scale], ['Models', BrainCircuit], ['Architecture', Workflow], ['Audit', FileCheck2]] as const;
const ASSET_TABS = new Set(['Asset', 'Evidence', 'Zoning', 'Development', 'Selection', 'Valuation', 'Scenario', 'Actions', 'Audit']);
async function getJson(path: string, signal?: AbortSignal) {
  const response = await fetch(API + path, { signal });
  if (!response.ok) throw new Error('The requested data could not be loaded.');
  return response.json();
}
function Pill({ children, t = 'blue' }: { children: any; t?: string }) { return <span className={'pill ' + t}>{children}</span>; }
function Metric({ l, v, s }: { l: string; v: string; s?: string }) { return <div className="metric"><span>{l}</span><strong>{v}</strong>{s && <small>{s}</small>}</div>; }
function Warning({ children }: { children: any }) { return <div className="warning"><AlertTriangle size={18}/><div>{children}</div></div>; }

export default function App() {
  const [assets, setAssets] = useState<any[]>([]), [id, setId] = useState(''), [d, setD] = useState<any>();
  const [tab, setTab] = useState(() => {
    const requested = new URLSearchParams(window.location.search).get('tab');
    return NAV.some(([name]) => name === requested) ? requested! : 'Portfolio';
  });
  const [search, setSearch] = useState(''), [scope, setScope] = useState('Singapore');
  const [market, setMarket] = useState<any>(), [error, setError] = useState(''), [assetError, setAssetError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    getJson('/portfolio?limit=500', controller.signal).then(result => {
      const rows = result.assets || [];
      setAssets(rows); setId((rows.find((a: any) => a.country === 'Singapore') || rows[0])?.asset_id || '');
    }).catch(reason => { if (reason.name !== 'AbortError') setError(String(reason.message)); });
    getJson('/market/public', controller.signal).then(setMarket).catch(() => {});
    return () => controller.abort();
  }, []);
  useEffect(() => {
    if (!id) return;
    const controller = new AbortController();
    setD(undefined); setAssetError('');
    getJson('/assets/' + encodeURIComponent(id), controller.signal).then(setD).catch(reason => { if (reason.name !== 'AbortError') setAssetError(String(reason.message)); });
    return () => controller.abort();
  }, [id]);
  const filtered = useMemo(() => assets.filter(a => (scope === 'All' || a.country === scope) && (!search || `${a.name} ${a.address || ''} ${(a.segments || []).join(' ')}`.toLowerCase().includes(search.toLowerCase()))), [assets, scope, search]);
  function navigate(next: string) {
    setTab(next); const url = new URL(window.location.href); url.searchParams.set('tab', next); window.history.replaceState(null, '', url);
  }
  return <div className="page app tabler-shell">
    <aside className="navbar navbar-vertical navbar-expand-lg" data-bs-theme="dark"><div className="brand"><b>FE</b><div>Portfolio intelligence<small>Singapore model · revised methodology</small></div></div>
      {NAV.map(([name, Icon]) => <button key={name} aria-current={tab === name ? 'page' : undefined} className={tab === name ? 'on' : ''} onClick={() => navigate(name)}><Icon size={18}/>{name}</button>)}
      <div className="synthetic">{PUBLIC_DEMO ? 'PUBLIC SYNTHETIC DEMO' : 'PROVISIONAL MODEL'}<br/><small>{PUBLIC_DEMO ? 'Fictional assets; official market context' : 'Evidence status shown for each asset'}</small></div>
    </aside>
    <main className="page-wrapper"><header className="navbar navbar-expand-md d-print-none"><div><small>SINGAPORE PORTFOLIO INTELLIGENCE</small><h1>{tab}</h1></div><div>
      {!PUBLIC_DEMO && <a className="download" href={API + '/artifacts/underwriting-template'}>Underwriting template</a>}
      <a className="download" href={import.meta.env.BASE_URL + 'reports/Real_Estate_Dashboard_Interpretation_Report.docx'}>Word report</a>
      <a className="download" href={import.meta.env.BASE_URL + 'reports/Real_Estate_Dashboard_Interpretation_Report.pdf'}>PDF report</a>
      <Pill t="orange">{PUBLIC_DEMO ? 'Fictional portfolio' : 'Evidence verification required'}</Pill><Pill t="teal">{STATIC_DEMO ? 'Saved results' : 'Backend connected'}</Pill>
    </div></header>
      <div className="page-body"><div className="container-xl">
        {STATIC_DEMO && <div className="callout">This public page shows saved model results. All sections can be explored; new calculations require the hosted backend.</div>}
        {error && <div className="warning" role="alert">{error}</div>}
        {ASSET_TABS.has(tab) && <section className="filters"><label>Selected asset <select aria-label="Selected asset" value={id} onChange={e => setId(e.target.value)}>{assets.map(a => <option key={a.asset_id} value={a.asset_id}>{a.name}</option>)}</select></label>{assetError && <span role="alert">{assetError}</span>}{!d && !assetError && <span>Loading asset analysis…</span>}</section>}
        {tab === 'Portfolio' && <Portfolio a={filtered} total={assets} market={market} search={search} setSearch={setSearch} scope={scope} setScope={setScope} open={next => { setId(next); navigate('Asset'); }}/>}
        {tab === 'Digital Twins' && <DigitalTwinDashboard api={API} staticMode={STATIC_DEMO}/>}
        {d && tab === 'Asset' && <Asset d={d}/>} {d && tab === 'Evidence' && <Evidence d={d}/>}
        {d && tab === 'Zoning' && <Zoning d={d}/>} {tab === 'Zoning ML' && <ZoningPredictionOverview api={API}/>}
        {d && tab === 'Development' && <AdvancedDevelopment assetId={d.asset_id} api={API}/>}
        {d && tab === 'Selection' && <SelectionLogic d={d}/>} {d && tab === 'Valuation' && <Valuation d={d}/>}
        {d && tab === 'Scenario' && <Scenario d={d}/>} {d && tab === 'Actions' && <Actions d={d}/>}
        {tab === 'Models' && <><ModelDiagnostics api={API}/><MarketRegimeCharts api={API}/></>}
        {tab === 'Architecture' && <ArchitecturePage/>} {tab === 'Optimiser' && <Optimiser/>}
        {d && tab === 'Audit' && <Audit d={d}/>}
      </div></div>
      <footer className="footer footer-transparent">{PUBLIC_DEMO ? 'Fictional portfolio and generated financials. Official national market indices are separate context; no demonstrated investment alpha.' : 'Input provenance and evidence readiness are shown by asset. Model outputs remain subject to project-specific verification.'}</footer>
    </main>
  </div>;
}

function Portfolio({ a, total, market, search, setSearch, scope, setScope, open }: { a: any[]; total: any[]; market: any; search: string; setSearch: (x: string) => void; scope: string; setScope: (x: string) => void; open: (x: string) => void }) {
  const countries = Array.from(new Set(total.map(x => x.country))).sort();
  return <><section><div className="head"><div><h2>Portfolio register</h2><p>{PUBLIC_DEMO ? 'Fictional records demonstrate the decision workflow.' : 'Source status must be checked before using any record for underwriting.'} All cards and portfolio charts below reflect the current filter.</p></div><Pill>{a.length} of {total.length} assets</Pill></div>
    <div className="filters"><label><Search size={17}/><input aria-label="Search portfolio" placeholder="Search property, address or segment" value={search} onChange={e => setSearch(e.target.value)}/></label><select aria-label="Portfolio country scope" value={scope} onChange={e => setScope(e.target.value)}><option>All</option>{countries.map(country => <option key={country}>{country}</option>)}</select></div>
    <div className="metrics"><Metric l="Displayed assets" v={String(a.length)}/><Metric l="Singapore in view" v={String(a.filter(x => x.country === 'Singapore').length)}/><Metric l="Planning review in view" v={String(a.filter(x => x.zoning_model_status === 'review_required').length)}/><Metric l="Underwriting ready in view" v={String(a.filter(x => x.selection?.readiness?.ready === true).length)}/></div></section>
    <PortfolioCharts assets={a}/>
    {market && <section><div className="head"><div><h2>Official Singapore market context</h2><p>National indices and historical changes are context, not asset forecasts or alpha. {market.status || market.source_status || ''}</p></div><Pill>{market.as_of || 'Date unavailable'}</Pill></div><div className="facts">
      {['private_residential', 'office', 'retail', 'industrial'].map(segment => <Metric key={segment} l={segment.replaceAll('_', ' ') + ' price QoQ'} v={pct(market.market_indicators?.[segment]?.price_qoq)} s={'YoY ' + pct(market.market_indicators?.[segment]?.price_yoy)}/>)}</div><MarketHistoryCharts market={market}/></section>}
    <section><div className="tablewrap"><table><thead><tr><th>Property</th><th>Country</th><th>Segments</th><th>Planning evidence</th><th>Readiness signal</th><th>Screened action</th><th/></tr></thead><tbody>{a.map(x => <tr key={x.asset_id}><td><b>{x.name}</b><small>{x.address || x.geocoded_address || 'Address unavailable'}</small></td><td>{x.country}</td><td>{(x.segments || []).join(', ')}</td><td>{x.ura_zoning?.match_method || 'Unverified'}<small>{x.ura_zoning?.matches?.[0]?.lu_desc || 'No match'}</small></td><td><Pill t={x.selection?.readiness?.ready ? 'teal' : 'orange'}>{x.selection?.signal || 'Not modelled'}</Pill></td><td>{x.selection?.preferred_action || x.recommendation?.action || 'Not modelled'}</td><td><button className="link" onClick={() => open(x.asset_id)}>Open →</button></td></tr>)}</tbody></table>{!a.length && <p>No assets match the filters.</p>}</div></section>
  </>;
}

function Asset({ d }: { d: any }) {
  return <><div className="hero"><div><Pill>{d.country}</Pill><h2>{d.name}</h2><p>{d.address || 'Address unavailable'} · {d.asset_id}</p></div><div><small>READINESS SIGNAL</small><strong>{d.selection?.signal || 'Not modelled'}</strong><span>Screened action: {d.selection?.preferred_action || d.recommendation?.action || 'Unavailable'}</span></div></div>
    <Warning>{d.input_quality || 'Input evidence unverified'}. {PUBLIC_DEMO ? 'The portfolio is fictional. ' : ''}A preferred action is a model ranking, not approval to invest.</Warning>
    <div className="metrics"><Metric l="Modelled current value" v={money(d.economics?.current_value_m)}/><Metric l="Risk-adjusted margin over Hold" v={money(d.selection?.opportunity?.risk_adjusted_margin_over_hold_m)}/><Metric l="Investment alpha" v="Not established"/><Metric l="Selected action loss probability" v={pct(d.recommendation?.probability_of_loss)}/></div>
    <section><h2>Decision rationale</h2><p>{d.recommendation?.explanation || 'No recommendation is available.'}</p><p>{d.selection?.reasons?.join(' ')}</p><div className="facts"><Metric l="Jurisdiction" v={d.jurisdiction || d.country}/><Metric l="Land-use match" v={d.ura_zoning?.matches?.[0]?.lu_desc || 'Unmatched'}/><Metric l="Planning match method" v={d.ura_zoning?.match_method || 'Unverified'}/><Metric l="Underwriting ready" v={d.selection?.readiness?.ready ? 'Yes' : 'No'}/></div></section></>;
}
function Evidence({ d }: { d: any }) {
  return <section><h2>Evidence and provenance</h2><p>{PUBLIC_DEMO ? 'Example source references belong to a fictional fixture.' : 'Catalogue provenance and verified underwriting are separate evidence categories.'}</p>
    {d.source_rows?.map((row: any, index: number) => <article className="evidence" key={index}><Database/><div><b>{row.sheet}</b><small>Source row {row.row}</small></div><Pill t="orange">{PUBLIC_DEMO ? 'Example record' : 'Source reference'}</Pill></article>)}
    <Warning>Populated fields, geocoding and catalogue matches do not verify title, area, valuation, NOI, leases, debt or action costs. Outstanding evidence: {d.selection?.readiness?.missing?.join(', ') || 'See input provenance.'}</Warning><EvidenceCharts d={d}/></section>;
}
function Zoning({ d }: { d: any }) {
  const c = d.capacity, z = d.ura_zoning;
  if (!c) return <Warning>Capacity analysis is unavailable for this asset.</Warning>;
  return <><Warning>Capacity is a planning screen. {PUBLIC_DEMO ? 'Coordinates and zoning are fictional fixture context. ' : ''}A match does not establish legal development permission.</Warning><section><h2>What this means for a decision</h2><p>Unused floor area identifies a redevelopment research candidate. The Development tab uses a planning envelope to estimate buildable area, costs and incremental value versus Hold. ML checks support analyst review.</p><p>Detailed feasibility and zoning ML are not yet connected to the main Hold / Retrofit / Repurpose / Redevelop / Sell rankings. Buy is not assessed: acquisition price and transaction underwriting are required.</p><div className="callout"><b>Data Required / Monitor</b> means evidence is incomplete. <b>Hold</b> is the economic action of retaining the asset, assessed against alternatives and portfolio constraints. A capacity opportunity alone establishes neither.</div></section><div className="metrics">{[['Statutory GFA', c.statutory_gfa_sqm], ['Physical GFA', c.physical_gfa_sqm], ['De facto GFA', c.de_facto_gfa_sqm], ['Economic GFA', c.economic_gfa_sqm]].map(([label, value]) => <Metric key={label} l={label} v={number(value) + ' sqm'}/>)}</div>
    <div className="two"><section><h2>Planning context</h2><Metric l="Land use" v={z?.matches?.[0]?.lu_desc || 'Unmatched'}/><Metric l="Planning area" v={z?.matches?.[0]?.planning_area || 'Unavailable'}/><Metric l="Match method" v={z?.match_method || 'Unverified'}/><Metric l="GPR used" v={number(d.statutory_gpr_used)} s={d.gpr_source}/><p>{z?.warning}</p></section><section><h2>Constraints and uncertainty</h2><div className="tags">{c.binding_constraints?.map((x: string) => <Pill key={x}>{x.replaceAll('_', ' ')}</Pill>)}</div><Metric l="Unused economic GFA" v={number(c.unused_economic_gfa_sqm) + ' sqm'}/><Metric l="Screening residual option" v={money(c.residual_value_m)} s="Excluded from additive selection adjustments"/><p>P10 / P50 / P90 attainable area: {number(c.p10_gfa_sqm)} / {number(c.p50_gfa_sqm)} / {number(c.p90_gfa_sqm)} sqm.</p></section></div><ZoningMap assetId={d.asset_id} api={API}/><ZoningCharts d={d}/></>;
}
function Valuation({ d }: { d: any }) {
  return <><Warning>Values depend on the supplied cash-flow assumptions and evidence status. The terminal receipt is already included in DCF and must not be added again.</Warning><div className="metrics"><Metric l="Current modelled value" v={money(d.economics?.current_value_m)}/><Metric l="Current modelled NOI" v={money(d.economics?.current_noi_m)}/><Metric l="Discount rate" v={pct(d.economics?.discount_rate)}/><Metric l="DCF value" v={money(d.dcf?.value_m)}/></div><ValuationCharts d={d}/><section><h2>Annual cash flows</h2><div className="cashflows">{d.dcf?.cashflows_m?.map((value: number, index: number) => <div key={index}><span>Year {index + 1}</span><b>{money(value)}</b></div>)}</div></section></>;
}
function Scenario({ d }: { d: any }) {
  const chosen = d.selection?.preferred_action || d.recommendation?.action;
  const result = d.actions?.find((row: any) => row.action === chosen);
  return <><section><h2>Risk for the selected action: {chosen || 'Unavailable'}</h2><p>These metrics follow the selected risk-adjusted decision. P10–P90 spans 80% of modelled outcomes; it is not a confidence interval around a verified forecast. Hold risk is incremental to retaining the asset, not zero total asset risk.</p><div className="metrics"><Metric l="Selected expected incremental NPV" v={money(result?.expected_npv_m)}/><Metric l="P10 NPV" v={money(result?.p10_npv_m)}/><Metric l="Loss probability" v={pct(result?.probability_of_loss)}/><Metric l="Loss CVaR 95%" v={money(result?.cvar_95_m)}/></div></section><ScenarioCharts d={d} api={API}/><section><h2>Illustrative approval pathway</h2>{d.approval?.stages?.map((row: any) => <article key={row.stage} className="stage"><b>{row.stage}</b><span>{pct(row.conditional_probability)} conditional pass</span><span>{row.expected_months} months</span><span>{pct(row.cumulative_probability)} cumulative pass</span></article>)}</section></>;
}
function Actions({ d }: { d: any }) {
  const chosen = d.selection?.preferred_action || d.recommendation?.action;
  return <section><h2>Actions versus Hold</h2><p>Expected incremental NPV includes the action's specified cash flows and approval branches. Negative Sell capex is a receipt; it is not profit.</p><div className="actions">{d.actions?.map((row: any) => <article key={row.action} className={row.action === chosen ? 'preferred' : ''}><h3>{row.action}</h3><strong>{money(row.expected_npv_m)}</strong><small>expected incremental NPV</small><p>P10 {money(row.p10_npv_m)}<br/>Loss probability {pct(row.probability_of_loss)}<br/>CVaR {money(row.cvar_95_m)}<br/>Net capital {money(row.capex_m)}<br/>Execution {row.execution_years} years</p><Pill t={row.decision_ready ? 'teal' : 'orange'}>{row.decision_ready ? 'Evidence ready' : 'Evidence incomplete'}</Pill></article>)}</div><ActionsCharts d={d}/></section>;
}
function ConstraintAudit({ result }: { result: any }) {
  const audit = result?.constraint_audit;
  if (!audit) return <p>Independent constraint audit unavailable for this snapshot.</p>;
  return <details><summary>{audit.passed ? 'Constraint audit passed' : 'Constraint audit failed'} · {audit.violation_count} violations · {audit.checks?.length || 0} checks</summary><p>Checks recompute the encoded plan; they do not verify underwriting inputs. Tolerance {audit.tolerance}; maximum residual {audit.max_violation}.</p><div className="tablewrap"><table><thead><tr><th>Constraint</th><th>Actual</th><th>Lower</th><th>Upper</th><th>Violation</th></tr></thead><tbody>{audit.checks?.map((row: any, index: number) => <tr key={index}><td>{row.constraint}</td><td>{number(row.lhs)}</td><td>{row.lower == null ? '—' : number(row.lower)}</td><td>{row.upper == null ? '—' : number(row.upper)}</td><td>{number(row.violation)}</td></tr>)}</tbody></table></div></details>;
}
function SavedSettings({ result }: { result: any }) {
  if (!result?.snapshot_request) return null;
  return <details><summary>Settings used for this saved calculation</summary><dl>{Object.entries(result.snapshot_request).map(([key, value]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{String(value)}</dd></div>)}</dl><p>{result.snapshot_warning}</p></details>;
}
function Optimiser() {
  const [parameters, setParameters] = useState({ capital_budget_m: 500, minimum_liquidity_m: 50, max_projects: 8, max_development_share: .45, cvar_penalty: .3, minimum_noi_ratio: .7 });
  const [o, setO] = useState<any>(), [twoStage, setTwoStage] = useState<any>(), [stability, setStability] = useState<any>();
  const [busy, setBusy] = useState(''), [error, setError] = useState('');
  useEffect(() => {
    if (!STATIC_DEMO) return;
    const controller = new AbortController();
    Promise.all([getJson('/snapshots/optimise', controller.signal).then(setO), getJson('/snapshots/two-stage', controller.signal).then(setTwoStage), getJson('/snapshots/stability', controller.signal).then(setStability)]).catch(reason => { if (reason.name !== 'AbortError') setError('A saved optimiser result is unavailable.'); });
    return () => controller.abort();
  }, []);
  async function run(kind: string) {
    setBusy(kind); setError('');
    try {
      if (Object.values(parameters).some(value => !Number.isFinite(value) || value < 0) || parameters.max_development_share > 1 || parameters.minimum_noi_ratio > 1 || parameters.cvar_penalty > 10 || parameters.max_projects > 500 || !Number.isInteger(parameters.max_projects)) throw new Error('Enter finite nonnegative inputs, shares between zero and one, and a whole project count up to 500.');
      if (parameters.minimum_liquidity_m > parameters.capital_budget_m) throw new Error('Minimum liquidity cannot exceed the initial capital budget.');
      if (kind === 'two-stage') {
        const { max_projects, max_development_share, ...rest } = parameters;
        setTwoStage(await runCalculation('/optimise/two-stage', { ...rest, max_concurrent_projects: max_projects, max_development_share }));
      } else {
        const { minimum_noi_ratio, ...rest } = parameters;
        const result = await runCalculation(kind === 'stability' ? '/optimise/stability' : '/optimise', rest);
        if (kind === 'stability') setStability(result); else setO(result);
      }
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Calculation failed.'); }
    finally { setBusy(''); }
  }
  const fields = [['capital_budget_m', 'Capital budget (SGD m)', 0, 1000000, 10], ['minimum_liquidity_m', 'Minimum liquidity (SGD m)', 0, 1000000, 5], ['max_projects', 'Concurrent projects', 0, 500, 1], ['max_development_share', 'Development asset share', 0, 1, .05], ['cvar_penalty', 'CVaR penalty', 0, 10, .05], ['minimum_noi_ratio', 'Retained NOI ratio (two-stage)', 0, 1, .05]] as const;
  return <><section><h2>Portfolio decision controls</h2><p>Capital is net of settled sale receipts. Development share limits the number of assets. The risk penalty is a preference, not a cash expense.</p>{STATIC_DEMO && <Warning>Calculations require the hosted backend; this page shows saved results. Controls below describe inputs for new calculations. Each saved result lists its own historical settings below.</Warning>}<div className="facts">{fields.map(([key, label, min, max, step]) => <label key={key}>{label}<input className="form-control" type="number" aria-label={label} min={min} max={max} step={step} disabled={STATIC_DEMO || !!busy} value={parameters[key]} onChange={event => setParameters(previous => ({ ...previous, [key]: Number(event.target.value) }))}/></label>)}</div><div className="optimizer-buttons">{[['multi-period', 'Run multi-period'], ['two-stage', 'Run two-stage'], ['stability', 'Test stability']].map(([kind, label]) => <button className="primary" key={kind} disabled={STATIC_DEMO || !!busy} onClick={() => run(kind)}>{busy === kind ? 'Calculating…' : label}</button>)}</div>{error && <p role="alert" className="warning">{error}</p>}</section>
    {o && <section><h2>Multi-period portfolio</h2><SavedSettings result={o}/><Pill t={o.feasible ? 'teal' : 'red'}>{o.feasible ? 'Audited feasible' : 'No feasible plan'}</Pill><p>{o.status}</p><div className="metrics"><Metric l="Expected NPV" v={money(o.portfolio_expected_npv_m)}/><Metric l="Risk-adjusted objective" v={money(o.risk_adjusted_objective_m)}/><Metric l="Gross capital required" v={money(o.capital_required_m)}/><Metric l="Capital released" v={money(o.capital_released_m)}/></div><p>{o.risk_interpretation}</p><p>{o.timing_interpretation}</p><OptimiserCharts o={o}/><div className="tablewrap"><table><thead><tr><th>Asset</th><th>Action</th><th>Start</th><th>Decision-time NPV</th><th>Net capital</th></tr></thead><tbody>{o.selections?.map((row: any) => <tr key={row.asset_id}><td>{row.asset_name}</td><td>{row.action}</td><td>Year {row.start_year}</td><td>{money(row.expected_npv_m)}</td><td>{money(row.capex_m)}</td></tr>)}</tbody></table></div><ConstraintAudit result={o}/></section>}
    {twoStage && <section><h2>Two-stage contingent plan</h2><SavedSettings result={twoStage}/><Pill t={twoStage.feasible ? 'teal' : 'red'}>{twoStage.feasible ? 'Audited feasible' : 'No feasible plan'}</Pill><p>{twoStage.status}</p><div className="metrics"><Metric l="Expected recourse NPV" v={money(twoStage.portfolio_expected_npv_m)}/><Metric l="Joint loss CVaR" v={money(twoStage.portfolio_loss_cvar_m)}/><Metric l="Risk-adjusted objective" v={money(twoStage.risk_adjusted_objective_m)}/></div><p>{twoStage.recourse_interpretation}</p><p>{twoStage.risk_interpretation}</p><TwoStageCharts twoStage={twoStage}/><ConstraintAudit result={twoStage}/></section>}
    {stability && <section><h2>Assumption sensitivity</h2><SavedSettings result={stability}/><p>{stability.successful_runs ?? stability.runs} feasible runs out of {stability.runs}; {stability.failed_runs ?? 0} failed runs. Frequencies are conditional on feasibility. Modal choices are not necessarily a jointly feasible portfolio.</p><div className="metrics"><Metric l="Mean expected NPV" v={money(stability.portfolio_expected_npv_mean_m)}/><Metric l="Mean penalised objective" v={money(stability.risk_adjusted_objective_mean_m ?? stability.objective_mean_m)}/><Metric l="Fragile assets" v={String(stability.fragile_assets ?? 'Unavailable')}/></div><StabilityCharts stability={stability}/><p>{stability.method}</p></section>}
  </>;
}
function Audit({ d }: { d: any }) {
  return <section><h2>Evidence and decision readiness</h2><div className="facts"><Metric l="Asset ID" v={d.asset_id}/><Metric l="Model version" v={d.model_version || 'Unavailable'}/><Metric l="Evidence ready" v={d.selection?.readiness?.ready ? 'Yes' : 'No'}/><Metric l="Verified implementation approval" v="Not supplied"/></div><Warning>Running the model does not approve an investment. Missing evidence: {d.selection?.readiness?.missing?.join(', ') || 'Refer to the evidence register.'}</Warning><AuditCharts d={d}/></section>;
}
function SelectionLogic({ d }: { d: any }) {
  const s = d.selection;
  if (!s) return <Warning>Selection logic is unavailable for this asset.</Warning>;
  const opportunity = s.opportunity || {};
  return <><div className="metrics"><Metric l="Readiness signal" v={s.signal}/><Metric l="Screened action" v={s.preferred_action}/><Metric l="Risk-adjusted margin over Hold" v={money(opportunity.risk_adjusted_margin_over_hold_m)}/><Metric l="Demonstrated alpha" v="Not established"/></div><Warning>{s.warning}</Warning><div className="two"><section><h2>Opportunity and break-even costs</h2><Metric l="Incremental NPV over Hold" v={money(opportunity.expected_incremental_npv_m)}/><Metric l="Additional discounted cost allowance" v={money(opportunity.break_even_additional_pv_cost_m)} s="Extra costs consume this expected-NPV allowance one-for-one"/><Metric l="Margin over next action" v={money(opportunity.margin_to_runner_up_m)}/><Metric l="Annual equivalent incremental yield" v={pct(opportunity.annual_equivalent_incremental_yield)} s="Not total return; do not add to NOI yield or historical price growth"/></section><section><h2>Evidence required</h2><p>{s.reasons?.join(' ')}</p><p>En-bloc, transformation, supply, view and tenure screens remain research hypotheses and are excluded from additive action value.</p><p>{s.readiness?.missing?.join(', ')}</p></section></div><SelectionCharts d={d}/><section><h2>Risk-adjusted action ranking</h2><div className="actions">{s.action_comparison?.map((row: any) => <article key={row.action} className={row.action === s.preferred_action ? 'preferred' : ''}><h3>{row.action}</h3><strong>{money(row.risk_adjusted_score_m)}</strong><small>expected NPV − {s.cvar_penalty} × loss CVaR</small><p>Expected NPV {money(row.base_action_npv_m)}<br/>Loss CVaR {money(row.cvar_95_m)}</p></article>)}</div></section></>;
}
