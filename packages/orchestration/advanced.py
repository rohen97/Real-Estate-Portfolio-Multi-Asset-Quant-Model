from __future__ import annotations
from pathlib import Path
import math
from shapely.geometry import box, mapping
from packages.orchestration.engine import inputs_for_asset, zone_match
from packages.zoning.engine import calculate_capacity
from packages.zoning.envelope3d import EnvelopeInputs, generate_envelopes
from packages.zoning.viewshed import viewshed
from packages.zoning.ura import surrounding_development_context
from packages.actions.enbloc import EnBlocInputs, evaluate_enbloc
from packages.actions.detailed_cashflow import DetailedActionInputs, evaluate_detailed_action

ROOT = Path(__file__).resolve().parents[2]


def synthetic_site_polygon(latitude, longitude, area_sqm, aspect=1.5):
    width = math.sqrt(area_sqm * aspect)
    depth = area_sqm / width
    dx = width / (111320 * math.cos(math.radians(latitude))) / 2
    dy = depth / 110540 / 2
    return mapping(box(longitude - dx, latitude - dy, longitude + dx, latitude + dy))


def analyse_asset(asset):
    zoning, economics, notes, status, quality = inputs_for_asset(asset)
    notes = list(notes)
    observed = asset.get('observed_inputs') or {}
    capacity = calculate_capacity(zoning).__dict__
    polygon = synthetic_site_polygon(asset['latitude'], asset['longitude'], zoning.site_area_sqm, zoning.aspect_ratio)
    envelope = generate_envelopes(EnvelopeInputs(
        site_geojson=polygon, legal_gpr=zoning.legal_gpr, height_limit_m=zoning.height_max_m,
        site_coverage_max=zoning.site_coverage_max,
        setback_m=max(zoning.side_setback_m, zoning.front_setback_m), floor_to_floor_m=3.6))
    zone = zone_match(asset)
    context = surrounding_development_context(
        ROOT / 'data/processed/ura_mp2025.sqlite', asset['latitude'], asset['longitude'],
        500, zone.get('objectid') if zone else None)
    buildings = []
    for item in context.get('candidates', []):
        gpr = float(item.get('gpr') or 1.4)
        buildings.append({'id': item.get('objectid'), 'distance_m': max(1, item.get('distance_m', 1)),
                          'height_m': gpr * 12, 'width_m': min(100, max(15, item.get('width_m', 25))),
                          'dx_m': item.get('dx_m', 0), 'dy_m': item.get('dy_m', item.get('distance_m', 1))})
    view = viewshed(viewpoint_height_m=30, surrounding_buildings=buildings, current_value_m=economics.current_value_m)
    view['source_status'] = context.get('status', 'unknown')
    view['decision_ready'] = False
    view['interpretation'] = ('Heights and footprint are proxies; this is not a surveyed viewshed' if buildings
                              else 'Surrounding-building evidence is unavailable; zero obstruction is not evidence of open views')
    preferred = envelope.get('preferred') or {}
    approved = preferred.get('gross_gfa_sqm', 0.)
    segments = ' '.join(asset.get('segments', [])).lower()
    residential_share = observed.get('residential_share')
    if residential_share is None:
        residential_share = 1. if 'residential' in segments else 0.
        notes.append('Residential tax allocation inferred from segment; mixed-use allocation requires verification')
    common = dict(lbc_rate_per_sqm=observed.get('lbc_rate_per_sqm'),
                  assessed_lbc_m=observed.get('assessed_lbc_m'),
                  residential_share=residential_share,
                  # The footprint and planning envelope remain synthetic here.
                  inputs_verified=False)
    cash = evaluate_detailed_action(DetailedActionInputs(
        action='Redevelop', current_value_m=economics.current_value_m, current_noi_m=economics.current_noi_m,
        site_area_sqm=zoning.site_area_sqm, current_gfa_sqm=zoning.current_gfa_sqm,
        approved_gfa_sqm=approved, nla_efficiency=zoning.gross_to_net_efficiency,
        market_value_per_nla_sqm=zoning.completed_value_per_nla,
        construction_cost_per_gfa_sqm=zoning.construction_cost_per_gfa,
        approval_probability=zoning.approval_probability,
        tenant_relocation_m=economics.current_noi_m * .5,
        demolition_m=max(1, economics.current_value_m * .015), **common))
    cash['feasible_envelope'] = bool(preferred)
    if not preferred:
        # Existing floor area is not approval for rebuilding when the geometry
        # screen found no feasible replacement envelope.
        for key, value in list(cash.items()):
            if key.endswith('_m'):
                cash[key] = [] if isinstance(value, list) else None
        cash.update(irr_annual=None, valuation_status='not_evaluated_no_feasible_envelope',
                    npv_basis='No redevelopment valuation: physical screening found no feasible envelope',
                    decision_ready=False, verification_required=True)
        cash['decision_blockers'].insert(0, 'No feasible redevelopment envelope; existing GFA cannot substitute for approved replacement capacity')
    owners = observed.get('owners_count') or (120 if 'residential' in segments else 1)
    enbloc = evaluate_enbloc(EnBlocInputs(
        current_strata_value_m=economics.current_value_m, site_area_sqm=zoning.site_area_sqm,
        existing_gfa_sqm=zoning.current_gfa_sqm, legal_gpr=zoning.legal_gpr,
        nla_efficiency=zoning.gross_to_net_efficiency,
        sale_price_per_nla_sqm=zoning.completed_value_per_nla,
        construction_cost_per_gfa_sqm=zoning.construction_cost_per_gfa,
        tenure_remaining_years=(asset.get('tenure_hint') or {}).get('remaining_years'),
        owners_count=owners, required_consent=observed.get('required_consent', .8),
        observed_consent_share=observed.get('observed_consent_share'),
        tenant_cost_m=economics.current_noi_m * .5, **common))
    notes.append('Synthetic rectangular site, proxy heights and incomplete underwriting: advanced outputs are screening estimates')
    return {'asset_id': asset['asset_id'], 'input_status': status, 'input_quality': quality,
            'notes': notes, 'site_polygon': polygon, 'site_polygon_source': 'synthetic_rectangle',
            'capacity': capacity, 'development_envelope': envelope, 'viewshed': view,
            'enbloc': enbloc, 'redevelopment_cashflow': cash,
            'decision_ready': False, 'valuation_status': 'incomplete_inputs', 'verification_required': True}
