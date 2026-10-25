# UK Wind Forecast Decision Support — Backend

This repository contains a Python API for a January 2026 day-ahead wind-purchase pilot. The backend uses only Elexon BMRS national FUELHH WIND actuals and WINDFOR forecasts; its snapshot is bundled under `server/data/` so normal app requests do not call Elexon. The existing `client/` directory has intentionally been left untouched.

## Repository layout

```text
api/index.py                    Vercel entry point
client/                         reserved for a later frontend (untouched)
docker-compose.yml              local backend service; commented client slot
docs/CHALLENGE.md               supplied company challenge document
server/
  app/main.py                   FastAPI app, OpenAPI, CORS, health and metadata
  app/config.py                 environment-driven decision window and timezone
  app/schemas.py                typed API response models
  app/routers/                  forecast, accuracy, and decision endpoints
  app/services/                 snapshot store, selection, metrics, decision logic
  data/actuals.csv              committed FUELHH WIND snapshot
  data/forecasts.csv            committed WINDFOR snapshot
  data/data_quality.md          counts, coverage, gaps, duplicates, publish spacing
  scripts/fetch_data.py         retrying, chunked one-off snapshot fetcher
  tests/                        service and TestClient endpoint tests
  Dockerfile                    backend container
  requirements.txt              backend dependencies
vercel.json                     serverless Python route
```

## Data/API verification

Before implementing the fetcher, the official Elexon OpenAPI document at <https://data.elexon.co.uk/swagger/v1/swagger.json> was inspected. It documents:

- `FUELHH/stream`: `settlementDateFrom`, `settlementDateTo` (`yyyy-MM-dd`) and `fuelType` (array; `WIND`).
- `WINDFOR/stream`: `publishDateTimeFrom` and `publishDateTimeTo` (date-time).
- Both return JSON arrays from the stream endpoints. FUELHH rows include `startTime`, `fuelType`, and `generation`; WINDFOR rows include `startTime`, `publishTime`, and `generation`.
- The OpenAPI schema does not declare a maximum date range. Real calls accepted one 31-day FUELHH range (1,488 rows) and one 35-day WINDFOR publish range (20,440 rows). The fetcher nevertheless uses seven-day chunks and sequential requests to be rate-limit friendly.

Sample rows from those successful API calls:

```json
{"dataset":"FUELHH","publishTime":"2026-01-03T00:00:00Z","startTime":"2026-01-02T23:30:00Z","fuelType":"WIND","generation":14202}
{"dataset":"WINDFOR","startTime":"2025-12-28T00:00:00Z","publishTime":"2025-12-28T22:30:00Z","generation":9054}
```

The actuals endpoint reports half-hour targets. In the fetched WINDFOR snapshot, unique targets are hourly, so only half of the expected half-hour decision points have a forecast. The API preserves those other points as missing; it does not interpolate or invent half-hour forecasts.

## Assumptions and definitions

- Decision dates are **2026-01-01 through 2026-01-31**. Delivery dates are **2026-01-02 through 2026-02-01**.
- The default decision cutoff is **09:00 Europe/London on D-1**. It is configurable as `cutoff=HH:MM`; timestamps are serialized in UTC ISO-8601. January is GMT, but `zoneinfo` is used for date and cutoff conversion.
- For each target, the selected vintage is the maximum `publishTime` no later than the decision cutoff. No forecast beyond the cutoff is eligible. Missing eligible forecasts remain null.
- Horizon is `(startTime - publishTime)` in hours. Vintage analysis retains negative horizons where Elexon published a value after its target; such rows are never used for the decision forecast.
- Error is `forecast_mw - actual_mw`: positive means an over-forecast; negative means an under-forecast.
- MAE and RMSE are in MW; ME is signed MW error; absolute and signed error quantiles are in MW. MAPE is a percent and excludes points where `abs(actual_mw) <= 1 MW`. WAPE is `sum(abs(error)) / sum(abs(actual)) * 100`. Coverage is paired forecast/actual points divided by expected half-hour targets (the horizon endpoint reports matched forecast-vintage coverage within each bucket).
- The decision endpoint accepts flat demand in MW from the caller; it is not Elexon data. Its default risk buffer is the historical P10 signed error, added to the point forecast and clamped at zero. Only earlier delivery days are used; fewer than `MINIMUM_BUFFER_SAMPLES` prior matched points produces an explicit `insufficient_history` status and no adjustment. **Sign caveat:** because error is `forecast - actual`, a positive P10 buffer raises estimated wind and is not conservative in that case. The API returns this warning in `buffer_note`; changing to a conservative adjustment would require subtracting a high-side forecast-error quantile rather than following the requested addition formula.

