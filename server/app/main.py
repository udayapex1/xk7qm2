from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.app.config import settings
from server.app.routers import accuracy, decision, forecast
from server.app.routers.common import store
from server.app.schemas import StrictModel
from server.app.services.forecast import delivery_window


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
    forecast_target_points: int
    forecast_target_coverage_pct: float
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
    return HealthResponse(status="ok")


@app.get("/api/meta", response_model=MetaResponse, tags=["meta"])
def meta() -> MetaResponse:
    actual_start = store.actuals["startTime"].min() if not store.actuals.empty else None
    actual_end = store.actuals["startTime"].max() if not store.actuals.empty else None
    forecast_start = store.forecasts["publishTime"].min() if not store.forecasts.empty else None
    forecast_end = store.forecasts["publishTime"].max() if not store.forecasts.empty else None
    window_start, _ = delivery_window(settings.first_delivery_date, settings.timezone)
    _, window_end = delivery_window(settings.last_delivery_date, settings.timezone)
    expected_points = 0
    current_date = settings.first_delivery_date
    while current_date <= settings.last_delivery_date:
        day_start, day_end = delivery_window(current_date, settings.timezone)
        expected_points += int((day_end - day_start).total_seconds() / 1800)
        current_date += timedelta(days=1)
    target_points = int(
        store.forecasts.loc[
            (store.forecasts["startTime"] >= window_start)
            & (store.forecasts["startTime"] < window_end),
            "startTime",
        ].nunique()
    )
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
        forecast_target_points=target_points,
        forecast_target_coverage_pct=100 * target_points / expected_points if expected_points else 0,
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
            "Coverage": "Paired forecast-and-actual rows divided by expected target points, expressed as percent.",
        },
    )
