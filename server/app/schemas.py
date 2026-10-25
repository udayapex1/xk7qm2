from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Metrics(StrictModel):
    sample_count: int
    coverage_pct: float
    mae_mw: float | None
    rmse_mw: float | None
    mean_error_mw: float | None
    mape_pct: float | None
    wape_pct: float | None
    absolute_error_percentiles_mw: dict[str, float] | None
    signed_error_percentiles_mw: dict[str, float] | None


class ForecastRow(StrictModel):
    start_time: datetime
    actual_mw: float | None
    forecast_mw: float | None
    publish_time: datetime | None
    horizon_hours: float | None
    error_mw: float | None


class ForecastResponse(StrictModel):
    delivery_date: date
    cutoff_timestamp: datetime
    cutoff_timezone: str
    rows: list[ForecastRow]
    summary: Metrics


class VintageRow(StrictModel):
    start_time: datetime
    publish_time: datetime
    generation_mw: float
    horizon_hours: float
    latest_available_at_cutoff: bool
    cutoff_timestamp: datetime


class VintagesResponse(StrictModel):
    target_time: datetime
    delivery_date: date
    cutoff_timestamp: datetime
    selection_rule: str
    forecasts: list[VintageRow]


class AccuracySummary(StrictModel):
    start_date: date
    end_date: date
    cutoff: str
    cutoff_timezone: str
    metrics: Metrics


class BucketMetrics(StrictModel):
    bucket: str
    metrics: Metrics


class HorizonAccuracyResponse(StrictModel):
    scope: str
    buckets: list[BucketMetrics]


class HourMetrics(StrictModel):
    hour: int
    metrics: Metrics


class ByHourResponse(StrictModel):
    cutoff: str
    utc: list[HourMetrics]
    local: list[HourMetrics]


class DailyMetrics(StrictModel):
    delivery_date: date
    metrics: Metrics


class DailyAccuracyResponse(StrictModel):
    cutoff: str
    days: list[DailyMetrics]


class HistogramBin(StrictModel):
    lower_error_mw: float
    upper_error_mw: float
    count: int


class DistributionResponse(StrictModel):
    sample_count: int
    error_definition: str
    bins: list[HistogramBin]


class DecisionRow(StrictModel):
    start_time: datetime
    actual_mw: float | None
    forecast_mw: float | None
    publish_time: datetime | None
    horizon_hours: float | None
    demand_mw: float
    risk_adjusted_forecast_mw: float | None
    additional_power_point_mw: float | None
    additional_power_conservative_mw: float | None


class DecisionResponse(StrictModel):
    delivery_date: date
    cutoff_timestamp: datetime
    demand_source: Literal["user_supplied_flat_demand_mw"]
    demand_mw: float
    error_quantile: float
    error_buffer_mw: float | None
    buffer_sample_count: int
    buffer_history_end_date: date | None
    buffer_status: str
    buffer_note: str
    rows: list[DecisionRow]
