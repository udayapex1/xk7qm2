from fastapi.testclient import TestClient

from server.app.main import app


client = TestClient(app)


def test_all_api_endpoints_smoke() -> None:
    assert client.get("/api/health").json() == {"status": "ok"}

    meta = client.get("/api/meta")
    assert meta.status_code == 200
    assert meta.json()["delivery_date_start"] == "2026-01-02"
    assert meta.json()["actual_coverage_pct"] == 100
    assert meta.json()["forecast_target_coverage_pct"] == 50

    forecast = client.get("/api/forecast", params={"delivery_date": "2026-01-02"})
    assert forecast.status_code == 200
    assert len(forecast.json()["rows"]) == 48
    assert forecast.json()["cutoff_timestamp"] == "2026-01-01T09:00:00Z"

    vintages = client.get(
        "/api/forecast/vintages",
        params={"target_time": "2026-01-02T12:00:00Z"},
    )
    assert vintages.status_code == 200
    for vintage in vintages.json()["forecasts"]:
        if vintage["latest_available_at_cutoff"]:
            assert vintage["publish_time"] <= vintages.json()["cutoff_timestamp"]

    assert client.get("/api/accuracy/summary").status_code == 200
    assert client.get("/api/accuracy/by-horizon").status_code == 200
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

    naive_target = client.get(
        "/api/forecast/vintages",
        params={"target_time": "2026-01-02T12:00:00"},
    )
    assert naive_target.status_code == 422