## Run locally

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn server.app.main:app --reload
```

Open <http://127.0.0.1:8000/docs> for the interactive OpenAPI documentation. Requests are served entirely from `server/data/`.

## Fetch or refresh the snapshot

```bash
pip install -r requirements.txt
python server/scripts/fetch_data.py
```

The script reads the `DECISION_START` and `DECISION_END` environment values if set, calls only the Elexon FUELHH and WINDFOR stream endpoints, retries transient errors, filters/cleans data, and writes the two CSV snapshots plus `server/data/data_quality.md`. The historical January 2026 snapshot is checked into the repository; running the script again is not required to start the API.

## Docker

```bash
docker compose up --build
```

The backend is available at <http://127.0.0.1:8000>. `docker-compose.yml` includes a commented placeholder for adding the client later.

## Tests

```bash
pytest server/tests -q
```

## Environment variables

Copy `server/.env.example` as a reference. Configuration is read from the process environment:

| Variable | Default | Purpose |
|---|---|---|
| `DECISION_START` | `2026-01-01` | First decision date |
| `DECISION_END` | `2026-01-31` | Last decision date |
| `DEFAULT_CUTOFF` | `09:00` | D-1 decision cutoff |
| `TIMEZONE` | `Europe/London` | Decision-window timezone |
| `ALLOWED_ORIGINS` | `*` | Comma-separated CORS origins, or `*` for development |
| `MINIMUM_BUFFER_SAMPLES` | `30` | Matched prior-day errors required for a decision buffer |

## API endpoints

All endpoints are under `/api`; responses use UTC timestamps.

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/meta
curl 'http://127.0.0.1:8000/api/forecast?delivery_date=2026-01-02&cutoff=09:00'
curl 'http://127.0.0.1:8000/api/forecast/vintages?target_time=2026-01-02T12:00:00Z&cutoff=09:00'
curl 'http://127.0.0.1:8000/api/accuracy/summary?start=2026-01-02&end=2026-02-01&cutoff=09:00'
curl http://127.0.0.1:8000/api/accuracy/by-horizon
curl 'http://127.0.0.1:8000/api/accuracy/by-hour?cutoff=09:00'
curl 'http://127.0.0.1:8000/api/accuracy/daily?cutoff=09:00'
curl 'http://127.0.0.1:8000/api/accuracy/distribution?bins=20&cutoff=09:00'
curl 'http://127.0.0.1:8000/api/decision?delivery_date=2026-01-02&cutoff=09:00&demand_mw=25000&quantile=0.1'
```

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Health check |
| `GET /api/meta` | Data range/coverage, default cutoff, and definitions |
| `GET /api/forecast` | Latest eligible forecast and actuals for all expected delivery half-hours |
| `GET /api/forecast/vintages` | Vintages for a target and flag for the latest vintage at cutoff |
| `GET /api/accuracy/summary` | Decision-time accuracy for a delivery-date range |
| `GET /api/accuracy/by-horizon` | All-vintage accuracy by forecast horizon |
| `GET /api/accuracy/by-hour` | Decision-time accuracy by UTC and local hour |
| `GET /api/accuracy/daily` | Decision-time daily MAE, bias, and other metrics |
| `GET /api/accuracy/distribution` | Histogram of decision-time signed errors |
| `GET /api/decision` | Point and risk-adjusted wind plus additional procurement using caller demand |

Dates outside the configured delivery window, malformed cutoffs, naive vintage timestamps, invalid demand, and invalid quantiles receive 4xx validation errors.

## Deployment

Vercel is configured through `api/index.py`, root `requirements.txt`, and `vercel.json`; no deployment has been made and there is no live URL yet. A Vercel project/deployment requires account credentials and configuration not present in this workspace.

The company document also requests a React frontend and a hosted Vercel/Heroku app. This work is intentionally backend-only per the current task scope; `client/` was not changed. The frontend and hosted deployment remain outstanding.

## Analysis

See [server/ANALYSIS.md](./server/ANALYSIS.md) for measured results from the committed Elexon snapshot.

AI tools were used to assist development.