# UK Wind Forecast Decision Support

**Live app:** : https://xk7qm2.vercel.app/

**Demo video:**: https://youtu.be/55GM2nIYAqM?si=9fSSi1ZhFCgVMJoI

## Overview

- A UK utility must buy power for the next day and make its decision before that delivery day begins.
- Wind generation forecasts are uncertain, so the amount of wind available can differ from the forecast.
- This portal shows the latest national wind forecast that was available at the decision cutoff.
- It measures forecast accuracy against observed generation and shows how forecast error affects extra power procurement.
- The snapshot uses Elexon FUELHH actuals and WINDFOR forecasts for January 2026 decision days.

## Screens and features

- **Forecast — `/`**: Select a delivery date and decision cutoff, review the selected forecast against actual wind, inspect forecast vintages, and open the accuracy or decision views.
- **Accuracy — `/accuracy`**: Review decision-time accuracy metrics, performance by horizon and hour, daily results, error distribution, and results grouped by actual wind generation.
- **Decision helper — `/decision`**: Enter a delivery date and demand, select an error quantile, and compare procurement using the forecast with procurement using a conservative wind estimate.

## Architecture

```text
Browser
  ├── Docker: Nginx static frontend ── /api/ ──┐
  └── Vercel: static frontend ──────── /api/ ──┤
                                               v
                                      FastAPI application
                                               |
                                  CSV snapshot loaded in memory
```

- The committed CSV snapshot is loaded by the API; normal requests do not call Elexon or use a database.
- Forecast selection uses the latest vintage published at or before the D-1 decision cutoff.
- Forecast points without an observed forecast remain null; half-hour forecasts are not interpolated.
- The decision buffer uses only errors from earlier delivery days.
- The frontend calls the same-origin `/api` path in production; Vite proxies that path to the local API during development.

## Repository layout

```text
.                                      Project root
├── .gitignore                         Local build and environment exclusions
├── README.md                          Project guide
├── requirements.txt                   Vercel Python runtime dependencies
├── docker-compose.yml                 Local backend and frontend services
├── vercel.json                        Vercel build, function, and rewrite config
├── api/
│   ├── __init__.py                    Python package marker
│   └── index.py                       Vercel entry point exporting the FastAPI app
├── client/
│   ├── .dockerignore                  Frontend Docker build exclusions
│   ├── .prettierrc.json               Prettier configuration
│   ├── Dockerfile                     Multi-stage frontend image build
│   ├── eslint.config.js               ESLint configuration
│   ├── index.html                     Vite HTML entry
│   ├── nginx.conf                     SPA routing and /api reverse proxy
│   ├── package.json                   Frontend dependencies and scripts
│   ├── package-lock.json              Locked frontend dependency versions
│   ├── tsconfig.app.json               Application TypeScript configuration
│   ├── tsconfig.json                   Project TypeScript configuration
│   ├── tsconfig.node.json              Vite config TypeScript configuration
│   ├── vite.config.ts                 Vite, API proxy, and Vitest configuration
│   └── src/
│       ├── App.tsx                    Navigation and page routes
│       ├── components.tsx             Shared presentation components
│       ├── main.tsx                   React application entry
│       ├── style.css                  Application styles
│       ├── vite-env.d.ts              Vite environment types
│       ├── api/
│       │   ├── client.ts               Typed API calls
│       │   └── types.ts                API response types
│       ├── components/ui/
│       │   └── bento-grid.tsx          Bento grid presentation component
│       ├── hooks/
│       │   ├── useAccuracy.ts          Accuracy data hook
│       │   ├── useApi.ts               Shared API hook
│       │   ├── useDecision.ts          Decision data hook
│       │   └── useForecast.ts          Forecast data hook
│       ├── lib/
│       │   └── format.ts               Display formatting helpers
│       ├── pages/
│       │   ├── AccuracyPage.tsx        Accuracy screen
│       │   ├── DecisionPage.tsx        Decision helper screen
│       │   └── ForecastPage.tsx        Forecast screen
│       └── test/
│           ├── client.test.ts          API client tests
│           ├── format.test.ts          Formatting helper tests
│           ├── pages.test.tsx          Page rendering tests
│           └── setup.ts                Test setup
├── docs/
│   ├── CHALLENGE.md                   Project brief
│   └── REint Full Stack SWE challenge v4 Shared (1).docx
│                                       Supplied challenge document
└── server/
    ├── .dockerignore                  Backend Docker build exclusions
    ├── .env.example                   Backend environment variable reference
    ├── ANALYSIS.md                    Snapshot analysis and API results
    ├── Dockerfile                     Backend container definition
    ├── __init__.py                    Python package marker
    ├── init.txt                       Backend setup note
    ├── requirements.txt               Pinned backend, fetcher, and test dependencies
    ├── app/
    │   ├── __init__.py                Python package marker
    │   ├── config.py                  Environment-based settings
    │   ├── main.py                    FastAPI application and metadata routes
    │   ├── schemas.py                 Typed API response models
    │   ├── routers/
    │   │   ├── __init__.py              Python package marker
    │   │   ├── accuracy.py             Accuracy endpoints
    │   │   ├── common.py               Shared request validation and snapshot access
    │   │   ├── decision.py             Decision endpoint
    │   │   └── forecast.py             Forecast and vintage endpoints
    │   └── services/
    │       ├── __init__.py              Python package marker
    │       ├── data_store.py           CSV loading and snapshot queries
    │       ├── decision.py             Prior-day buffer and procurement calculations
    │       ├── forecast.py             Target grids and forecast selection
    │       └── metrics.py              Accuracy metric calculations
    ├── data/
    │   ├── actuals.csv                FUELHH actual wind snapshot
    │   ├── data_quality.md            Snapshot counts and data-quality summary
    │   └── forecasts.csv              WINDFOR forecast vintages snapshot
    ├── scripts/
    │   └── fetch_data.py              Elexon snapshot fetch and report generation
    └── tests/                         Backend service and API tests
```

