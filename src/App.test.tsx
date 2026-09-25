import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import App from './App';
import DigitalTwinDashboard from './components/DigitalTwinDashboard';
import AdvancedDevelopment from './components/AdvancedDevelopment';
import { commonMarketHistory } from './components/Visuals';
vi.mock('./components/PlotlyChart', () => ({ default: ({ data, ariaLabel }: any) => <div role="img" aria-label={ariaLabel} data-series={JSON.stringify(data)}/> }));
vi.mock('./components/ArchitecturePage', () => ({ default: () => <div>Architecture view</div> }));
vi.mock('./components/ZoningMap', () => ({ default: () => <div>Map view</div> }));

const asset = { asset_id: 'A', name: 'Alpha building', address: 'Fictional address', country: 'Singapore', segments: ['Office'], source_rows: [], recommendation: { action: 'Hold', probability_of_loss: 0 }, selection: { preferred_action: 'Hold', signal: 'Data Required / Monitor', readiness: { ready: false, missing: ['noi_m'] } }, actions: [{ action: 'Hold', expected_npv_m: 0, p10_npv_m: 0, p50_npv_m: 0, p90_npv_m: 0, probability_of_loss: 0, cvar_95_m: 0 }, { action: 'Redevelop', expected_npv_m: 99, p10_npv_m: -20, p50_npv_m: 99, p90_npv_m: 120, probability_of_loss: .6, cvar_95_m: 500 }] };
function response(data: any, ok = true) { return Promise.resolve({ ok, json: () => Promise.resolve(data) }); }
let fetchMock: ReturnType<typeof vi.fn>;
beforeEach(() => {
  window.history.replaceState(null, '', '/');
  fetchMock = vi.fn((input: any, init?: any) => {
    const url = String(input);
    if (init?.method === 'POST') return response({ detail: 'Calculation queue is full; try again.' }, false);
    if (url.includes('/portfolio')) return response({ assets: [asset] });
    if (url.endsWith('/assets/A')) return response(asset);
    if (url.includes('/scenario-samples')) return response({ samples: {} });
    return response({});
  });
  vi.stubGlobal('fetch', fetchMock);
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

test('opens full navigation and allows a filtered portfolio', async () => {
  render(<App/>);
  expect(screen.getByText('Portfolio intelligence')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Digital Twins' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Optimiser' })).toBeInTheDocument();
  await screen.findByText('Alpha building');
  fireEvent.change(screen.getByLabelText('Search portfolio'), { target: { value: 'unmatched' } });
  expect(screen.getByText('No assets match the filters.')).toBeInTheDocument();
  expect(screen.getByText('Displayed assets').parentElement).toHaveTextContent('0');
});

test('scenario cards use the selected action instead of the maximum raw NPV', async () => {
  render(<App/>);
  await screen.findByText('Alpha building');
  fireEvent.click(screen.getByRole('button', { name: 'Scenario' }));
  await screen.findByText('Risk for the selected action: Hold');
  expect(screen.getByText('Selected expected incremental NPV').parentElement).toHaveTextContent('S$0.00m');
  expect(screen.getByText('Selected expected incremental NPV').parentElement).not.toHaveTextContent('99.00');
});

