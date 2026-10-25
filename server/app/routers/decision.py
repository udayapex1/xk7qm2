from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from server.app.config import settings
from server.app.routers.common import check_delivery_date, parse_cutoff, store
from server.app.routers.forecast import json_value
from server.app.schemas import DecisionResponse, DecisionRow
from server.app.services.decision import build_decision_rows, historical_error_buffer
from server.app.services.forecast import decision_cutoff, latest_available


router = APIRouter(prefix="/api", tags=["decision support"])


@router.get("/decision", response_model=DecisionResponse)
def get_decision(
    delivery_date: date,
    demand_mw: float = Query(gt=0, le=200000, description="Flat user-supplied demand in MW; maximum 200,000 MW."),
    cutoff: str | None = Query(default=None, description="Decision cutoff in Europe/London, HH:MM."),
    quantile: float = Query(default=0.90, ge=0, le=1, description="Quantile of prior-day signed errors (forecast minus actual)."),
) -> DecisionResponse:
    """Return point procurement and a conservative wind procurement estimate."""
    check_delivery_date(delivery_date)
    cutoff_time = parse_cutoff(cutoff)
    selected = latest_available(store, delivery_date, cutoff_time, settings.timezone)
    error_quantile, sample_count, history_end, status = historical_error_buffer(
        store, delivery_date, cutoff_time, settings.timezone, quantile
    )
    decisions = build_decision_rows(selected, demand_mw, error_quantile)
    rows = [
        DecisionRow(
            start_time=row.startTime.to_pydatetime(),
            actual_mw=json_value(row.actual),
            forecast_mw=json_value(row.generation),
            publish_time=json_value(row.publishTime),
            horizon_hours=json_value(row.horizon_hours),
            demand_mw=float(row.demand_mw),
            conservative_wind_mw=json_value(row.conservative_wind),
            additional_power_point_mw=json_value(row.additional_power_point),
            additional_power_conservative_mw=json_value(row.additional_power_conservative),
        )
        for row in decisions.itertuples(index=False)
    ]
    return DecisionResponse(
        delivery_date=delivery_date,
        cutoff_timestamp=decision_cutoff(
            delivery_date, cutoff_time, settings.timezone
        ).to_pydatetime(),
        demand_source="user_supplied_flat_demand_mw",
        demand_mw=demand_mw,
        error_quantile=quantile,
        historical_error_quantile_mw=error_quantile,
        buffer_sample_count=sample_count,
        buffer_history_end_date=history_end,
        buffer_status=status,
        buffer_note=(
            "Error is forecast minus actual. Conservative wind is max(forecast - Qq(prior-day errors), 0); "
            "when the historical error is below its q-quantile, actual wind is at least this estimate "
            "(approximately q probability under a stable error distribution). The quantile uses only "
            "earlier delivery days. With insufficient history, conservative wind equals the forecast."
        ),
        rows=rows,
    )
