from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from server.app.config import settings
from server.app.routers.common import parse_cutoff, store
from server.app.schemas import (
    AccuracySummary,
    BucketMetrics,
    ByHourResponse,
    DailyAccuracyResponse,
    DailyMetrics,
    DistributionResponse,
    HistogramBin,
    HourMetrics,
    HorizonAccuracyResponse,
    Metrics,
    WindLevelAccuracyResponse,
    WindLevelBucket,
)
from server.app.services.forecast import (
    delivery_window,
    expected_forecast_targets,
    expected_targets,
    latest_available,
)
from server.app.services.metrics import calculate_metrics, paired_errors


router = APIRouter(prefix="/api/accuracy", tags=["accuracy"])


def dates_in_range(start_date: date, end_date: date) -> list[date]:
    """Validate an inclusive delivery-date range against the configured window."""
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="start must be on or before end.")
    if start_date < settings.first_delivery_date or end_date > settings.last_delivery_date:
        raise HTTPException(
            status_code=422,
            detail=(
                f"start and end must be within {settings.first_delivery_date.isoformat()} "
                f"through {settings.last_delivery_date.isoformat()}."
            ),
        )
    count = (end_date - start_date).days
    return [start_date + timedelta(days=offset) for offset in range(count + 1)]


def selected_frame(days: list[date], cutoff) -> pd.DataFrame:
    """Build the decision-time, latest-vintage frame for a list of delivery days."""
    frames = []
    for delivery_date in days:
        frame = latest_available(store, delivery_date, cutoff, settings.timezone)
        frame["delivery_date"] = delivery_date
        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def frame_metrics(
    frame: pd.DataFrame, expected_count: int, coverage_count: int | None = None
) -> Metrics:
    """Calculate metrics with coverage measured against hourly forecast-grid points."""
    errors, actuals = paired_errors(frame)
    return Metrics(
        **calculate_metrics(
            errors, actuals, expected_count=expected_count, coverage_count=coverage_count
        )
    )


@router.get(
    "/summary",
    response_model=AccuracySummary,
    description="Decision-time accuracy using the latest forecast available at the D-1 cutoff; evaluated on the hourly forecast grid.",
)
def accuracy_summary(
    start: date = Query(default=settings.first_delivery_date),
    end: date = Query(default=settings.last_delivery_date),
    cutoff: str | None = Query(default=None, description="Decision cutoff in Europe/London, HH:MM."),
) -> AccuracySummary:
    """Report decision-time accuracy using the latest vintage available at cutoff."""
    days = dates_in_range(start, end)
    cutoff_time = parse_cutoff(cutoff)
    frame = selected_frame(days, cutoff_time)
    expected_count = sum(len(expected_forecast_targets(day, settings.timezone)) for day in days)
    return AccuracySummary(
        start_date=start,
        end_date=end,
        cutoff=cutoff_time.strftime("%H:%M"),
        cutoff_timezone=settings.timezone_name,
        evaluation_grid="Hourly forecast targets; half-hour timestamps without a forecast are returned as null and excluded from metrics.",
        metrics=frame_metrics(frame, expected_count),
    )


