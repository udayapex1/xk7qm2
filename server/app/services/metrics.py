from __future__ import annotations

from collections.abc import Iterable

import numpy as np


ABSOLUTE_PERCENTILES = (50, 90, 95, 99)
SIGNED_PERCENTILES = (5, 10, 50, 90, 95)
MAPE_NEAR_ZERO_MW = 1.0


def calculate_metrics(
    errors: Iterable[float],
    actuals: Iterable[float],
    expected_count: int | None = None,
    coverage_count: int | None = None,
) -> dict[str, object]:
    """Calculate error metrics and coverage against the expected forecast grid."""
    error_values = np.asarray(list(errors), dtype=float)
    actual_values = np.asarray(list(actuals), dtype=float)
    valid = np.isfinite(error_values) & np.isfinite(actual_values)
    error_values, actual_values = error_values[valid], actual_values[valid]
    count = len(error_values)
    coverage_denominator = expected_count if expected_count is not None else count
    coverage_numerator = count if coverage_count is None else coverage_count
    coverage = 100.0 * coverage_numerator / coverage_denominator if coverage_denominator else 0.0
    if not count:
        return {
            "sample_count": 0,
            "coverage_pct": coverage,
            "mae_mw": None,
            "rmse_mw": None,
            "mean_error_mw": None,
            "mape_pct": None,
            "wape_pct": None,
            "absolute_error_percentiles_mw": None,
            "signed_error_percentiles_mw": None,
        }

    absolute = np.abs(error_values)
    mape_mask = np.abs(actual_values) > MAPE_NEAR_ZERO_MW
    mape = (
        float(np.mean(absolute[mape_mask] / np.abs(actual_values[mape_mask])) * 100)
        if mape_mask.any()
        else None
    )
    actual_total = float(np.sum(np.abs(actual_values)))
    wape = float(np.sum(absolute) / actual_total * 100) if actual_total else None
    return {
        "sample_count": count,
        "coverage_pct": coverage,
        "mae_mw": float(np.mean(absolute)),
        "rmse_mw": float(np.sqrt(np.mean(np.square(error_values)))),
        "mean_error_mw": float(np.mean(error_values)),
        "mape_pct": mape,
        "wape_pct": wape,
        "absolute_error_percentiles_mw": {
            f"p{percentile}": float(np.percentile(absolute, percentile))
            for percentile in ABSOLUTE_PERCENTILES
        },
        "signed_error_percentiles_mw": {
            f"p{percentile}": float(np.percentile(error_values, percentile))
            for percentile in SIGNED_PERCENTILES
        },
    }


def paired_errors(frame) -> tuple[list[float], list[float]]:
    """Extract rows with both a forecast and an actual value."""
    paired = frame.dropna(subset=["error", "actual"])
    return paired["error"].astype(float).tolist(), paired["actual"].astype(float).tolist()
