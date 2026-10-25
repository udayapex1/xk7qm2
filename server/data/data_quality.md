# Data quality report

Generated from the Elexon BMRS API by `scripts/fetch_data.py`.

## Snapshot scope

- Actuals: FUELHH, `fuelType=WIND`, delivery target times 2026-01-02T00:00:00+00:00 to 2026-02-01T23:30:00+00:00 (UTC).
- Forecasts: WINDFOR, publish times 2025-12-31T02:30:00+00:00 to 2026-01-31T22:30:00+00:00 (UTC).
- Forecast target times retained: 2026-01-02T00:00:00+00:00 to 2026-02-01T23:00:00+00:00 (UTC).
- Data was restricted to delivery dates covered by the January 2026 decision window.

## Counts and data quality

- Actual rows: 1488; duplicate rows removed: 0.
- Actual half-hour gaps between consecutive retained points: 0.
- Actual coverage against expected half-hour slots: 100.00% (1488/1488).
- Forecast rows: 17864; duplicate `(startTime, publishTime)` rows removed: 0.
- Unique forecast target times: 744 (50.00% of expected half-hour targets); target spacing (minutes): min 60.0, median 60.0, max 60.0.
- Unique forecast publish times: 256.
- Forecast publish-time spacing (minutes): min 120.0, median 180.0, max 240.0.
- Forecast horizon (startTime - publishTime, hours): min -25.50, max 66.50.

Forecast target resolution is taken as supplied by Elexon. Missing target points are retained as missing by the API; no interpolation or fabrication is performed.