The `client/src/api/`, `hooks/`, `pages/`, `components/`, and `lib/` directories separate API calls, data fetching, screens, shared presentation, and formatting. The backend separates FastAPI routes from data and decision services.

## Getting started

### Prerequisites

- Python 3.12 for the backend, matching `server/Dockerfile`.
- Node.js 22 for the frontend container; use Node.js 22 locally as well.
- Docker with the Compose plugin for the Docker option.

### A. Docker

From the repository root:

```bash
docker compose up --build
```

Open the frontend at <http://localhost:8080>. The API docs are at <http://localhost:8000/docs>. Stop the services with:

```bash
docker compose down
```

### B. Local development

In one terminal, from the repository root, create and activate a virtual environment and install the backend requirements:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r server/requirements.txt
python -m uvicorn server.app.main:app --reload
```

The API docs are at <http://127.0.0.1:8000/docs>. On Debian or Ubuntu, install the matching `python3.12-venv` system package first if `venv` reports that `ensurepip` is unavailable.

In a second terminal:

```bash
cd client
npm install
npm run dev
```

Open the Vite development server at <http://localhost:5173>. Vite proxies `/api` requests to `http://127.0.0.1:8000`.

### C. Live deployment

Open <LIVE_APP_LINK> when the live deployment URL is available.

## Data snapshot

The checked-in snapshot is in `server/data/actuals.csv` and `server/data/forecasts.csv`; its quality summary is in [`server/data/data_quality.md`](server/data/data_quality.md). The API loads these files at startup and serves requests from memory.

The fetcher in `server/scripts/fetch_data.py` calls the Elexon BMRS `FUELHH/stream` endpoint with `settlementDateFrom`, `settlementDateTo`, and `fuelType=WIND`. It calls `WINDFOR/stream` with `publishDateTimeFrom` and `publishDateTimeTo`. Requests are chunked; the fetched rows are filtered, de-duplicated, and written to the CSV snapshot and quality report.

To refresh the snapshot from the repository root, first activate the local virtual environment and install `server/requirements.txt` as shown above, then run:

```bash
python server/scripts/fetch_data.py
```

The default fetch window is the January 2026 decision window. The script accepts `--decision-start` and `--decision-end`; corresponding environment variables are also supported. Refreshing calls the external Elexon API and overwrites the local snapshot files.

