# January 2026 wind forecast analysis

This analysis was computed from the committed Elexon BMRS FUELHH WIND actuals and WINDFOR forecasts using the application’s default `09:00 Europe/London` D-1 cutoff. The decision-time summary uses delivery dates 2026-01-02 through 2026-02-01. This is a descriptive pilot result, not a market recommendation.

## Snapshot and coverage

- Actuals: **1,488** half-hour rows, covering 2026-01-02 00:00Z through 2026-02-01 23:30Z. No duplicate actual timestamps or 30-minute gaps were found.
- Forecasts: **17,864** unique `(startTime, publishTime)` rows targeting the same delivery window; no duplicates were removed.
- There are **256** unique publish times. Observed spacing is **2 hours minimum, 3 hours median, 4 hours maximum**.
- Forecast horizon (`startTime - publishTime`) ranges from **-25.5 to 66.5 hours** across all stored vintages.
- The unique WINDFOR target times are hourly rather than half-hourly in this snapshot: **744 of 1,488 expected half-hour targets** have at least one forecast, yielding **50% decision-time coverage**. The unforecast half-hours are left missing; no interpolation was done.

## Decision-time accuracy

| Metric | Result |
|---|---:|
| Paired sample count | 744 |
| Coverage | 50.00% |
| MAE | 2,022.47 MW |
| RMSE | 2,497.41 MW |
| Mean error (forecast - actual) | +1,745.94 MW |
| MAPE (actuals within the 1 MW guard excluded) | 21.85% |
| WAPE | 17.92% |
| Absolute error P50 / P90 / P95 / P99 | 1,655 / 4,154 / 5,268 / 6,139 MW |
| Signed error P5 / P10 / P50 / P90 / P95 | -1,039 / -426 / +1,582 / +4,154 / +5,268 MW |

The mean and median signed errors are positive, so this particular latest-at-cutoff sample **over-forecasts wind on average** under the chosen convention. That could lead a buyer to understate additional procurement if the point forecast were used without adjustment. It does not establish why the error occurred.

## Accuracy across all vintages by horizon

These buckets use every retained WINDFOR vintage with an exact `startTime` actual match; they are not the buyer’s single latest-at-cutoff forecast. Negative horizons are separated because they describe forecasts published after the target time.

| Horizon | Samples | MAE (MW) | Mean error (MW) |
|---|---:|---:|---:|
| `<0h` | 3,577 | 1,803.94 | +1,668.61 |
| `0-6h` | 1,446 | 1,681.34 | +1,455.49 |
| `6-12h` | 1,456 | 1,752.44 | +1,530.03 |
| `12-24h` | 2,954 | 1,891.83 | +1,710.81 |
| `24-36h` | 2,976 | 2,004.17 | +1,719.06 |
| `36-48h` | 2,945 | 2,233.83 | +1,900.10 |
| `48h+` | 2,510 | 2,307.40 | +1,415.05 |

For non-negative horizons, MAE rises from 1,681 MW in the 0-6 hour bucket to 2,307 MW in the 48+ hour bucket. These all-vintage results include many intra-day revisions and should not be compared directly with the 744 decision-time samples.

## Time and notable days

- Highest daily MAE: **2026-01-28, 5,328.96 MW** (positive mean error).
- Next highest: **2026-01-12, 4,875.42 MW**, and **2026-01-11, 4,853.00 MW** (both positive mean error).
- Lowest daily MAE: **2026-01-19, 683.63 MW** (mean error -683.63 MW).
- Of 24 UTC hours, 05:00 had the largest hour-of-day MAE at approximately **2,414 MW**; these hour metrics use the 09:00 D-1 latest forecast and omit missing half-hour pairs.

## Interpretation and limits

The strongest practical caveat is forecast coverage: the actuals are half-hourly while the returned wind forecast targets in this dataset are hourly. The API reports all 48 expected half-hour rows and preserves missing forecast values, so coverage remains visible instead of silently treating an hourly value as a half-hour value. Forecast publication updates were observed every 2–4 hours, but a particular target's latest vintage at the cutoff can be older.

Error is always `forecast - actual`; positive means over-forecast. The decision endpoint follows the requested formula of adding a historical signed-error quantile (P10 by default) to the point forecast and clipping it at zero. On 2026-01-04, for example, that historical P10 was +1,128.3 MW; adding it increases estimated wind, so the operation is not conservative for positive quantiles under this sign convention. The response explicitly warns about this sign interaction. A truly conservative low-wind estimate under `forecast - actual` would subtract a high-side forecast-error quantile, which differs from the requested formula. The endpoint only learns from earlier delivery days and uses no buffer when there are fewer than 30 prior matched points. Demand is user-provided, not sourced from Elexon. No weather, demand, price, or other generation data is included.
