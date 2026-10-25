from __future__ import annotations

import argparse
import os
import random
import time as time_module
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import pandas as pd


API_ROOT = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CHUNK_DAYS = 7
REQUEST_PAUSE_SECONDS = 0.25
MAX_ATTEMPTS = 5


def request_rows(
    client: httpx.Client, dataset: str, params: dict[str, str]
) -> list[dict[str, Any]]:
    url = f"{API_ROOT}/{dataset}/stream"
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = client.get(url, params=params)
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == MAX_ATTEMPTS - 1:
                    response.raise_for_status()
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
                time_module.sleep(delay + random.uniform(0, 0.25))
                continue
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError(f"{dataset} returned {type(payload).__name__}, expected JSON array")
            if any(not isinstance(row, dict) for row in payload):
                raise ValueError(f"{dataset} returned a non-object row")
            return payload
        except (httpx.RequestError, httpx.HTTPStatusError):
            if attempt == MAX_ATTEMPTS - 1:
                raise
            time_module.sleep(2**attempt + random.uniform(0, 0.25))
    raise RuntimeError(f"Unable to fetch {dataset} after {MAX_ATTEMPTS} attempts")


def date_chunks(start: date, end: date):
    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=CHUNK_DAYS - 1), end)
        yield current, chunk_end
        current = chunk_end + timedelta(days=1)


def fetch_actuals(client: httpx.Client, start: date, end: date) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for chunk_start, chunk_end in date_chunks(start, end):
        rows.extend(
            request_rows(
                client,
                "FUELHH",
                {
                    "settlementDateFrom": chunk_start.isoformat(),
                    "settlementDateTo": chunk_end.isoformat(),
                    "fuelType": "WIND",
                },
            )
        )
        time_module.sleep(REQUEST_PAUSE_SECONDS)
    return rows


def fetch_forecasts(client: httpx.Client, start: date, end_exclusive: date) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    current = start
    while current < end_exclusive:
        chunk_end = min(current + timedelta(days=CHUNK_DAYS), end_exclusive)
        rows.extend(
            request_rows(
                client,
                "WINDFOR",
                {
                    "publishDateTimeFrom": datetime.combine(
                        current, time.min, timezone.utc
                    ).isoformat().replace("+00:00", "Z"),
                    "publishDateTimeTo": datetime.combine(
                        chunk_end, time.min, timezone.utc
                    ).isoformat().replace("+00:00", "Z"),
                },
            )
        )
        current = chunk_end
        time_module.sleep(REQUEST_PAUSE_SECONDS)
    return rows