@router.get(
    "/by-horizon",
    response_model=HorizonAccuracyResponse,
    description="All-vintage accuracy by forecast horizon. This is not decision-time accuracy.",
)
def accuracy_by_horizon() -> HorizonAccuracyResponse:
    """Report all-vintage accuracy by horizon, separate from decision-time summary."""
    start, _ = delivery_window(settings.first_delivery_date, settings.timezone)
    _, end = delivery_window(settings.last_delivery_date, settings.timezone)
    forecasts = store.forecasts_for(start, end)
    actuals = store.actuals_for(start, end)[["startTime", "generation"]].rename(
        columns={"generation": "actual"}
    )
    paired = forecasts.merge(actuals, on="startTime", how="left")
    paired["error"] = paired["generation"] - paired["actual"]
    paired["horizon"] = (
        (paired["startTime"] - paired["publishTime"]).dt.total_seconds() / 3600
    )
    boundaries = (0, 6, 12, 24, 36, 48, float("inf"))
    labels = ("0-6h", "6-12h", "12-24h", "24-36h", "36-48h", "48h+")
    paired["bucket"] = pd.cut(
        paired["horizon"], bins=boundaries, labels=labels, right=False, include_lowest=True
    )
    result = []
    days = dates_in_range(settings.first_delivery_date, settings.last_delivery_date)
    expected_grid = set(
        target
        for day in days
        for target in expected_forecast_targets(day, settings.timezone)
    )
    expected_count = len(expected_grid)

    def vintage_metrics(group: pd.DataFrame) -> Metrics:
        """Measure unique target coverage for a vintage-horizon bucket."""
        evaluated_targets = group.dropna(subset=["generation", "actual"])["startTime"].nunique()
        return frame_metrics(group, expected_count, coverage_count=evaluated_targets)

    if (paired["horizon"] < 0).any():
        negative = paired.loc[paired["horizon"] < 0]
        result.append(
            BucketMetrics(
                bucket="<0h",
                metrics=vintage_metrics(negative),
            )
        )
    for label in labels:
        group = paired.loc[paired["bucket"] == label]
        if not group.empty:
            result.append(BucketMetrics(bucket=label, metrics=vintage_metrics(group)))
    return HorizonAccuracyResponse(
        scope="All retained WINDFOR vintages joined to actuals by exact UTC startTime; this is not decision-time accuracy.",
        coverage_definition="Unique evaluated target timestamps represented in this horizon bucket / expected hourly forecast-grid points in the configured window. A target may appear in multiple horizon buckets.",
        buckets=result,
    )


@router.get(
    "/by-hour",
    response_model=ByHourResponse,
    description="Decision-time accuracy using the latest forecast available at the D-1 cutoff.",
)
def accuracy_by_hour(
    cutoff: str | None = Query(default=None, description="Decision cutoff in Europe/London, HH:MM."),
) -> ByHourResponse:
    """Break down decision-time accuracy by UTC and local target hour."""
    cutoff_time = parse_cutoff(cutoff)
    days = dates_in_range(settings.first_delivery_date, settings.last_delivery_date)
    frame = selected_frame(days, cutoff_time)
    utc_hours = frame["startTime"].dt.hour
    local_hours = frame["startTime"].dt.tz_convert(settings.timezone).dt.hour
    expected_utc_by_hour = {hour: 0 for hour in range(24)}
    expected_local_by_hour = {hour: 0 for hour in range(24)}
    for day in days:
        for target in expected_forecast_targets(day, settings.timezone):
            expected_utc_by_hour[target.hour] += 1
            expected_local_by_hour[target.tz_convert(settings.timezone).hour] += 1

    def hour_metrics(hour_values: pd.Series, expected_by_hour: dict[int, int]) -> list[HourMetrics]:
        """Calculate hourly metrics against the expected hourly target count."""
        rows = []
        for hour in range(24):
            group = frame.loc[hour_values == hour]
            denominator = expected_by_hour[hour]
            if denominator:
                rows.append(HourMetrics(hour=hour, metrics=frame_metrics(group, denominator)))
        return rows

    return ByHourResponse(
        cutoff=cutoff_time.strftime("%H:%M"),
        utc=hour_metrics(utc_hours, expected_utc_by_hour),
        local=hour_metrics(local_hours, expected_local_by_hour),
    )


@router.get(
    "/daily",
    response_model=DailyAccuracyResponse,
    description="Decision-time accuracy using the latest forecast available at the D-1 cutoff.",
)
def accuracy_daily(
    cutoff: str | None = Query(default=None, description="Decision cutoff in Europe/London, HH:MM."),
) -> DailyAccuracyResponse:
    """Return decision-time metrics for each delivery day."""
    cutoff_time = parse_cutoff(cutoff)
    days = dates_in_range(settings.first_delivery_date, settings.last_delivery_date)
    selected = selected_frame(days, cutoff_time)
    results = []
    for delivery_date in days:
        group = selected.loc[selected["delivery_date"] == delivery_date]
        results.append(
            DailyMetrics(
                delivery_date=delivery_date,
                metrics=frame_metrics(group, len(expected_forecast_targets(delivery_date, settings.timezone))),
            )
        )
    return DailyAccuracyResponse(cutoff=cutoff_time.strftime("%H:%M"), days=results)


