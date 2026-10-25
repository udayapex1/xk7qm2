from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from server.app.services.data_store import DataStore


def delivery_window(delivery_date: date, zone: ZoneInfo) -> tuple[pd.Timestamp, pd.Timestamp]:
    local_start = datetime.combine(delivery_date, time.min, tzinfo=zone)
    local_end = datetime.combine(delivery_date + timedelta(days=1), time.min, tzinfo=zone)
    return (
        pd.Timestamp(local_start.astimezone(ZoneInfo("UTC"))),
        pd.Timestamp(local_end.astimezone(ZoneInfo("UTC"))),
    )


def decision_cutoff(delivery_date: date, cutoff: time, zone: ZoneInfo) -> pd.Timestamp:
    decision_date = delivery_date - timedelta(days=1)
    local_cutoff = datetime.combine(decision_date, cutoff, tzinfo=zone)
    return pd.Timestamp(local_cutoff.astimezone(ZoneInfo("UTC")))


def expected_targets(delivery_date: date, zone: ZoneInfo) -> pd.DatetimeIndex:
    start, end = delivery_window(delivery_date, zone)
    return pd.date_range(start=start, end=end, freq="30min", inclusive="left")


def latest_available(
    store: DataStore,
    delivery_date: date,
    cutoff: time,
    zone: ZoneInfo,
) -> pd.DataFrame:
    start, end = delivery_window(delivery_date, zone)
    cutoff_timestamp = decision_cutoff(delivery_date, cutoff, zone)
    actuals = store.actuals_for(start, end).set_index("startTime")["generation"]
    forecasts = store.forecasts_for(start, end)
    forecasts = forecasts.loc[forecasts["publishTime"] <= cutoff_timestamp]
    forecasts = forecasts.sort_values(["startTime", "publishTime"])
    latest = forecasts.drop_duplicates(subset=["startTime"], keep="last").set_index("startTime")

    result = pd.DataFrame(index=expected_targets(delivery_date, zone))
    result.index.name = "startTime"
    result["actual"] = actuals.reindex(result.index)
    result["generation"] = latest["generation"].reindex(result.index)
    result["publishTime"] = latest["publishTime"].reindex(result.index)
    result["horizon_hours"] = (
        (result.index.to_series() - result["publishTime"]).dt.total_seconds() / 3600
    )
    result["error"] = result["generation"] - result["actual"]
    return result.reset_index()


def horizon_hours(start_time: datetime | pd.Timestamp, publish_time: datetime | pd.Timestamp) -> float:
    return (pd.Timestamp(start_time) - pd.Timestamp(publish_time)).total_seconds() / 3600
