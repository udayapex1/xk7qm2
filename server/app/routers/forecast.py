from __future__ import annotations

from datetime import date, datetime

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from server.app.config import settings
from server.app.routers.common import check_delivery_date, parse_cutoff, store
from server.app.schemas import (
    ForecastResponse,
    ForecastRow,
    Metrics,
    VintageRow,
    VintagesResponse,
)
from server.app.services.forecast import (
    decision_cutoff,
    expected_forecast_targets,
    horizon_hours,
    latest_available,
)
from server.app.services.metrics import calculate_metrics, paired_errors


router = APIRouter(prefix="/api", tags=["forecast"])


def json_value(value):
    """Convert pandas nulls and scalar wrappers to JSON-compatible values."""
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if hasattr(value, "item"):
        return value.item()
    return value


@router.get("/forecast", response_model=ForecastResponse)
def get_forecast(
    delivery_date: date,
    cutoff: str | None = Query(default=None, description="Decision cutoff in Europe/London, HH:MM."),
) -> ForecastResponse:
    """Return the latest D-1 eligible forecast at every expected half-hour point."""
    check_delivery_date(delivery_date)
    cutoff_time = parse_cutoff(cutoff)
    frame = latest_available(store, delivery_date, cutoff_time, settings.timezone)
    rows = [
        ForecastRow(
            start_time=row.startTime.to_pydatetime(),
            actual_mw=json_value(row.actual),
            forecast_mw=json_value(row.generation),
            publish_time=json_value(row.publishTime),
            horizon_hours=json_value(row.horizon_hours),
            error_mw=json_value(row.error),
            forecast_missing=pd.isna(row.generation),
        )
        for row in frame.itertuples(index=False)
    ]
    errors, actuals = paired_errors(frame)
    metrics = calculate_metrics(
        errors,
        actuals,
        expected_count=len(expected_forecast_targets(delivery_date, settings.timezone)),
    )
    return ForecastResponse(
        delivery_date=delivery_date,
        cutoff_timestamp=decision_cutoff(delivery_date, cutoff_time, settings.timezone).to_pydatetime(),
        cutoff_timezone=settings.timezone_name,
        rows=rows,
        summary=Metrics(**metrics),
    )


@router.get("/forecast/vintages", response_model=VintagesResponse)
def get_forecast_vintages(
    target_time: datetime = Query(description="Target timestamp; an ISO-8601 timestamp with timezone."),
    cutoff: str | None = Query(default=None, description="Decision cutoff in Europe/London, HH:MM."),
) -> VintagesResponse:
    """Return all stored forecast vintages for one timestamp with cutoff eligibility flags."""
    if target_time.tzinfo is None or target_time.utcoffset() is None:
        raise HTTPException(status_code=422, detail="target_time must include a timezone (ISO-8601).")
    target_utc = pd.Timestamp(target_time).tz_convert("UTC")
    delivery_date = target_utc.to_pydatetime().astimezone(settings.timezone).date()
    check_delivery_date(delivery_date)
    cutoff_time = parse_cutoff(cutoff)
    cutoff_timestamp = decision_cutoff(delivery_date, cutoff_time, settings.timezone)
    vintages = store.forecast_vintages(target_utc).sort_values("publishTime")
    eligible = vintages.loc[vintages["publishTime"] <= cutoff_timestamp]
    latest_publish = eligible["publishTime"].max() if not eligible.empty else None
    rows = [
        VintageRow(
            start_time=row.startTime.to_pydatetime(),
            publish_time=row.publishTime.to_pydatetime(),
            generation_mw=float(row.generation),
            horizon_hours=horizon_hours(row.startTime, row.publishTime),
            latest_available_at_cutoff=row.publishTime == latest_publish,
            cutoff_timestamp=cutoff_timestamp.to_pydatetime(),
        )
        for row in vintages.itertuples(index=False)
    ]
    return VintagesResponse(
        target_time=target_utc.to_pydatetime(),
        delivery_date=delivery_date,
        cutoff_timestamp=cutoff_timestamp.to_pydatetime(),
        selection_rule="Maximum publish_time <= the D-1 cutoff; forecasts published later are ineligible.",
        forecasts=rows,
    )
