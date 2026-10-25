# January 2026 wind forecast analysis

Computed from the committed Elexon BMRS FUELHH WIND and WINDFOR snapshot. Decision-time statistics select the latest forecast published by 09:00 Europe/London on D-1. All reported errors are forecast minus actual in MW.

## Snapshot and evaluation coverage

- Actuals: **1,488** half-hour rows, Jan 2 through Feb 1, 2026; 0 duplicate timestamps, 0 half-hour gaps, and **0 null generation values**.
- Forecasts: **17,864** unique `(startTime, publishTime)` rows; **0 null generation values**, 0 duplicate pairs. There are 256 publish times with spacing 120–240 minutes (median 180 minutes).
- Forecast target times range from 2026-01-02 00:00Z to 2026-02-01 23:00Z. Targets are hourly: **744 unique targets**.
- Decision-time evaluation uses the **hourly forecast grid**, not the half-hour actual grid: 744 evaluated forecast/actual points / 744 expected hourly targets = **100.00% coverage**. The forecast API still returns 1,488 expected half-hour rows; 744 have no forecast and remain null with `forecast_missing=true` (**50% half-hour row coverage**). No interpolation is performed.
- All-vintage forecast horizon ranges from **-25.5 to 66.5 hours**. Negative horizons are forecast vintages published after their target and are excluded from D-1 decisions.

## Is the positive bias an alignment artifact?

At the exact UTC `startTime` join, the selected decision-time sample has **744 points**, correlation **0.931614**, and mean error **+1,745.94 MW**. The result remains strongly positive at every tested half-hour shift from -2 to +2 hours:

| Actual shift relative to forecast target | Correlation | Mean error (MW) | Points |
|---:|---:|---:|---:|
| -120 min | 0.927037 | +1,713.35 | 742 |
| -90 min | 0.929819 | +1,717.69 | 742 |
| -60 min | 0.932027 | +1,729.92 | 743 |
| -30 min | **0.932066** | +1,734.05 | 743 |
| 0 min (exact `startTime`) | 0.931614 | +1,745.94 | 744 |
| +30 min | 0.929008 | +1,749.84 | 744 |
| +60 min | 0.925621 | +1,762.17 | 743 |
| +90 min | 0.920322 | +1,766.44 | 743 |
| +120 min | 0.914415 | +1,778.52 | 742 |

The maximum correlation is at -30 minutes, but its improvement over the exact timestamp join is only 0.000452; its mean bias remains +1.73 GW. This does not support changing the join. The exact join is retained because Elexon defines the timestamps as settlement/target period starts: FUELHH `startTime` is consistent with its settlement period (for example, settlement period 48 on Jan 2 starts at 23:30Z), and WINDFOR `startTime` is its forecast target period. The data is UTC-normalized before joining.

Elexon documents FUELHH as half-hourly generation outturn by fuel type, aggregated for Great Britain, with generation in **average MW over each 30-minute period**. WINDFOR is Great Britain wind-generation forecast data; Elexon's BMRS interface definition describes it as **forecast peak wind generation** with generation in **MW**. Thus both are national wind power in MW, not MWh or energy totals, but the temporal statistic is not identical: FUELHH is a half-hour average while WINDFOR is a peak forecast; the retained snapshot also has hourly forecast targets. We compare only coincident hourly target starts and make no half-hour interpolation. The measured over-forecast is robust to tested time shifts, but this one-month comparison cannot separate forecast error from the peak-versus-average definition difference.

