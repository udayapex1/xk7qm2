from __future__ import annotations

from datetime import date, time, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from server.app.config import settings
from server.app.services.data_store import DataStore
from server.app.services.forecast import latest_available


def historical_error_buffer(
    store: DataStore,
    delivery_date: date,
    cutoff: time,
    zone: ZoneInfo,
    quantile: float,
) -> tuple[float | None, int, date | None, str]:
    """Return a signed-error quantile using only earlier delivery days."""
    errors: list[float] = []
    prior_date = settings.first_delivery_date
    while prior_date < delivery_date:
        selected = latest_available(store, prior_date, cutoff, zone)
        errors.extend(selected["error"].dropna().astype(float).tolist())
        prior_date += timedelta(days=1)

    sample_count = len(errors)
    history_end = delivery_date - timedelta(days=1) if sample_count else None
    if sample_count < settings.minimum_buffer_samples:
        return None, sample_count, history_end, "insufficient_history"
    return float(np.quantile(errors, quantile)), sample_count, history_end, "historical_quantile"


def build_decision_rows(
    selected: pd.DataFrame,
    demand_mw: float,
    error_quantile_mw: float | None,
) -> pd.DataFrame:
    """Add conservative wind and procurement estimates to selected forecasts."""
    result = selected.copy()
    result["demand_mw"] = demand_mw
    if error_quantile_mw is None:
        result["conservative_wind"] = result["generation"]
    else:
        result["conservative_wind"] = (result["generation"] - error_quantile_mw).clip(lower=0)
    result["additional_power_point"] = (demand_mw - result["generation"]).clip(lower=0)
    result["additional_power_conservative"] = (demand_mw - result["conservative_wind"]).clip(lower=0)
    return result
