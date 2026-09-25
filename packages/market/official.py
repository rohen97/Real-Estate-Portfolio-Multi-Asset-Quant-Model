"""Auditable quarterly public indices; market context, never asset-level alpha."""
from __future__ import annotations
from datetime import date
import calendar
import math
import re

DATASETS = {
    "residential_price": {"id": "d_da00b36ca8c831322fa0bb2a3378a476", "agency": "URA via SingStat", "rows": {"Residential Properties": ("private_residential", "price")}},
    "residential_rent": {"id": "d_647dabde09e726b9eeb75e4d9cd96699", "agency": "URA via SingStat", "rows": {"Rental Index Of Residential Properties": ("private_residential", "rent")}},
    "commercial_price": {"id": "d_620ad30cf4aca7c1c25eb2eff9e4bedc", "agency": "URA via SingStat", "rows": {"Office Space In Central Region": ("office", "price"), "Retail Space In Central Region": ("retail", "price")}},
    "commercial_rent": {"id": "d_862c74b13138382b9f0c50c68d436b95", "agency": "URA", "rows": {"office": ("office", "rent"), "retail": ("retail", "rent")}, "long": True},
    "industrial_price": {"id": "d_dce35e6697eadb9884f2e02af764e468", "agency": "JTC via SingStat", "rows": {"All Industrial": ("industrial", "price")}},
    "industrial_rent": {"id": "d_37e46b203bb77387328d25882247d000", "agency": "JTC via SingStat", "rows": {"All Industrial": ("industrial", "rent")}},
}

def quarter_id(value: str) -> int | None:
    text = re.sub(r"[\s_-]", "", str(value)).upper()
    match = re.fullmatch(r"(\d{4})(?:Q([1-4])|([1-4])Q)", text)
    return int(match[1]) * 4 + int(match[2] or match[3]) - 1 if match else None

def quarter_label(quarter: int) -> str:
    return f"{quarter // 4}-Q{quarter % 4 + 1}"

def quarter_end(quarter: int) -> date:
    month = (quarter % 4 + 1) * 3
    return date(quarter // 4, month, calendar.monthrange(quarter // 4, month)[1])

def _level(value):
    try:
        number = float(value)
        return number if math.isfinite(number) and number > 0 else None
    except (ValueError, TypeError):
        return None

def parse_dataset(payload: dict, spec: dict, as_of: date) -> list[dict]:
    result = payload.get("result", {})
    rows = result.get("records", [])
    if not payload.get("success") or not rows or result.get("total", len(rows)) > len(rows):
        raise ValueError("Incomplete or unsuccessful official-data response")
    series = {}
    for row in rows:
        label = str(row.get("property_type" if spec.get("long") else "DataSeries", "")).strip()
        if label not in spec["rows"]:
            continue
        observations = [(row.get("quarter"), row.get("index"))] if spec.get("long") else row.items()
        values = series.setdefault(label, {})
        for period, raw in observations:
            quarter, level = quarter_id(period), _level(raw)
            if quarter is None or level is None or quarter_end(quarter) > as_of:
                continue
            if quarter in values and values[quarter] != level:
                raise ValueError(f"Conflicting observations for {label} {quarter_label(quarter)}")
            values[quarter] = level
    output = []
    for label, (segment, measure) in spec["rows"].items():
        values = series.get(label, {})
        if not values:
            raise ValueError(f"Missing required series: {label}")
        output.append({"segment": segment, "measure": measure, "series_label": label,
                       "dataset_id": spec["id"], "agency": spec["agency"],
                       "source_url": f"https://data.gov.sg/datasets/{spec['id']}/view",
                       "observations": [{"period": quarter_label(q), "index": values[q]} for q in sorted(values)]})
    return output

def build_snapshot(series: list[dict], as_of: date, provenance: dict) -> dict:
    indicators, latest_dates = {}, []
    for item in series:
        values = {quarter_id(row["period"]): row["index"] for row in item["observations"]}
        values = {q: v for q, v in values.items() if q is not None and quarter_end(q) <= as_of}
        if not values:
            continue
        quarter = max(values)
        current, end = values[quarter], quarter_end(quarter)
        latest_dates.append(end)
        measure = item["measure"]
        segment = indicators.setdefault(item["segment"], {"series": {}, "geographic_scope": "Central Region" if item["segment"] in ("office", "retail") else "Singapore"})
        segment.update({f"{measure}_index": current,
                        f"{measure}_qoq": current / values[quarter - 1] - 1 if quarter - 1 in values else None,
                        f"{measure}_yoy": current / values[quarter - 4] - 1 if quarter - 4 in values else None,
                        f"{measure}_period": quarter_label(quarter)})
        segment["series"][measure] = {"source_url": item["source_url"], "dataset_id": item["dataset_id"],
                                      "agency": item["agency"], "observations": len(values),
                                      "period_end": end.isoformat(), "age_days": (as_of - end).days,
                                      "stale": (as_of - end).days > 180}
        segment["period"] = segment.get("price_period", segment.get("rent_period"))
        segment["status"] = "stale" if any(x["stale"] for x in segment["series"].values()) else "official_context"
    return {"schema_version": "2.0", "status": "official_context" if indicators else "unavailable",
            "as_of": max(latest_dates).isoformat() if latest_dates else None, "evaluated_at": as_of.isoformat(),
            "market_indicators": indicators, "provenance": provenance, "history": series,
            "warning": "Published, potentially revised national/regional indices. Not point-in-time investment backtests, asset underwriting, or alpha. Missing quarters are not interpolated."}
