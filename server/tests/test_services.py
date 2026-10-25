from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from dataclasses import replace
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from server.app.config import settings
from server.app.services import decision as decision_service
from server.app.services.data_store import DataStore
from server.app.services.decision import build_decision_rows, historical_error_buffer
from server.app.services.forecast import decision_cutoff, expected_targets, horizon_hours, latest_available
from server.app.services.metrics import calculate_metrics


def make_store(forecasts: list[dict], actuals: list[dict]) -> DataStore:
    return DataStore(
        pd.DataFrame(actuals, columns=["startTime", "generation"]),
        pd.DataFrame(forecasts, columns=["startTime", "publishTime", "generation"]),
    )


def test_latest_available_selects_latest_eligible_never_future_and_marks_missing() -> None:
    delivery = date(2026, 1, 2)
    target = "2026-01-02T00:00:00Z"
    store = make_store(
        [
            {"startTime": target, "publishTime": "2026-01-01T08:00:00Z", "generation": 100},
            {"startTime": target, "publishTime": "2026-01-01T09:00:00Z", "generation": 110},
            {"startTime": target, "publishTime": "2026-01-01T09:01:00Z", "generation": 999},
        ],
        [{"startTime": target, "generation": 105}],
    )
    frame = latest_available(store, delivery, time(9, 0), ZoneInfo("Europe/London"))
    selected = frame.loc[frame["startTime"] == pd.Timestamp(target)]

    assert selected.iloc[0]["generation"] == 110
    assert selected.iloc[0]["publishTime"] == pd.Timestamp("2026-01-01T09:00:00Z")
    assert selected.iloc[0]["error"] == 5
    assert selected["publishTime"].max() <= pd.Timestamp("2026-01-01T09:00:00Z")
    assert frame["generation"].isna().sum() == 47


def test_horizon_is_start_minus_publish_in_hours() -> None:
    assert horizon_hours(
        datetime(2026, 1, 2, 12, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 6, tzinfo=timezone.utc),
    ) == 30


def test_window_and_cutoff_respect_uk_dst() -> None:
    zone = ZoneInfo("Europe/London")
    assert len(expected_targets(date(2026, 3, 29), zone)) == 46
    assert len(expected_targets(date(2026, 10, 25), zone)) == 50
    assert decision_cutoff(date(2026, 3, 30), time(9), zone) == pd.Timestamp(
        "2026-03-29T08:00:00Z"
    )


def test_metrics_match_hand_calculated_values_and_error_sign() -> None:
    metrics = calculate_metrics([2, -2], [10, 20], expected_count=4)
    assert metrics["mae_mw"] == 2
    assert metrics["rmse_mw"] == 2
    assert metrics["mean_error_mw"] == 0
    assert metrics["mape_pct"] == pytest.approx(15)
    assert metrics["wape_pct"] == pytest.approx(100 * 4 / 30)
    assert metrics["sample_count"] == 2
    assert metrics["coverage_pct"] == 50
    assert metrics["absolute_error_percentiles_mw"]["p50"] == 2
    assert metrics["signed_error_percentiles_mw"]["p50"] == 0


def test_all_error_percentiles_match_hand_calculated_values() -> None:
    metrics = calculate_metrics([-4, -2, 1, 3], [10, 20, 30, 40])
    assert metrics["absolute_error_percentiles_mw"] == {
        "p50": 2.5,
        "p90": 3.7,
        "p95": 3.8499999999999996,
        "p99": 3.9699999999999998,
    }
    assert metrics["signed_error_percentiles_mw"] == {
        "p5": -3.7,
        "p10": -3.4,
        "p50": -0.5,
        "p90": 2.4000000000000004,
        "p95": 2.6999999999999993,
    }


def test_mape_excludes_near_zero_actuals_and_signed_error_positive_is_overforecast() -> None:
    metrics = calculate_metrics([10, 2], [0.1, 10], expected_count=2)
    assert metrics["mape_pct"] == 20
    assert metrics["mean_error_mw"] == 6
    assert metrics["signed_error_percentiles_mw"]["p50"] == 6


def test_mape_is_missing_when_every_actual_is_near_zero() -> None:
    assert calculate_metrics([1], [0.5])["mape_pct"] is None


def test_positive_bias_lowers_conservative_wind_and_increases_procurement() -> None:
    selected = pd.DataFrame(
        {
            "startTime": [pd.Timestamp("2026-01-02T00:00:00Z")],
            "actual": [None],
            "generation": [20.0],
            "publishTime": [pd.Timestamp("2026-01-01T00:00:00Z")],
            "horizon_hours": [24.0],
            "error": [None],
        }
    )
    selected.loc[0, "generation"] = 100.0
    decision = build_decision_rows(selected, demand_mw=110, error_quantile_mw=10)
    assert decision.iloc[0]["conservative_wind"] == 90
    assert decision.iloc[0]["conservative_wind"] < decision.iloc[0]["generation"]
    assert decision.iloc[0]["additional_power_point"] == 10
    assert decision.iloc[0]["additional_power_conservative"] == 20
    assert decision.iloc[0]["additional_power_conservative"] > decision.iloc[0]["additional_power_point"]


def test_conservative_wind_floor_at_zero() -> None:
    selected = pd.DataFrame({"generation": [20.0], "actual": [None]})
    decision = build_decision_rows(selected, demand_mw=30, error_quantile_mw=25)
    assert decision.iloc[0]["conservative_wind"] == 0
    assert decision.iloc[0]["additional_power_conservative"] == 30


def test_decision_buffer_uses_only_prior_delivery_days(monkeypatch) -> None:
    zone = ZoneInfo("Europe/London")
    prior_day = date(2026, 1, 2)
    delivery_day = date(2026, 1, 3)
    forecasts = []
    actuals = []
    for index in range(48):
        target_prior = datetime(2026, 1, 2, tzinfo=timezone.utc) + timedelta(minutes=30 * index)
        target_delivery = datetime(2026, 1, 3, tzinfo=timezone.utc) + timedelta(minutes=30 * index)
        forecasts.extend(
            [
                {
                    "startTime": target_prior.isoformat(),
                    "publishTime": "2026-01-01T08:00:00Z",
                    "generation": 104,
                },
                {
                    "startTime": target_delivery.isoformat(),
                    "publishTime": "2026-01-02T08:00:00Z",
                    "generation": 1000,
                },
            ]
        )
        actuals.extend(
            [
                {"startTime": target_prior.isoformat(), "generation": 100},
                {"startTime": target_delivery.isoformat(), "generation": 100},
            ]
        )
    store = make_store(forecasts, actuals)
    monkeypatch.setattr(
        decision_service, "settings", replace(settings, minimum_buffer_samples=30)
    )

    buffer, count, history_end, status = historical_error_buffer(
        store, delivery_day, time(9), zone, 0.9
    )

    assert buffer == 4
    assert count == 48
    assert history_end == prior_day
    assert status == "historical_quantile"


def test_first_delivery_day_has_graceful_insufficient_history(monkeypatch) -> None:
    monkeypatch.setattr(
        decision_service, "settings", replace(settings, minimum_buffer_samples=30)
    )
    store = make_store([], [])

    buffer, count, history_end, status = historical_error_buffer(
        store, settings.first_delivery_date, time(9), ZoneInfo("Europe/London"), 0.1
    )

    assert buffer is None
    assert count == 0
    assert history_end is None
    assert status == "insufficient_history"