## Methodology and definitions

- **Decision and delivery dates:** Decision dates are January 1–31, 2026. Corresponding delivery dates are January 2–February 1, 2026.
- **Cutoff:** The default cutoff is 09:00 Europe/London on the day before delivery (D-1). The `cutoff` query parameter accepts `HH:MM` in that timezone. Timestamps in API responses are UTC.
- **Forecast selection:** For a target, decision-time views select the latest forecast whose `publishTime` is at or before the D-1 cutoff. Later vintages are excluded.
- **Forecast horizon:** `horizon_hours` is `(startTime - publishTime)` in hours. The all-vintage horizon view can include negative horizons; these are never eligible for the decision-time forecast.
- **Error sign:** `error_mw = forecast_mw - actual_mw`. A positive value means over-forecast; a negative value means under-forecast.
- **Metrics:** MAE is mean absolute error, RMSE is root mean squared error, and ME/bias is mean signed error, all in MW. MAPE is a percentage and excludes points where `abs(actual_mw) <= 1 MW`. WAPE is `sum(abs(error)) / sum(abs(actual)) * 100`. Absolute error percentiles are P50/P90/P95/P99; signed error percentiles are P5/P10/P50/P90/P95.
- **Coverage:** Decision-time accuracy is evaluated where an hourly WINDFOR forecast and actual are available. Coverage is evaluated points divided by the expected hourly forecast-grid points in the requested window. All-vintage horizon bucket coverage uses unique evaluated targets in that bucket over the expected hourly grid for the configured window; one target may appear in multiple buckets. The forecast endpoint still returns expected half-hour rows, with `forecast_mw`, `error_mw`, and horizon fields null and `forecast_missing=true` where no forecast exists. No interpolation is performed.
- **Decision buffer:** With `error = forecast - actual`, the conservative estimate is `max(forecast - Qq(prior-day errors), 0)`, with default `q=0.90`. Under a stable past error distribution, approximately q of actual values should be at least that estimate. Only earlier delivery days contribute errors. If fewer than `MINIMUM_BUFFER_SAMPLES` matched errors are available, the response status is `insufficient_history` and conservative wind equals the point forecast.
- **Measurement caveat:** FUELHH generation is an average MW over each half-hour. WINDFOR provides GB wind forecast values in MW and its interface definition describes them as peak wind generation. Both are national wind measures in MW, but the temporal statistics differ. Forecast targets in the snapshot are hourly, so evaluation uses matching hourly target starts without interpolating half-hour values.

## API reference

All routes return JSON and are prefixed with `/api`. Dates use `YYYY-MM-DD`; cutoff values use `HH:MM` in Europe/London; response timestamps are UTC. Defaults and accepted ranges are described in `/api/meta` and the OpenAPI docs.

| Method and path | Query parameters | Purpose |
|---|---|---|
| `GET /api/health` | — | Health check. |
| `GET /api/meta` | — | Configured dates, data coverage, resolution, and metric definitions. |
| `GET /api/forecast` | `delivery_date` required; `cutoff` optional | Latest eligible forecast and actuals on expected half-hour delivery timestamps. |
| `GET /api/forecast/vintages` | `target_time` required with timezone; `cutoff` optional | All stored forecast vintages for a target and cutoff eligibility. |
| `GET /api/accuracy/summary` | `start`, `end`, `cutoff` optional | Decision-time accuracy for a delivery-date range. |
| `GET /api/accuracy/by-horizon` | — | All-vintage accuracy grouped by forecast horizon. |
| `GET /api/accuracy/by-hour` | `cutoff` optional | Decision-time accuracy grouped by UTC and local target hour. |
| `GET /api/accuracy/daily` | `cutoff` optional | Decision-time metrics for each delivery day. |
| `GET /api/accuracy/distribution` | `bins` (1–100, default 20); `cutoff` optional | Histogram of decision-time signed errors. |
| `GET /api/accuracy/by-wind-level` | `start`, `end`, `cutoff` optional | Decision-time accuracy by actual-generation quartile. |
| `GET /api/decision` | `delivery_date`, `demand_mw` required; `cutoff` optional; `quantile` default 0.90, range 0–1 | Point and conservative procurement estimates. Demand must be greater than 0 and at most 200,000 MW. |

