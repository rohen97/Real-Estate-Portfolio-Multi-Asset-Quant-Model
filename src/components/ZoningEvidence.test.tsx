import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { ZoningPredictionOverview } from './Visuals';
import { canShowZoningChange, canShowZoningConfidence } from './zoningEvidence';

vi.mock('./PlotlyChart', () => ({ default: ({ data, ariaLabel }: any) => <div role="img" aria-label={ariaLabel} data-series={JSON.stringify(data)}/> }));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

const model = () => ({ trained: true, calibrated: true, synthetic_training: false, core: { confidence: .8, entropy: .3, abstain: false } });
const change = () => ({ trained: true, calibrated: true, synthetic_training: false, change_probability: .2 });
const feature = (properties: any) => ({ geometry: { coordinates: [103.8, 1.3] }, properties });
function response(data: any) { vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(data) }))); }

test('public numeric zoning fixtures never become probability charts', async () => {
  response({ status: 'synthetic_fixture_not_model', features: [feature({ name: 'Fictional asset', confidence: .86, entropy: .4, change_probability: .18, confidence_status: 'illustrative_uncalibrated', abstain: true })] });
  render(<ZoningPredictionOverview api="/api"/>);
  expect(await screen.findByText(/No eligible calibrated confidence/)).toBeInTheDocument();
  expect(screen.getByText(/No eligible calibrated zoning-change probabilities/)).toBeInTheDocument();
  expect(screen.queryByRole('img', { name: 'Available challenger confidence and entropy' })).not.toBeInTheDocument();
  expect(screen.queryByRole('img', { name: 'Available zoning change screening probabilities' })).not.toBeInTheDocument();
  expect(await screen.findByRole('img', { name: 'Supplied zoning discrepancy locations' })).toBeInTheDocument();
});

test('overview charts include only trained calibrated non-abstained estimates', async () => {
  const accepted = { prediction: model(), future_change: change() };
  response({ features: [feature(accepted), feature({ prediction: { ...model(), core: { confidence: .99, entropy: .1, abstain: true } }, future_change: { ...change(), calibrated: false } }), feature({ prediction: { ...model(), trained: false }, future_change: { ...change(), status: 'not_estimated' } })] });
  render(<ZoningPredictionOverview api="/api"/>);
  const confidence = await screen.findByRole('img', { name: 'Available challenger confidence and entropy' });
  const future = await screen.findByRole('img', { name: 'Available zoning change screening probabilities' });
  expect(JSON.parse(confidence.getAttribute('data-series')!)[0]).toMatchObject({ x: [.8], y: [.3] });
  expect(JSON.parse(future.getAttribute('data-series')!)[0].x).toEqual([.2]);
});

test('missing provenance, synthetic training and invalid probabilities remain unavailable', () => {
  expect(canShowZoningConfidence({ confidence: .86, entropy: .3, abstain: false })).toBe(false);
  expect(canShowZoningChange({ change_probability: .18 })).toBe(false);
  expect(canShowZoningConfidence({ prediction: { ...model(), synthetic_training: true } })).toBe(false);
  expect(canShowZoningChange({ future_change: { ...change(), synthetic_training: true } })).toBe(false);
  expect(canShowZoningConfidence({ prediction: { ...model(), core: { confidence: NaN, entropy: .3, abstain: false } } })).toBe(false);
  expect(canShowZoningChange({ future_change: { ...change(), change_probability: 1.1 } })).toBe(false);
  expect(canShowZoningConfidence({ prediction: model() }, { status: 'synthetic_fixture_not_model' })).toBe(false);
  expect(canShowZoningChange({ future_change: change() }, { status: 'synthetic_fixture_not_model' })).toBe(false);
});

test('existing challenger validation and calibration metadata can enable a real estimate', () => {
  const validated = { prediction: { model_validation: { status: 'validated' }, probability_calibration: { core: { temperature: 1.2, observations: 40 } }, synthetic_training: false, core: { confidence: .7, entropy: .5, abstain: false } } };
  expect(canShowZoningConfidence(validated)).toBe(true);
});
