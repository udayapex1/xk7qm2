import { useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useMeta } from '../hooks/useApi';
import { useAccuracy } from '../hooks/useAccuracy';
import { ErrorBanner, Kpi, Loading, Panel } from '../components';
import { formatBias, formatNumber, formatPct } from '../lib/format';
export default function AccuracyPage() {
  const { data: meta } = useMeta();
  const [range, setRange] = useState({
    start: '2026-01-02',
    end: '2026-02-01',
    cutoff: '09:00',
  });
  const [query, setQuery] = useState(range);
  const { data, error, loading } = useAccuracy(
    query.start,
    query.end,
    query.cutoff,
  );
  return (
    <main>
      <header className="page-title">
        <div>
          <p className="eyebrow">MODEL PERFORMANCE</p>
          <h1>Forecast accuracy</h1>
          <p>
            Decision-time performance uses the latest eligible forecast; horizon
            view includes all retained vintages.
          </p>
        </div>
      </header>
      <Panel title="Evaluation window">
        <form
          className="controls"
          onSubmit={(e) => {
            e.preventDefault();
            setQuery(range);
          }}
        >
          <label>
            From
            <input
              aria-label="From date"
              type="date"
              min={meta?.delivery_date_start}
              max={meta?.delivery_date_end}
              value={range.start}
              onChange={(e) => setRange({ ...range, start: e.target.value })}
            />
          </label>
          <label>
            To
            <input
              aria-label="To date"
              type="date"
              min={meta?.delivery_date_start}
              max={meta?.delivery_date_end}
              value={range.end}
              onChange={(e) => setRange({ ...range, end: e.target.value })}
            />
          </label>
          <label>
            Cutoff ({meta?.timezone ?? 'Europe/London'})
            <input
              aria-label="Cutoff"
              type="time"
              value={range.cutoff}
              onChange={(e) => setRange({ ...range, cutoff: e.target.value })}
            />
          </label>
          <button>Update analysis</button>
        </form>
      </Panel>
      <ErrorBanner message={error} />
      {loading ? (
        <Loading />
      ) : (
        data && (
          <>
            <div className="kpis">
              <Kpi
                label="MAE"
                value={formatNumber(data[0].metrics.mae_mw, 'MW')}
              />
              <Kpi
                label="RMSE"
                value={formatNumber(data[0].metrics.rmse_mw, 'MW')}
              />
              <Kpi
                label="Bias"
                value={formatBias(data[0].metrics.mean_error_mw)}
              />
              <Kpi label="WAPE" value={formatPct(data[0].metrics.wape_pct)} />
              <Kpi
                label="Samples / coverage"
                value={`${formatNumber(data[0].metrics.sample_count)} / ${formatPct(data[0].metrics.coverage_pct)}`}
              />
            </div>
            <div className="grid2">
              <Panel title="Absolute error by forecast horizon">
                <div className="chart small">
                  <ResponsiveContainer>
                    <BarChart data={data[1].buckets}>
                      <CartesianGrid stroke="#e7eeeb" />
                      <XAxis dataKey="bucket" />
                      <YAxis unit=" MW" />
                      <Tooltip
                        formatter={(v) => formatNumber(Number(v), 'MW')}
                      />
                      <Bar dataKey="metrics.mae_mw" name="MAE" fill="#0f766e" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <p className="hint">
                  All-vintage horizon view. Coverage is unique target timestamps
                  per bucket over the hourly expected grid.
                </p>
              </Panel>
              <Panel title="Bias by hour of day">
                <div className="chart small">
                  <ResponsiveContainer>
                    <LineChart data={data[2].local}>
                      <CartesianGrid stroke="#e7eeeb" />
                      <XAxis dataKey="hour" />
                      <YAxis unit=" MW" />
                      <Tooltip formatter={(v) => formatBias(Number(v))} />
                      <ReferenceLine y={0} stroke="#687872" />
                      <Line
                        dataKey="metrics.mean_error_mw"
                        name="Bias"
                        stroke="#0f766e"
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <p className="hint">Local hour, Europe/London</p>
              </Panel>
              <Panel title="Daily MAE and bias">
                <div className="chart small">
                  <ResponsiveContainer>
                    <LineChart data={data[3].days}>
                      <CartesianGrid stroke="#e7eeeb" />
                      <XAxis dataKey="delivery_date" minTickGap={24} />
                      <YAxis unit=" MW" />
                      <Tooltip
                        formatter={(v) => formatNumber(Number(v), 'MW')}
                      />
                      <Line
                        dataKey="metrics.mae_mw"
                        name="MAE"
                        stroke="#1d4ed8"
                        dot={false}
                      />
                      <Line
                        dataKey="metrics.mean_error_mw"
                        name="Bias"
                        stroke="#b45309"
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </Panel>
              <Panel title="Signed error distribution">
                <div className="chart small">
                  <ResponsiveContainer>
                    <BarChart data={data[4].bins}>
                      <CartesianGrid stroke="#e7eeeb" />
                      <XAxis
                        dataKey="lower_error_mw"
                        tickFormatter={(v) =>
                          `${Math.round(Number(v) / 1000)}k`
                        }
                        minTickGap={26}
                      />
                      <YAxis />
                      <Tooltip
                        labelFormatter={(v) =>
                          `From ${formatNumber(Number(v), 'MW')}`
                        }
                      />
                      <Bar dataKey="count" fill="#0f766e" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <p className="hint">
                  Mean signed error: {formatBias(data[0].metrics.mean_error_mw)}{' '}
                  <span className="marker" />
                </p>
              </Panel>
            </div>
            <Panel title="Accuracy by actual wind level">
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Quartile</th>
                      <th>Actual generation bounds</th>
                      <th>Samples</th>
                      <th>Coverage</th>
                      <th>MAE</th>
                      <th>Bias</th>
                      <th>P90 absolute error</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data[5].buckets.map((b) => (
                      <tr key={b.bucket}>
                        <td>{b.bucket}</td>
                        <td>
                          {formatNumber(b.lower_actual_mw)}–
                          {formatNumber(b.upper_actual_mw)} MW
                        </td>
                        <td>{b.metrics.sample_count}</td>
                        <td>{formatPct(b.metrics.coverage_pct)}</td>
                        <td>{formatNumber(b.metrics.mae_mw, 'MW')}</td>
                        <td>{formatBias(b.metrics.mean_error_mw)}</td>
                        <td>
                          {formatNumber(
                            b.metrics.absolute_error_percentiles_mw?.p90,
                            'MW',
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
            <Panel title="Absolute error percentiles">
              {['p50', 'p90', 'p95', 'p99'].map((k) => (
                <span className="percentile" key={k}>
                  <b>{k.toUpperCase()}</b>{' '}
                  {formatNumber(
                    data[0].metrics.absolute_error_percentiles_mw?.[k],
                    'MW',
                  )}
                </span>
              ))}
            </Panel>
            <Panel title="Metric guide">
              <p>
                <strong>{meta?.error_definition}</strong>
              </p>
              <ul>
                {Object.entries(meta?.metric_definitions ?? {}).map(
                  ([k, v]) => (
                    <li key={k}>
                      <b>{k}:</b> {v}
                    </li>
                  ),
                )}
              </ul>
            </Panel>
          </>
        )
      )}
    </main>
  );
}