Examples:

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/meta
curl 'http://127.0.0.1:8000/api/forecast?delivery_date=2026-01-02&cutoff=09:00'
curl 'http://127.0.0.1:8000/api/accuracy/summary?start=2026-01-02&end=2026-02-01&cutoff=09:00'
curl 'http://127.0.0.1:8000/api/decision?delivery_date=2026-01-02&demand_mw=25000&quantile=0.9'
```

Invalid dates, cutoff formats, timezone-less vintage timestamps, out-of-range demand, and invalid quantiles return HTTP 422 with a validation detail. See <http://127.0.0.1:8000/docs> for interactive API documentation when the backend is running.

## Configuration

Backend defaults come from `server/app/config.py` and can be overridden with process environment variables. `server/.env.example` lists the same settings for reference; the application does not load that file automatically.

| Variable | Default | Purpose |
|---|---|---|
| `DECISION_START` | `2026-01-01` | First decision date. |
| `DECISION_END` | `2026-01-31` | Last decision date. |
| `DEFAULT_CUTOFF` | `09:00` | D-1 cutoff in local time. |
| `TIMEZONE` | `Europe/London` | Timezone for decision and delivery dates. |
| `ALLOWED_ORIGINS` | `*` | Comma-separated CORS origins, or `*`. |
| `MINIMUM_BUFFER_SAMPLES` | `30` | Minimum matched prior-day errors for the buffer. |
| `VITE_API_BASE_URL` | `/api` | Frontend API base path; change it when the API is hosted at another base URL. |

## Testing and build

From the repository root, install backend requirements in the active virtual environment and run:

```bash
python -m pip install -r server/requirements.txt
python -m pytest server/tests -q
```

For the frontend, from `client/`:

```bash
npm install
npm test
npm run lint
npm run build
```

## Deployment

The repository is configured as a single Vercel project: the build command creates the static client in `client/dist`, and `api/index.py` exports the FastAPI app as a Python function. `vercel.json` includes `server/data/**` with the function, routes `/api/...` to the function, and rewrites other paths to the client `index.html`. The root `requirements.txt` contains the Python runtime dependencies used for this deployment; local development, tests, and snapshot fetching use `server/requirements.txt` instead.

**Deployed app:  https://xk7qm2.vercel.app/

Docker is provided for local and reviewer use; the Vercel deployment uses its build and function configuration rather than the Dockerfiles. The live URL above is a placeholder, not a deployment claim.

## ScreenShots 
<img width="1903" height="962" alt="image" src="https://github.com/user-attachments/assets/58a5a28d-c909-42eb-b466-3825c14e3b32" />
<img width="1903" height="962" alt="image" src="https://github.com/user-attachments/assets/7e9e2e06-de13-4236-8225-a51e942327eb" />
<img width="1903" height="962" alt="image" src="https://github.com/user-attachments/assets/878e0890-c570-43bc-a579-6d2eb61dcad6" />



## Findings

- The January 2026 decision-time sample contains 744 hourly forecast/actual points, with 100.00% forecast-grid coverage.
- Mean error is +1,745.94 MW, indicating over-forecast on average; MAE is 2,022.47 MW and WAPE is 17.92%.
- The positive mean error appears across actual-wind quartiles; the time-shift analysis also retains a positive bias.
- See [`server/ANALYSIS.md`](server/ANALYSIS.md) for the detailed alignment checks, horizon and hour breakdowns, wind-level results, and decision example.

## Limitations and assumptions

- The analysis uses the January 2026 snapshot only; it does not establish performance in other periods.
- WINDFOR targets are hourly while FUELHH actuals are half-hourly. The API does not invent half-hour forecasts.
- The forecast and actual series have a peak-versus-average definitional difference described above.
- Demand is supplied by the user as a flat MW value; demand is not sourced from Elexon or forecast by this application.

## AI usage

OpenAI Codex was used as an AI coding assistant to help with implementation and documentation. The author reviewed and tested the output.