test('optimiser sends edited inputs and surfaces backend failures', async () => {
  render(<App/>);
  fireEvent.click(screen.getByRole('button', { name: 'Optimiser' }));
  fireEvent.change(screen.getByLabelText('Capital budget (SGD m)'), { target: { value: '120' } });
  fireEvent.click(screen.getByRole('button', { name: 'Run multi-period' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Calculation queue is full; try again.');
  const request = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST');
  expect(JSON.parse(request?.[1]?.body)).toMatchObject({ capital_budget_m: 120, max_projects: 8, max_development_share: .45 });
  expect(screen.getByRole('button', { name: 'Run multi-period' })).toBeEnabled();
});

test('stability renders independently of a two-stage result', async () => {
  fetchMock.mockImplementation((input: any, init?: any) => init?.method === 'POST' ? response({ runs: 20, successful_runs: 18, failed_runs: 2, assets: [], fragile_assets: 0, risk_adjusted_objective_mean_m: 1, portfolio_expected_npv_mean_m: 2 }) : response(String(input).includes('/portfolio') ? { assets: [asset] } : {}));
  render(<App/>);
  fireEvent.click(screen.getByRole('button', { name: 'Optimiser' }));
  fireEvent.click(screen.getByRole('button', { name: 'Test stability' }));
  expect(await screen.findByRole('heading', { name: 'Assumption sensitivity' })).toBeInTheDocument();
  expect(screen.queryByRole('heading', { name: 'Two-stage contingent plan' })).not.toBeInTheDocument();
  expect(screen.getByText(/18 feasible runs out of 20/)).toBeInTheDocument();
});

test('digital-twin filters update cards and plots without implying a filtered portfolio solve', async () => {
  const twin = (id: string, name: string, completeness: number) => ({ asset_id: id, name, segment: 'Office', planning_area: 'Demo area', context_status: 'synthetic_fixture', context_completeness_pct: completeness, verified_underwriting_pct: 0, stability_score: 1, environments: { base: { recommended_action: 'Hold', expected_npv_m: 0, p10_m: 0, p90_m: 0, probability_of_loss: 0 } } });
  fetchMock.mockImplementation(() => response({ assets: [twin('A', 'Alpha', .5), twin('B', 'Beta', 1)], portfolio_summary: { assets: 2, fictional_asset_contexts: 2 }, environments: [{ id: 'base', label: 'Base', assumptions: {}, portfolio: { selections: [], annual_plan: [], portfolio_expected_npv_m: 123 } }], methodology: {} }));
  render(<DigitalTwinDashboard api="/api"/>);
  await screen.findByText('Alpha');
  fireEvent.change(screen.getByLabelText('Search digital twins'), { target: { value: 'Alpha' } });
  expect(screen.queryByText('Beta')).not.toBeInTheDocument();
  expect(screen.getByText('Displayed twins').parentElement).toHaveTextContent('1');
  expect(screen.getByText('Context completeness').parentElement).toHaveTextContent('50.0%');
  const interval = await screen.findByRole('img', { name: 'Filtered asset P10 to P90 intervals' });
  await waitFor(() => expect(JSON.parse(interval.getAttribute('data-series')!)[0].x).toEqual(['A']));
  expect(screen.getByText('Expected portfolio NPV').parentElement).toHaveTextContent('123.00');
  expect(screen.getByText(/always represents all 2 assets/)).toBeInTheDocument();
});

test('advanced analysis does not convert unavailable viewshed into zero loss', async () => {
  fetchMock.mockImplementation(() => response({ viewshed: { status: 'unavailable', view_premium_loss_m: null, contributors: [] }, redevelopment_cashflow: { decision_ready: false, npv_m: -3, npv_basis: 'incremental versus Hold' }, development_envelope: { options: [], preferred: null }, decision_ready: false }));
  render(<AdvancedDevelopment assetId="A" api="/api"/>);
  await screen.findByText('View premium loss');
  expect(screen.getByText('View premium loss').parentElement).toHaveTextContent('Unavailable');
  expect(screen.queryByRole('img', { name: 'Assumed geometry viewshed obstruction' })).not.toBeInTheDocument();
});

test('market charts rebase every price and rent series to one overlapping quarter', () => {
  const common = commonMarketHistory([
    { segment: 'Residential', measure: 'price', observations: [{ period: '1975-Q1', index: 100 }, { period: '2011Q1', index: 500 }, { period: '2026-Q2', index: 750 }] },
    { segment: 'Retail', measure: 'price', observations: [{ period: '2011-Q1', index: 100 }, { period: '2026-Q2', index: 90 }] },
    { segment: 'Office', measure: 'rent', observations: [{ period: '1990-Q1', index: 100 }, { period: '2011-Q1', index: 200 }, { period: '2026-Q2', index: 210 }] },
  ]);
  expect(common?.start).toBe('2011-Q1');
  expect(common?.end).toBe('2026-Q2');
  expect(common?.series.map(row => row.observations.map((point: any) => point.rebased_index))).toEqual([[100, 150], [100, 90], [100, 105]]);
  expect(commonMarketHistory([{ measure: 'price', observations: [{ period: '2010-Q1', index: 100 }] }, { measure: 'rent', observations: [{ period: '2011-Q1', index: 100 }] }])).toBeNull();
});