def quality_report(
    actuals: pd.DataFrame,
    forecasts: pd.DataFrame,
    actual_duplicates: int,
    forecast_duplicates: int,
    expected_actual_points: int,
) -> str:
    actual_times = pd.to_datetime(actuals["startTime"], utc=True).sort_values()
    publish_times = pd.to_datetime(forecasts["publishTime"], utc=True).drop_duplicates().sort_values()
    start_times = pd.to_datetime(forecasts["startTime"], utc=True)
    unique_targets = start_times.drop_duplicates().sort_values()
    publish_values = pd.to_datetime(forecasts["publishTime"], utc=True)
    horizons = (start_times - publish_values).dt.total_seconds() / 3600
    gaps = actual_times.diff().dropna()
    gap_count = int((gaps != pd.Timedelta(value=30, unit="minutes")).astype(int).sum())
    publish_spacing = publish_times.diff().dropna().dt.total_seconds() / 60
    actual_coverage = 100 * len(actuals) / expected_actual_points if expected_actual_points else 0
    actual_null_generation = int(actuals["generation"].isna().sum())
    forecast_null_generation = int(forecasts["generation"].isna().sum())
    forecast_target_coverage = (
        100 * unique_targets.nunique() / expected_actual_points if expected_actual_points else 0
    )
    target_spacing = unique_targets.diff().dropna().dt.total_seconds() / 60
    return f"""# Data quality report

Generated from the Elexon BMRS API by `scripts/fetch_data.py`.

## Snapshot scope

- Actuals: FUELHH, `fuelType=WIND`, delivery target times {actual_times.min().isoformat()} to {actual_times.max().isoformat()} (UTC).
- Forecasts: WINDFOR, publish times {publish_values.min().isoformat()} to {publish_values.max().isoformat()} (UTC).
- Forecast target times retained: {start_times.min().isoformat()} to {start_times.max().isoformat()} (UTC).
- Data was restricted to delivery dates covered by the January 2026 decision window.

## Counts and data quality

- Actual rows: {len(actuals)}; duplicate rows removed: {actual_duplicates}.
- Actual rows with null generation: {actual_null_generation}.
- Actual half-hour gaps between consecutive retained points: {gap_count}.
- Actual coverage against expected half-hour slots: {actual_coverage:.2f}% ({len(actuals)}/{expected_actual_points}).
- Forecast rows: {len(forecasts)}; duplicate `(startTime, publishTime)` rows removed: {forecast_duplicates}.
- Forecast rows with null generation: {forecast_null_generation}.
- Unique forecast target times: {unique_targets.nunique()} ({forecast_target_coverage:.2f}% of expected half-hour targets); target spacing (minutes): min {target_spacing.min() if len(target_spacing) else float('nan'):.1f}, median {target_spacing.median() if len(target_spacing) else float('nan'):.1f}, max {target_spacing.max() if len(target_spacing) else float('nan'):.1f}.
- Unique forecast publish times: {publish_times.nunique()}.
- Forecast publish-time spacing (minutes): min {publish_spacing.min() if len(publish_spacing) else float('nan'):.1f}, median {publish_spacing.median() if len(publish_spacing) else float('nan'):.1f}, max {publish_spacing.max() if len(publish_spacing) else float('nan'):.1f}.
- Forecast horizon (startTime - publishTime, hours): min {horizons.min():.2f}, max {horizons.max():.2f}.

Forecast target resolution is taken as supplied by Elexon. Missing target points are retained as missing by the API; no interpolation or fabrication is performed.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch the January 2026 Elexon wind snapshot.")
    parser.add_argument("--decision-start", default=os.getenv("DECISION_START", "2026-01-01"))
    parser.add_argument("--decision-end", default=os.getenv("DECISION_END", "2026-01-31"))
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    args = parser.parse_args()
    decision_start = date.fromisoformat(args.decision_start)
    decision_end = date.fromisoformat(args.decision_end)
    if decision_start > decision_end:
        parser.error("--decision-start must be on or before --decision-end")

    delivery_start = decision_start + timedelta(days=1)
    delivery_end = decision_end + timedelta(days=1)
    publish_start = decision_start - timedelta(days=4)
    publish_end_exclusive = decision_end + timedelta(days=1)

    with httpx.Client(timeout=httpx.Timeout(60), follow_redirects=True) as client:
        actual_rows = fetch_actuals(client, delivery_start, delivery_end)
        forecast_rows = fetch_forecasts(client, publish_start, publish_end_exclusive)

    actuals = pd.DataFrame(actual_rows)
    forecasts = pd.DataFrame(forecast_rows)
    required_actual = {"startTime", "generation", "fuelType"}
    required_forecast = {"startTime", "publishTime", "generation"}
    if not required_actual.issubset(actuals.columns):
        raise ValueError(f"FUELHH is missing required fields: {required_actual - set(actuals.columns)}")
    if not required_forecast.issubset(forecasts.columns):
        raise ValueError(
            f"WINDFOR is missing required fields: {required_forecast - set(forecasts.columns)}"
        )

    actuals = actuals.loc[actuals["fuelType"] == "WIND"].copy()
    actuals["startTime"] = pd.to_datetime(actuals["startTime"], utc=True)
    actuals = actuals.loc[
        (actuals["startTime"] >= pd.Timestamp(delivery_start, tz="UTC"))
        & (actuals["startTime"] < pd.Timestamp(delivery_end + timedelta(days=1), tz="UTC"))
    ]
    forecasts["startTime"] = pd.to_datetime(forecasts["startTime"], utc=True)
    forecasts["publishTime"] = pd.to_datetime(forecasts["publishTime"], utc=True)
    target_start = pd.Timestamp(delivery_start, tz="UTC")
    target_end = pd.Timestamp(delivery_end + timedelta(days=1), tz="UTC")
    forecasts = forecasts.loc[
        (forecasts["startTime"] >= target_start)
        & (forecasts["startTime"] < target_end)
        & (forecasts["publishTime"] < pd.Timestamp(publish_end_exclusive, tz="UTC"))
    ].copy()

    actual_duplicates = int(actuals.duplicated(subset=["startTime"], keep="last").sum())
    forecast_duplicates = int(
        forecasts.duplicated(subset=["startTime", "publishTime"], keep="last").sum()
    )
    actuals = actuals.drop_duplicates(subset=["startTime"], keep="last").sort_values("startTime")
    forecasts = forecasts.drop_duplicates(
        subset=["startTime", "publishTime"], keep="last"
    ).sort_values(["startTime", "publishTime"])
    actuals = actuals[["startTime", "generation"]]
    forecasts = forecasts[["startTime", "publishTime", "generation"]]

    args.data_dir.mkdir(parents=True, exist_ok=True)
    actuals.to_csv(args.data_dir / "actuals.csv", index=False, date_format="%Y-%m-%dT%H:%M:%SZ")
    forecasts.to_csv(
        args.data_dir / "forecasts.csv", index=False, date_format="%Y-%m-%dT%H:%M:%SZ"
    )
    expected_slots = ((delivery_end - delivery_start).days + 1) * 48
    report = quality_report(
        actuals, forecasts, actual_duplicates, forecast_duplicates, expected_slots
    )
    (args.data_dir / "data_quality.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