Sources: [Elexon Insights API developer portal](https://developer.data.elexon.co.uk/) and [Elexon BSC interface definition for FUELHH and WINDFOR](https://bscdocs.elexon.co.uk/bsc-module/interface-definition-documents/neta-interface-definition-and-design-document-part-1-interfaces-with-bsc-parties-and-their-agents/v-57-0/id-67b34bd747c7f13fbb2970f5).

## Decision-time accuracy

The `/api/accuracy/summary` response reports the same metrics below. Coverage uses the hourly forecast grid (744 points), while half-hour rows without a forecast remain visible in `/api/forecast` as null and flagged.

| Metric | Result |
|---|---:|
| Evaluated sample count | 744 |
| Hourly forecast-grid coverage | 100.00% (744/744) |
| MAE | 2,022.47 MW |
| RMSE | 2,497.41 MW |
| Mean error | +1,745.94 MW |
| MAPE (absolute actual <= 1 MW excluded) | 21.85% |
| WAPE | 17.92% |
| Absolute error P50 / P90 / P95 / P99 | 1,655 / 4,154 / 5,268 / 6,139 MW |
| Signed error P5 / P10 / P50 / P90 / P95 | -1,039 / -426 / +1,582 / +4,154 / +5,268 MW |

## Bias by horizon and hour

The horizon values below match `/api/accuracy/by-horizon`, which intentionally includes every retained forecast vintage. Coverage in each bucket is the unique evaluated target timestamps represented in that bucket divided by the full 744-point hourly grid; the same target can occur in several vintage horizon buckets. The hour table matches `/api/accuracy/by-hour` and uses selected decision-time forecasts.

| All-vintage forecast horizon | Samples | Mean error (MW) | Coverage of hourly grid |
|---|---:|---:|---:|
| <0 h | 3,577 | +1,668.61 | 96.64% |
| 0–6 h | 1,446 | +1,455.49 | 97.45% |
| 6–12 h | 1,456 | +1,530.03 | 98.25% |
| 12–24 h | 2,954 | +1,710.81 | 99.87% |
| 24–36 h | 2,976 | +1,719.06 | 100.00% |
| 36–48 h | 2,945 | +1,900.10 | 100.00% |
| 48 h+ | 2,510 | +1,415.05 | 79.17% |

| Local target hour | Samples | Mean error (MW) | Local target hour | Samples | Mean error (MW) |
|---:|---:|---:|---:|---:|---:|
| 00 | 31 | +1,906.65 | 12 | 31 | +1,392.94 |
| 01 | 31 | +2,082.39 | 13 | 31 | +1,308.94 |
| 02 | 31 | +2,205.90 | 14 | 31 | +1,349.65 |
| 03 | 31 | +2,303.61 | 15 | 31 | +1,277.35 |
| 04 | 31 | +2,314.52 | 16 | 31 | +1,354.00 |
| 05 | 31 | +2,339.42 | 17 | 31 | +1,364.74 |
| 06 | 31 | +2,316.71 | 18 | 31 | +1,401.45 |
| 07 | 31 | +2,159.39 | 19 | 31 | +1,397.13 |
| 08 | 31 | +1,917.23 | 20 | 31 | +1,398.35 |
| 09 | 31 | +1,855.00 | 21 | 31 | +1,519.10 |
| 10 | 31 | +1,793.84 | 22 | 31 | +1,607.23 |
| 11 | 31 | +1,581.65 | 23 | 31 | +1,755.35 |

Bias is positive in every hour. It ranges from +1,277 MW at 15:00 to +2,339 MW at 05:00, so the result is not driven by one target hour.

## Accuracy by actual wind level

`/api/accuracy/by-wind-level` assigns evaluated hourly actual generation to quartiles over the requested window. Values and bounds below match the default-window live API response.

| Actual generation bucket | Bounds (MW) | Samples | MAE (MW) | Mean error (MW) |
|---|---:|---:|---:|---:|
| Q1 | 1,728–7,999 | 186 | 1,879.92 | +1,624.11 |
| Q2 | 7,999–11,429 | 186 | 1,597.98 | +916.20 |
| Q3 | 11,429–15,080.5 | 186 | 2,410.22 | +2,314.87 |
| Q4 | 15,080.5–17,805 | 186 | 2,201.76 | +2,128.57 |

All four quartiles have 100% coverage of their hourly-grid targets in this snapshot. The error is positive in each actual-wind band.

## Decision support and interpretation

Error is `forecast - actual`; positive means over-forecast. The decision endpoint now computes `conservative_wind = max(forecast - Q90(prior-day errors), 0)`. If the distribution is stable, approximately 90% of actuals should be at least this conservative estimate because `actual = forecast - error`. The Q90 uses only earlier delivery days. Before 30 matched prior points are available, the API reports `insufficient_history` and leaves conservative wind equal to the point forecast.

For the first Jan 4 target, the API uses 48 errors through Jan 3: forecast 16,572 MW and prior-error Q90 4,155.5 MW produce conservative wind 12,416.5 MW. At user-supplied demand 18,000 MW, point procurement is 1,428 MW and conservative procurement is 5,583.5 MW. This is a concrete positive-bias case where the conservative estimate lowers wind and raises procurement.

The largest decision-time daily MAE was **2026-01-28, 5,328.96 MW**; next were Jan 12 (4,875.42 MW) and Jan 11 (4,853.00 MW). The lowest was Jan 19 (683.63 MW). These are retrospective results from one month and do not establish the cause of forecast errors or provide a market recommendation. Demand remains a user-supplied flat value; no demand, price, weather, or other generation data is included.
