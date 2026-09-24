from __future__ import annotations

from datetime import date
from hashlib import sha256
from math import exp
from typing import Any

import numpy as np

GENERATOR_VERSION = "semi-synthetic-twin-0.3.0"
CURRENT_YEAR = 2026

SEGMENT_PROFILES: dict[str, dict[str, float]] = {
    "Residential": {
        "site_area_sqm": 950,
        "gpr": 2.1,
        "efficiency": 0.82,
        "rent_psm_pa": 720,
        "value_psm": 17500,
        "occupancy": 0.95,
        "expense_ratio": 0.24,
        "cap_rate": 0.032,
        "construction_cost_psm": 4600,
    },
    "Commercial": {
        "site_area_sqm": 4200,
        "gpr": 4.2,
        "efficiency": 0.78,
        "rent_psm_pa": 980,
        "value_psm": 15500,
        "occupancy": 0.90,
        "expense_ratio": 0.31,
        "cap_rate": 0.043,
        "construction_cost_psm": 4300,
    },
    "Mall": {
        "site_area_sqm": 8500,
        "gpr": 3.5,
        "efficiency": 0.68,
        "rent_psm_pa": 1180,
        "value_psm": 16500,
        "occupancy": 0.92,
        "expense_ratio": 0.36,
        "cap_rate": 0.047,
        "construction_cost_psm": 4800,
    },
    "Hotel": {
        "site_area_sqm": 5200,
        "gpr": 4.2,
        "efficiency": 0.72,
        "rent_psm_pa": 860,
        "value_psm": 14000,
        "occupancy": 0.82,
        "expense_ratio": 0.48,
        "cap_rate": 0.052,
        "construction_cost_psm": 5200,
    },
    "Serviced Residence": {
        "site_area_sqm": 3200,
        "gpr": 3.2,
        "efficiency": 0.76,
        "rent_psm_pa": 900,
        "value_psm": 15000,
        "occupancy": 0.86,
        "expense_ratio": 0.39,
        "cap_rate": 0.046,
        "construction_cost_psm": 4900,
    },
    "Self-Storage": {
        "site_area_sqm": 3600,
        "gpr": 2.5,
        "efficiency": 0.84,
        "rent_psm_pa": 520,
        "value_psm": 7500,
        "occupancy": 0.88,
        "expense_ratio": 0.28,
        "cap_rate": 0.058,
        "construction_cost_psm": 2900,
    },
}


