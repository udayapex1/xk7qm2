from fastapi.testclient import TestClient

from server.app.main import app


client = TestClient(app)


def test_all_api_endpoints_smoke() -> None:
    assert client.get("/api/health").json() == {"status": "ok"}

    meta = client.get("/api/meta")
    assert meta.status_code == 200
    assert meta.json()["delivery_date_start"] == "2026-01-02"
    assert meta.json()["actual_coverage_pct"] == 100
    assert meta.json()["forecast_grid_expected_points"] == 744
    assert meta.json()["forecast_grid_evaluated_points"] == 744
    assert meta.json()["forecast_grid_coverage_pct"] == 100

    forecast = client.get("/api/forecast", params={"delivery_date": "2026-01-02"})
    assert forecast.status_code == 200
    assert len(forecast.json()["rows"]) == 48
    assert sum(row["forecast_missing"] for row in forecast.json()["rows"]) == 24
    assert sum(row["forecast_mw"] is not None for row in forecast.json()["rows"]) == 24
    assert forecast.json()["cutoff_timestamp"] == "2026-01-01T09:00:00Z"

    vintages = client.get(
        "/api/forecast/vintages",
        params={"target_time": "2026-01-02T12:00:00Z"},
    )
    assert vintages.status_code == 200
    for vintage in vintages.json()["forecasts"]:
        if vintage["latest_available_at_cutoff"]:
            assert vintage["publish_time"] <= vintages.json()["cutoff_timestamp"]

    summary = client.get("/api/accuracy/summary")
    assert summary.status_code == 200
    assert summary.json()["metrics"]["sample_count"] == 744
    assert summary.json()["metrics"]["coverage_pct"] == 100
    horizon = client.get("/api/accuracy/by-horizon")
    assert horizon.status_code == 200
    assert "All retained" in horizon.json()["scope"]
    horizon_coverages = [bucket["metrics"]["coverage_pct"] for bucket in horizon.json()["buckets"]]
    assert all(coverage <= 100 for coverage in horizon_coverages)
    assert any(coverage < 100 for coverage in horizon_coverages)
    wind = client.get("/api/accuracy/by-wind-level")
    assert wind.status_code == 200
    assert len(wind.json()["buckets"]) == 4
    assert sum(bucket["metrics"]["sample_count"] for bucket in wind.json()["buckets"]) == 744

    positive_bias_decision = client.get(
        "/api/decision",
        params={"delivery_date": "2026-01-04", "demand_mw": 18000},
    ).json()
    first = positive_bias_decision["rows"][0]
    assert positive_bias_decision["error_quantile"] == 0.9
    assert positive_bias_decision["buffer_history_end_date"] < positive_bias_decision["delivery_date"]
    assert first["conservative_wind_mw"] < first["forecast_mw"]
    assert first["additional_power_conservative_mw"] > first["additional_power_point_mw"]
    assert client.get("/api/accuracy/by-hour").status_code == 200
    assert client.get("/api/accuracy/daily").status_code == 200
    distribution = client.get("/api/accuracy/distribution", params={"bins": 10})
    assert distribution.status_code == 200
    assert sum(item["count"] for item in distribution.json()["bins"]) == distribution.json()["sample_count"]

    decision = client.get(
        "/api/decision",
        params={"delivery_date": "2026-01-02", "demand_mw": 25000},
    )
    assert decision.status_code == 200
    assert decision.json()["demand_source"] == "user_supplied_flat_demand_mw"
    assert decision.json()["buffer_status"] == "insufficient_history"


def test_api_rejects_out_of_window_dates_and_bad_cutoff() -> None:
    outside = client.get("/api/forecast", params={"delivery_date": "2026-01-01"})
    assert outside.status_code == 422
    assert "must be between" in outside.json()["detail"]

    bad_cutoff = client.get(
        "/api/forecast",
        params={"delivery_date": "2026-01-02", "cutoff": "9am"},
    )
    assert bad_cutoff.status_code == 422
    assert "HH:MM" in bad_cutoff.json()["detail"]

    bad_summary = client.get(
        "/api/accuracy/summary",
        params={"start": "2026-01-10", "end": "2026-01-02"},
    )
    assert bad_summary.status_code == 422

    bad_decision = client.get(
        "/api/decision",
        params={"delivery_date": "2026-01-02", "demand_mw": -1},
    )
    assert bad_decision.status_code == 422

    huge_demand = client.get(
        "/api/decision",
        params={"delivery_date": "2026-01-02", "demand_mw": 200001},
    )
    assert huge_demand.status_code == 422
    assert "200000" in huge_demand.text

    naive_target = client.get(
        "/api/forecast/vintages",
        params={"target_time": "2026-01-02T12:00:00"},
    )
    assert naive_target.status_code == 422