@router.get(
    "/distribution",
    response_model=DistributionResponse,
    description="Decision-time signed-error histogram using the latest forecast available at the D-1 cutoff.",
)
def accuracy_distribution(
    bins: int = Query(default=20, ge=1, le=100),
    cutoff: str | None = Query(default=None, description="Decision cutoff in Europe/London, HH:MM."),
) -> DistributionResponse:
    """Return a histogram of selected decision-time signed errors."""
    cutoff_time = parse_cutoff(cutoff)
    days = dates_in_range(settings.first_delivery_date, settings.last_delivery_date)
    selected = selected_frame(days, cutoff_time)
    errors, _ = paired_errors(selected)
    if errors:
        counts, edges = np.histogram(np.asarray(errors), bins=bins)
        result = [
            HistogramBin(
                lower_error_mw=float(edges[index]),
                upper_error_mw=float(edges[index + 1]),
                count=int(counts[index]),
            )
            for index in range(len(counts))
        ]
    else:
        result = []
    return DistributionResponse(
        sample_count=len(errors),
        error_definition="error_mw = forecast_mw - actual_mw; positive means over-forecast.",
        bins=result,
    )


@router.get(
    "/by-wind-level",
    response_model=WindLevelAccuracyResponse,
    description="Decision-time accuracy grouped by actual wind-generation quartile.",
)
def accuracy_by_wind_level(
    start: date = Query(default=settings.first_delivery_date),
    end: date = Query(default=settings.last_delivery_date),
    cutoff: str | None = Query(default=None, description="Decision cutoff in Europe/London, HH:MM."),
) -> WindLevelAccuracyResponse:
    """Break down decision-time accuracy by actual-generation quartiles."""
    days = dates_in_range(start, end)
    cutoff_time = parse_cutoff(cutoff)
    selected = selected_frame(days, cutoff_time)
    expected_grid = {
        target for day in days for target in expected_forecast_targets(day, settings.timezone)
    }
    grid = selected.loc[selected["startTime"].isin(expected_grid)].copy()
    actual_values = grid["actual"].dropna().to_numpy(dtype=float)
    if not len(actual_values):
        return WindLevelAccuracyResponse(
            start_date=start,
            end_date=end,
            cutoff=cutoff_time.strftime("%H:%M"),
            bucket_method="Actual-generation quartiles over hourly target timestamps in the selected window.",
            buckets=[],
        )
    edges = np.unique(np.quantile(actual_values, [0, 0.25, 0.5, 0.75, 1]))
    bucket_count = len(edges) - 1
    indices = np.searchsorted(edges[1:-1], grid["actual"].to_numpy(dtype=float), side="left")
    grid["wind_bucket_index"] = indices
    result = []
    for index in range(bucket_count):
        group = grid.loc[grid["wind_bucket_index"] == index]
        if group.empty:
            continue
        evaluated = group.dropna(subset=["error", "actual"])["startTime"].nunique()
        result.append(
            WindLevelBucket(
                bucket=f"Q{index + 1}",
                lower_actual_mw=float(edges[index]),
                upper_actual_mw=float(edges[index + 1]),
                metrics=frame_metrics(group, len(group), coverage_count=evaluated),
            )
        )
    return WindLevelAccuracyResponse(
        start_date=start,
        end_date=end,
        cutoff=cutoff_time.strftime("%H:%M"),
        bucket_method="Actual-generation quartiles over hourly target timestamps in the selected window; bounds are in MW.",
        buckets=result,
    )
