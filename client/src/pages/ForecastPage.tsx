import { useMemo, useState } from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useMeta } from '../hooks/useApi';
import { useForecast, useVintages } from '../hooks/useForecast';
import { useAccuracySummary } from '../hooks/useAccuracy';
import { ErrorBanner, Loading, MetricKpis, Panel } from '../components';
import { formatBias, formatNumber, formatTime } from '../lib/format';

export default function ForecastPage() {
  const { data: meta, error: metaError } = useMeta();
  const [date, setDate] = useState('2026-01-04');
  const [cutoff, setCutoff] = useState('09:00');
  const [query, setQuery] = useState({ date: '2026-01-04', cutoff: '09:00' });
  const { data, error, loading } = useForecast(query.date, query.cutoff);
  const accuracy = useAccuracySummary(query.cutoff);
  const [target, setTarget] = useState<string | null>(null);
  const vintage = useVintages(target, query.cutoff);
  const chart = useMemo(
    () =>
      data?.rows.map((r) => ({
        ...r,
        label: formatTime(r.start_time).split(' London')[0],
      })) ?? [],
    [data],
  );
  const dMinusOne = new Date(`${query.date}T12:00:00Z`);
  dMinusOne.setUTCDate(dMinusOne.getUTCDate() - 1);
  return (
    <main>
      <header className="page-title">
        <div>
          <p className="eyebrow">DAY-AHEAD WIND PROCUREMENT</p>
          <h1>Forecast overview</h1>
          <p>Latest national wind forecast available at the decision point.</p>
        </div>
      </header>
      <Panel title="Delivery controls">
        <form
          className="controls"
          onSubmit={(e) => {
            e.preventDefault();
            setQuery({ date, cutoff });
            setTarget(null);
          }}
        >
          <label>
            Delivery date
            <input
              aria-label="Delivery date"
              type="date"
              min={meta?.delivery_date_start}
              max={meta?.delivery_date_end}
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </label>
          <label>
            Decision cutoff ({meta?.timezone ?? 'Europe/London'})
            <input
              aria-label="Decision cutoff"
              type="time"
              value={cutoff}
              onChange={(e) => setCutoff(e.target.value)}
            />
          </label>
          <button>Show forecast</button>
        </form>
        <p className="hint">
          Decision made{' '}
          {dMinusOne.toLocaleDateString('en-GB', {
            timeZone: 'UTC',
            day: '2-digit',
            month: 'short',
            year: 'numeric',
          })}{' '}
          at {query.cutoff} London time
        </p>
      </Panel>
      <ErrorBanner message={metaError || error || accuracy.error} />
      {loading || accuracy.loading ? (
        <Loading />
      ) : (
        data &&
        accuracy.data && (
          <>
            <MetricKpis metrics={accuracy.data.metrics} includeCoverage />
            <Panel title="Actual and latest available forecast">
              <p className="hint">
                Select an hourly point to inspect all forecast vintages. Dashed
                amber line ends wherever forecasts are missing.
              </p>
              <div
                className="chart"
                role="img"
                aria-label="Line chart comparing actual wind generation and latest available forecast in megawatts by half-hour"
              >
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={chart}
                    onClick={(e) => {
                      const row = e?.activePayload?.[0]?.payload as
                        (typeof chart)[number] | undefined;
                      if (row) setTarget(row.start_time);
                    }}
                    margin={{ top: 10, right: 20, left: 0, bottom: 5 }}
                  >
                    <CartesianGrid stroke="#e7eeeb" />
                    <XAxis dataKey="label" minTickGap={32} />
                    <YAxis unit=" MW" width={86} />
                    <Tooltip
                      content={({ active, payload, label }) =>
                        active && payload?.[0] ? (
                          <div className="chart-tooltip">
                            <b>{label} London</b>
                            <br />
                            UTC {payload[0].payload.start_time}
                            <br />
                            Actual:{' '}
                            {formatNumber(payload[0].payload.actual_mw, 'MW')}
                            <br />
                            Forecast:{' '}
                            {formatNumber(payload[0].payload.forecast_mw, 'MW')}
                            <br />
                            Published:{' '}
                            {formatTime(payload[0].payload.publish_time, true)}
                            <br />
                            Horizon:{' '}
                            {formatNumber(
                              payload[0].payload.horizon_hours,
                              'h',
                            )}
                            <br />
                            Error: {formatBias(payload[0].payload.error_mw)}
                          </div>
                        ) : null
                      }
                    />
                    <Line
                      type="linear"
                      dataKey="actual_mw"
                      name="Actual"
                      stroke="#1d4ed8"
                      strokeWidth={2}
                      dot={false}
                      connectNulls={false}
                    />
                    <Line
                      type="linear"
                      dataKey="forecast_mw"
                      name="Forecast"
                      stroke="#b45309"
                      strokeWidth={2}
                      strokeDasharray="6 4"
                      dot={{ r: 2 }}
                      connectNulls={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="legend">
                <span className="blue-dot" /> Actual generation{' '}
                <span className="amber-dot" /> Latest available forecast
              </div>
              <div className="controls">
                <label>
                  Inspect target time
                  <select
                    aria-label="Inspect target time"
                    value={target ?? ''}
                    onChange={(e) => setTarget(e.target.value || null)}
                  >
                    <option value="">Choose a target time</option>
                    {data.rows.map((r) => (
                      <option key={r.start_time} value={r.start_time}>
                        {formatTime(r.start_time, true)}
                        {r.forecast_missing ? ' · no forecast' : ''}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Time (London)</th>
                      <th>Actual</th>
                      <th>Forecast</th>
                      <th>Published</th>
                      <th>Horizon</th>
                      <th>Error</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.rows.map((row) => (
                      <tr
                        key={row.start_time}
                        className={row.forecast_missing ? 'missing' : ''}
                        onClick={() => setTarget(row.start_time)}
                      >
                        <td>{formatTime(row.start_time, true)}</td>
                        <td>{formatNumber(row.actual_mw, 'MW')}</td>
                        <td>
                          {row.forecast_missing
                            ? 'Forecast gap'
                            : formatNumber(row.forecast_mw, 'MW')}
                        </td>
                        <td>{formatTime(row.publish_time)}</td>
                        <td>{formatNumber(row.horizon_hours, 'h')}</td>
                        <td>{formatBias(row.error_mw)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
            <Panel title="Why this forecast?">
              <p>
                The chart selects the latest forecast published at or before the
                decision cutoff on D−1. Forecasts published later are ignored,
                so there is no look-ahead. WINDFOR is hourly; half-hour points
                without a forecast remain gaps and are not interpolated.
              </p>
            </Panel>
            <Panel
              title="Vintage explorer"
              extra={
                target && (
                  <span className="hint">
                    Selected {formatTime(target, true)}
                  </span>
                )
              }
            >
              {!target ? (
                <p className="hint">
                  Select a chart point or choose a target time.
                </p>
              ) : vintage.loading ? (
                <Loading />
              ) : vintage.error ? (
                <ErrorBanner message={vintage.error} />
              ) : vintage.data?.forecasts.length ? (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Published (London)</th>
                        <th>Forecast</th>
                        <th>Horizon</th>
                        <th>Selection</th>
                      </tr>
                    </thead>
                    <tbody>
                      {vintage.data.forecasts.map((v) => (
                        <tr
                          key={v.publish_time}
                          className={
                            v.latest_available_at_cutoff ? 'chosen' : ''
                          }
                        >
                          <td>{formatTime(v.publish_time, true)}</td>
                          <td>{formatNumber(v.generation_mw, 'MW')}</td>
                          <td>{formatNumber(v.horizon_hours, 'h')}</td>
                          <td>
                            {v.latest_available_at_cutoff
                              ? 'Chosen at cutoff'
                              : new Date(v.publish_time) >
                                  new Date(v.cutoff_timestamp)
                                ? 'After cutoff'
                                : 'Earlier vintage'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : vintage.data ? (
                <p className="hint">
                  No forecast vintages exist for this target time.
                </p>
              ) : null}
            </Panel>
          </>
        )
      )}
    </main>
  );
}