def stable_seed(asset_id: str, master_seed: int = 20260924) -> int:
    digest = sha256(f"{GENERATOR_VERSION}|{master_seed}|{asset_id}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % (2**32 - 1)


def segment_group(asset: dict[str, Any]) -> str:
    text = " ".join(asset.get("segments") or []).lower()
    if "storage" in text:
        return "Self-Storage"
    if "serviced" in text:
        return "Serviced Residence"
    if "hotel" in text:
        return "Hotel"
    if "mall" in text or "retail" in text:
        return "Mall"
    if "commercial" in text or "industrial" in text or "medical" in text:
        return "Commercial"
    return "Residential"


def zone_match(asset: dict[str, Any]) -> dict[str, Any]:
    return (asset.get("ura_zoning", {}).get("matches") or [{}])[0]


def bounded(value: float, low: float, high: float) -> float:
    return float(np.clip(value, low, high))


def score_0_100(value: float) -> float:
    return round(bounded(value, 0, 100), 2)


def _real_context(asset: dict[str, Any], zone: dict[str, Any]) -> dict[str, Any]:
    return {
        "asset_id": asset["asset_id"],
        "name": asset.get("name"),
        "address": asset.get("address"),
        "country": asset.get("country"),
        "segment": segment_group(asset),
        "source_segments": asset.get("segments") or [],
        "latitude": asset.get("latitude"),
        "longitude": asset.get("longitude"),
        "size_from_sqft": asset.get("size_from_sqft"),
        "asking_rent_monthly_sgd": asset.get("asking_rent_monthly_sgd"),
        "planning_area": zone.get("planning_area") or "Unknown",
        "subzone": zone.get("subzone") or "Unknown",
        "ura_land_use": zone.get("lu_desc") or zone.get("lu_text") or "Unknown",
        "ura_gpr": zone.get("gpr"),
        "ura_height_max": zone.get("height_max"),
        "zoning_exception": asset.get("zoning_exception"),
    }


def _make_financial_history(asset_id: str, underwriting: dict[str, float], rng: np.random.Generator) -> list[dict[str, Any]]:
    years = list(range(CURRENT_YEAR - 11, CURRENT_YEAR + 1))
    cycle = np.array([-0.012, 0.004, 0.018, 0.028, 0.015, -0.035, 0.008, 0.031, 0.024, -0.006, 0.013])
    current_noi = underwriting["noi_m"]
    current_value = underwriting["valuation_m"]
    current_occupancy = underwriting["occupancy"]
    current_cap_rate = underwriting["cap_rate"]
    growth = 0.018 + rng.normal(0, 0.005)
    rows: list[dict[str, Any]] = []
    for index, year in enumerate(years):
        distance = CURRENT_YEAR - year
        if distance:
            historical_growth = growth + cycle[max(0, len(cycle) - distance) :].mean() if distance <= len(cycle) else growth
        else:
            historical_growth = growth
        noi = current_noi / ((1 + historical_growth) ** distance)
        noi *= 1 + rng.normal(0, 0.025)
        occupancy = bounded(current_occupancy - 0.002 * distance + rng.normal(0, 0.018), 0.62, 0.995)
        cap_rate = bounded(current_cap_rate + 0.0005 * distance + rng.normal(0, 0.002), 0.022, 0.09)
        valuation = max(noi / cap_rate, current_value / ((1.018 + rng.normal(0, 0.004)) ** distance))
        rows.append(
            {
                "Asset ID": asset_id,
                "Fiscal Year": year,
                "NOI SGD m": round(noi, 4),
                "Occupancy %": round(occupancy, 4),
                "Cap Rate %": round(cap_rate, 4),
                "Maintenance Capex SGD m": round(valuation * bounded(rng.normal(0.009, 0.002), 0.003, 0.02), 4),
                "Valuation SGD m": round(valuation, 4),
                "Synthetic": True,
                "Generator Version": GENERATOR_VERSION,
            }
        )
    return rows


def _make_leases(asset_id: str, underwriting: dict[str, float], segment: str, rng: np.random.Generator) -> list[dict[str, Any]]:
    tenant_count = 1 if segment == "Residential" else int(rng.integers(5, 14))
    shares = rng.dirichlet(np.ones(tenant_count) * (2.5 if tenant_count > 1 else 1))
    annual_gross_rent = underwriting["gross_rent_m"] * 1_000_000
    leases = []
    grades = ["A", "A-", "BBB", "BBB-", "BB+"]
    for index, share in enumerate(shares):
        expiry_year = int(rng.integers(CURRENT_YEAR + 1, CURRENT_YEAR + 8))
        expiry_month = int(rng.integers(1, 13))
        leases.append(
            {
                "Asset ID": asset_id,
                "Tenant ID": f"SYN-{index + 1:02d}",
                "Area sqm": round(underwriting["nla_sqm"] * float(share), 2),
                "Passing Rent SGD pa": round(annual_gross_rent * float(share), 2),
                "Market Rent SGD pa": round(annual_gross_rent * float(share) * bounded(rng.normal(1.035, 0.06), 0.85, 1.25), 2),
                "Lease Expiry": f"{expiry_year:04d}-{expiry_month:02d}-28",
                "Tenant Credit Grade": str(rng.choice(grades, p=[0.22, 0.24, 0.3, 0.16, 0.08])),
                "Collection %": round(bounded(rng.normal(0.985, 0.015), 0.88, 1), 4),
                "Synthetic": True,
            }
        )
    return leases


def _make_capex_history(asset_id: str, valuation_m: float, rng: np.random.Generator) -> list[dict[str, Any]]:
    categories = ["Lifecycle replacement", "Energy efficiency", "Tenant works", "Facade and public realm"]
    projects = []
    for index in range(4):
        year = int(rng.integers(CURRENT_YEAR - 8, CURRENT_YEAR + 1))
        budget = valuation_m * bounded(rng.normal(0.012, 0.006), 0.002, 0.04)
        overrun = bounded(rng.normal(1.07, 0.12), 0.82, 1.45)
        projects.append(
            {
                "Asset ID": asset_id,
                "Project": categories[index],
                "Year": year,
                "Budget SGD m": round(budget, 4),
                "Actual SGD m": round(budget * overrun, 4),
                "Delay Months": int(max(0, round(rng.normal(2.5, 3)))),
                "Synthetic": True,
            }
        )
    return sorted(projects, key=lambda item: item["Year"])


def generate_twin(asset: dict[str, Any], master_seed: int = 20260924) -> dict[str, Any]:
    seed = stable_seed(asset["asset_id"], master_seed)
    rng = np.random.default_rng(seed)
    segment = segment_group(asset)
    profile = SEGMENT_PROFILES[segment]
    zone = zone_match(asset)
    context = _real_context(asset, zone)
    location_factor = bounded(0.82 + (stable_seed(context["planning_area"], 17) % 1000) / 2500 + rng.normal(0, 0.035), 0.78, 1.28)
    gpr = float(zone.get("gpr") or profile["gpr"])
    observed_size_sqm = float(asset.get("size_from_sqft") or 0) * 0.092903
    if observed_size_sqm > 0:
        nla_sqm = max(35.0, observed_size_sqm)
        current_gfa_sqm = nla_sqm / profile["efficiency"]
        site_area_sqm = current_gfa_sqm / max(0.6, gpr * bounded(rng.normal(0.76, 0.08), 0.55, 0.94))
    else:
        site_area_sqm = profile["site_area_sqm"] * float(rng.lognormal(0, 0.38))
        current_gfa_sqm = site_area_sqm * gpr * bounded(rng.normal(0.73, 0.09), 0.5, 0.94)
        nla_sqm = current_gfa_sqm * profile["efficiency"]
    approved_gfa_sqm = site_area_sqm * gpr * bounded(rng.normal(0.92, 0.035), 0.82, 1.0)
    occupancy = bounded(profile["occupancy"] + rng.normal(0, 0.035), 0.68, 0.99)
    expense_ratio = bounded(profile["expense_ratio"] + rng.normal(0, 0.035), 0.16, 0.58)
    rent_psm_pa = profile["rent_psm_pa"] * location_factor * bounded(rng.normal(1, 0.09), 0.75, 1.28)
    observed_asking_rent = asset.get("asking_rent_monthly_sgd")
    gross_rent_m = (
        float(observed_asking_rent) * 12 / 1_000_000
        if observed_asking_rent
        else nla_sqm * rent_psm_pa / 1_000_000
    )
    noi_m = gross_rent_m * occupancy * (1 - expense_ratio)
    cap_rate = bounded(profile["cap_rate"] + (1 - location_factor) * 0.008 + rng.normal(0, 0.0025), 0.025, 0.075)
    direct_value = nla_sqm * profile["value_psm"] * location_factor / 1_000_000
    valuation_m = max(noi_m / cap_rate, direct_value * 0.9)
    valuation_m *= bounded(rng.normal(1, 0.045), 0.88, 1.14)
    debt_m = valuation_m * bounded(rng.normal(0.43, 0.1), 0.12, 0.68)
    maintenance_capex_m = valuation_m * bounded(rng.normal(0.009, 0.002), 0.003, 0.02)
    age_years = int(rng.integers(6, 48))
    energy_intensity = bounded(125 + age_years * 2.1 + rng.normal(0, 25), 85, 310)
    remaining_tenure = int(rng.choice([45, 60, 75, 88, 999], p=[0.08, 0.15, 0.22, 0.35, 0.2]))
    current_utilisation = current_gfa_sqm / max(1, site_area_sqm * gpr)
    capacity_gap = max(0, approved_gfa_sqm - current_gfa_sqm)
    redevelopment_score = score_0_100(20 + 95 * (1 - current_utilisation) + 0.45 * (age_years - 15) + 10 * (location_factor - 1))
    operational_score = score_0_100(45 + 70 * (occupancy - 0.7) - 45 * (expense_ratio - 0.25))
    market_score = score_0_100(50 + 55 * (location_factor - 0.85) + 8 * (gpr - 2.1))
    sustainability_score = score_0_100(100 - (energy_intensity - 85) / 2.25)
    yield_score = score_0_100((noi_m / max(valuation_m, 0.1) - 0.018) / (0.07 - 0.018) * 100)
    financial_score = score_0_100(0.75 * yield_score + 0.25 * (occupancy * 100))
    underwriting = {
        "site_area_sqm": round(site_area_sqm, 2),
        "current_gfa_sqm": round(current_gfa_sqm, 2),
        "approved_gfa_sqm": round(approved_gfa_sqm, 2),
        "nla_sqm": round(nla_sqm, 2),
        "nla_efficiency": profile["efficiency"],
        "valuation_m": round(valuation_m, 4),
        "gross_rent_m": round(gross_rent_m, 4),
        "noi_m": round(noi_m, 4),
        "occupancy": round(occupancy, 4),
        "expense_ratio": round(expense_ratio, 4),
        "cap_rate": round(cap_rate, 5),
        "debt_m": round(debt_m, 4),
        "maintenance_capex_m": round(maintenance_capex_m, 4),
        "rent_psm_pa": round(rent_psm_pa, 2),
        "market_value_per_nla_sqm": round(profile["value_psm"] * location_factor, 2),
        "construction_cost_per_gfa_sqm": profile["construction_cost_psm"],
        "remaining_tenure_years": remaining_tenure,
        "building_age_years": age_years,
        "energy_intensity_kwh_sqm": round(energy_intensity, 2),
        "capacity_gap_sqm": round(capacity_gap, 2),
    }
    legacy_inputs = {
        "financial": financial_score,
        "operational": operational_score,
        "market": market_score,
        "sustainability": sustainability_score,
    }
    real_fields = [
        field
        for field, value in context.items()
        if field not in {"zoning_exception"} and value not in (None, "", "Unknown", [])
    ]
    synthetic_fields = list(underwriting.keys())
    provenance = {field: {"status": "real_portfolio_anchor", "source": "Far East portfolio / URA MP2025"} for field in real_fields}
    provenance.update(
        {
            field: {
                "status": "synthetic",
                "source": GENERATOR_VERSION,
                "replace_with": "verified company underwriting",
            }
            for field in synthetic_fields
        }
    )
    financials = _make_financial_history(asset["asset_id"], underwriting, rng)
    leases = _make_leases(asset["asset_id"], underwriting, segment, rng)
    capex = _make_capex_history(asset["asset_id"], valuation_m, rng)
    latent = {
        "location_factor": round(location_factor, 5),
        "execution_quality": round(bounded(rng.normal(0.62, 0.18), 0.12, 0.95), 5),
        "market_mismatch": round(bounded(rng.beta(2.1, 3.0), 0.02, 0.95), 5),
        "redevelopment_score": redevelopment_score,
        "operational_gap": round(100 - operational_score, 2),
        "sustainability_gap": round(100 - sustainability_score, 2),
    }
    return {
        "asset_id": asset["asset_id"],
        "name": asset.get("name"),
        "generator": {
            "version": GENERATOR_VERSION,
            "seed": seed,
            "generated_on": date.today().isoformat(),
            "status": "synthetic_software_validation",
        },
        "real_context": context,
        "underwriting": underwriting,
        "legacy_inputs": legacy_inputs,
        "histories": {
            "financials": financials,
            "leases": leases,
            "capex": capex,
            "planning": [
                {
                    "Asset ID": asset["asset_id"],
                    "Year": CURRENT_YEAR - 2,
                    "Event": "Synthetic pre-application capacity review",
                    "Outcome": "Conditional",
                    "Synthetic": True,
                }
            ],
        },
        "field_provenance": provenance,
        "completeness": {
            "real_context_fields": len(real_fields),
            "real_context_possible": 14,
            "real_context_pct": round(len(real_fields) / 14, 4),
            "verified_underwriting_pct": 0.0,
            "synthetic_underwriting_fields": len(synthetic_fields),
        },
        "latent_simulation_truth": latent,
    }


def generate_portfolio_twins(portfolio: list[dict[str, Any]], master_seed: int = 20260924) -> list[dict[str, Any]]:
    return [
        generate_twin(asset, master_seed)
        for asset in portfolio
        if asset.get("country") == "Singapore" and asset.get("latitude") is not None
    ]
