from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

from server.app.config import settings
from server.app.routers import accuracy, decision, forecast
from server.app.routers.common import store
from server.app.schemas import StrictModel
from server.app.services.forecast import (
    decision_cutoff,
    delivery_window,
    expected_forecast_targets,
)


class HealthResponse(StrictModel):
    status: str


class MetaResponse(StrictModel):
    decision_date_start: date
    decision_date_end: date
    delivery_date_start: date
    delivery_date_end: date
    default_cutoff: str
    timezone: str
    actual_rows: int
    actual_expected_points: int
    actual_coverage_pct: float
    forecast_rows: int
    forecast_grid_expected_points: int
    forecast_grid_evaluated_points: int
    forecast_grid_coverage_pct: float
    forecast_grid_resolution: str
    half_hour_missing_forecast_behavior: str
    actual_start_time: datetime | None
    actual_end_time: datetime | None
    forecast_publish_start: datetime | None
    forecast_publish_end: datetime | None
    error_definition: str
    metric_definitions: dict[str, str]


app = FastAPI(
    title="UK Wind Forecast Decision Support API",
    version="1.0.0",
    description=(
        "National GB wind actuals and forecasts from Elexon BMRS. "
        "Forecast error is forecast minus actual: positive means over-forecast."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials="*" not in settings.allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(forecast.router)
app.include_router(accuracy.router)
app.include_router(decision.router)


@app.get("/api/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    """Report that the API process is responding."""
    return HealthResponse(status="ok")


@app.get("/api/meta", response_model=MetaResponse, tags=["meta"])
def meta() -> MetaResponse:
    """Describe the configured window, snapshot coverage, and metric definitions."""
    actual_start = store.actuals["startTime"].min() if not store.actuals.empty else None
    actual_end = store.actuals["startTime"].max() if not store.actuals.empty else None
    forecast_start = store.forecasts["publishTime"].min() if not store.forecasts.empty else None
    forecast_end = store.forecasts["publishTime"].max() if not store.forecasts.empty else None
    expected_points = 0
    current_date = settings.first_delivery_date
    while current_date <= settings.last_delivery_date:
        day_start, day_end = delivery_window(current_date, settings.timezone)
        expected_points += int((day_end - day_start).total_seconds() / 1800)
        current_date += timedelta(days=1)
    expected_grid: set[pd.Timestamp] = set()
    current_date = settings.first_delivery_date
    while current_date <= settings.last_delivery_date:
        expected_grid.update(expected_forecast_targets(current_date, settings.timezone))
        current_date += timedelta(days=1)
    actual_grid = set(store.actuals.loc[store.actuals["startTime"].isin(expected_grid), "startTime"])
    eligible_grid: set[pd.Timestamp] = set()
    current_date = settings.first_delivery_date
    while current_date <= settings.last_delivery_date:
        day_start, day_end = delivery_window(current_date, settings.timezone)
        cutoff_timestamp = decision_cutoff(
            current_date, settings.default_cutoff, settings.timezone
        )
        eligible = store.forecasts_for(day_start, day_end)
        eligible = eligible.loc[eligible["publishTime"] <= cutoff_timestamp]
        eligible = eligible.drop_duplicates(subset=["startTime"], keep="last")
        eligible_grid.update(eligible.loc[eligible["generation"].notna(), "startTime"])
        current_date += timedelta(days=1)
    evaluated_points = len(actual_grid & eligible_grid)
    return MetaResponse(
        decision_date_start=settings.decision_start,
        decision_date_end=settings.decision_end,
        delivery_date_start=settings.first_delivery_date,
        delivery_date_end=settings.last_delivery_date,
        default_cutoff=settings.default_cutoff.strftime("%H:%M"),
        timezone=settings.timezone_name,
        actual_rows=len(store.actuals),
        actual_expected_points=expected_points,
        actual_coverage_pct=100 * len(store.actuals) / expected_points if expected_points else 0,
        forecast_rows=len(store.forecasts),
        forecast_grid_expected_points=len(expected_grid),
        forecast_grid_evaluated_points=evaluated_points,
        forecast_grid_coverage_pct=100 * evaluated_points / len(expected_grid) if expected_grid else 0,
        forecast_grid_resolution="Hourly WINDFOR targets; actuals are half-hourly.",
        half_hour_missing_forecast_behavior="Half-hour timestamps without a forecast are returned as null with forecast_missing=true; no interpolation is applied.",
        actual_start_time=actual_start,
        actual_end_time=actual_end,
        forecast_publish_start=forecast_start,
        forecast_publish_end=forecast_end,
        error_definition="error_mw = forecast_mw - actual_mw; positive means over-forecast.",
        metric_definitions={
            "MAE": "Mean absolute forecast error, MW.",
            "RMSE": "Root mean squared forecast error, MW.",
            "ME": "Mean signed error (forecast - actual), MW; positive means over-forecast.",
            "MAPE": "Mean absolute percentage error; excludes actuals with absolute value <= 1 MW.",
            "WAPE": "Sum absolute errors / sum absolute actual generation, expressed as percent.",
            "Coverage": "At the configured default cutoff, evaluated hourly forecast/actual target points divided by expected hourly forecast-grid points, expressed as percent. Half-hour rows without forecasts remain null and are flagged.",
            "Decision-time accuracy": "Uses the latest WINDFOR vintage published no later than the D-1 cutoff.",
            "All-vintage horizon accuracy": "Includes all retained WINDFOR vintages, with per-bucket coverage based on unique target timestamps.",
        },
    )
