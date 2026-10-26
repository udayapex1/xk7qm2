import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import App from '../App';
const metrics = {
  sample_count: 1,
  coverage_pct: 100,
  mae_mw: 100,
  rmse_mw: 100,
  mean_error_mw: 50,
  mape_pct: 2,
  wape_pct: 1,
  absolute_error_percentiles_mw: { p50: 60, p90: 90, p95: 95, p99: 99 },
  signed_error_percentiles_mw: { p50: 50, p90: 90 },
};
const meta = {
  decision_date_start: '2026-01-01',
  decision_date_end: '2026-01-31',
  delivery_date_start: '2026-01-02',
  delivery_date_end: '2026-02-01',
  default_cutoff: '09:00',
  timezone: 'Europe/London',
  actual_rows: 1488,
  actual_expected_points: 1488,
  actual_coverage_pct: 100,
  forecast_rows: 17864,
  forecast_grid_expected_points: 744,
  forecast_grid_evaluated_points: 744,
  forecast_grid_coverage_pct: 100,
  forecast_grid_resolution: 'Hourly WINDFOR targets; actuals are half-hourly.',
  half_hour_missing_forecast_behavior: 'Null and flagged.',
  actual_start_time: null,
  actual_end_time: null,
  forecast_publish_start: null,
  forecast_publish_end: null,
  error_definition:
    'error_mw = forecast_mw - actual_mw; positive means over-forecast.',
  metric_definitions: { MAE: 'Mean absolute error.' },
};
const row = {
  start_time: '2026-01-04T00:00:00Z',
  actual_mw: 1000,
  forecast_mw: 1100,
  publish_time: '2026-01-03T07:30:00Z',
  horizon_hours: 16.5,
  error_mw: 100,
  forecast_missing: false,
};
function payload(url: string) {
  const path = new URL(url).pathname;
  if (path.endsWith('/meta')) return meta;
  if (path.endsWith('/forecast/vintages'))
    return {
      target_time: row.start_time,
      delivery_date: '2026-01-04',
      cutoff_timestamp: '2026-01-03T09:00:00Z',
      selection_rule: 'Maximum publish_time',
      forecasts: [
        {
          start_time: row.start_time,
          publish_time: row.publish_time,
          generation_mw: 1100,
          horizon_hours: 16.5,
          latest_available_at_cutoff: true,
          cutoff_timestamp: '2026-01-03T09:00:00Z',
        },
      ],
    };
  if (path.endsWith('/forecast'))
    return {
      delivery_date: '2026-01-04',
      cutoff_timestamp: '2026-01-03T09:00:00Z',
      cutoff_timezone: 'Europe/London',
      rows: [row],
      summary: metrics,
    };
  if (path.endsWith('/accuracy/summary'))
    return {
      start_date: '2026-01-02',
      end_date: '2026-02-01',
      cutoff: '09:00',
      cutoff_timezone: 'Europe/London',
      evaluation_grid: 'Hourly',
      metrics,
    };
  if (path.endsWith('/accuracy/by-horizon'))
    return {
      scope: 'all vintages',
      coverage_definition: 'grid',
      buckets: [{ bucket: '12-24h', metrics }],
    };
  if (path.endsWith('/accuracy/by-hour'))
    return {
      cutoff: '09:00',
      utc: [{ hour: 0, metrics }],
      local: [{ hour: 0, metrics }],
    };
  if (path.endsWith('/accuracy/daily'))
    return {
      cutoff: '09:00',
      days: [{ delivery_date: '2026-01-04', metrics }],
    };
  if (path.endsWith('/accuracy/distribution'))
    return {
      sample_count: 1,
      error_definition: 'forecast - actual',
      bins: [{ lower_error_mw: 0, upper_error_mw: 100, count: 1 }],
    };
  if (path.endsWith('/accuracy/by-wind-level'))
    return {
      start_date: '2026-01-02',
      end_date: '2026-02-01',
      cutoff: '09:00',
      bucket_method: 'quartiles',
      buckets: [
        { bucket: 'Q1', lower_actual_mw: 0, upper_actual_mw: 1000, metrics },
      ],
    };
  if (path.endsWith('/decision'))
    return {
      delivery_date: '2026-01-04',
      cutoff_timestamp: '2026-01-03T09:00:00Z',
      demand_source: 'user_supplied_flat_demand_mw',
      demand_mw: 18000,
      error_quantile: 0.9,
      historical_error_quantile_mw: 50,
      buffer_sample_count: 30,
      buffer_history_end_date: '2026-01-03',
      buffer_status: 'historical_quantile',
      buffer_note: 'Prior-day errors only.',
      rows: [
        {
          ...row,
          demand_mw: 18000,
          conservative_wind_mw: 1050,
          additional_power_point_mw: 16900,
          additional_power_conservative_mw: 16950,
        },
      ],
    };
  return { status: 'ok' };
}
beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn((input: RequestInfo | URL) =>
      Promise.resolve(
        new Response(JSON.stringify(payload(String(input))), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    ),
  );
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
function mount(path: string) {
  return render(
    <MemoryRouter
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      initialEntries={[path]}
    >
      <Routes>
        <Route path="*" element={<App />} />
      </Routes>
    </MemoryRouter>,
  );
}
describe('page rendering with API data', () => {
  it('renders forecast page and opens vintages on selection', async () => {
    mount('/');
    expect(
      await screen.findByText(/The forecast ran .* on Sunday 4 Jan/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Actual vs latest available forecast/),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Inspect target time'), {
      target: { value: row.start_time },
    });
    expect(await screen.findByText('Vintage explorer')).toBeInTheDocument();
    expect(await screen.findByText('Chosen at cutoff')).toBeInTheDocument();
  });
  it('renders the accuracy dashboard from API metrics', async () => {
    mount('/accuracy');
    expect(
      await screen.findByText(
        'How the forecast performs across the delivery window',
      ),
    ).toBeInTheDocument();
    expect(
      await screen.findByText('Accuracy by actual wind level'),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/positive means over-forecast/),
    ).toBeInTheDocument();
  });
  it('renders the decision helper after calculation', async () => {
    mount('/decision');
    fireEvent.click(screen.getByRole('button', { name: 'Calculate' }));
    expect(
      await screen.findByText('Procurement comparison'),
    ).toBeInTheDocument();
    expect(screen.getByText('With safety buffer')).toBeInTheDocument();
  });
});
