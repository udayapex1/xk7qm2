import { useMemo, useState } from 'react';
import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  ReferenceLine,
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
  const chart = useMemo(() => {
    let forecastSegment = 0;
    return (data?.rows ?? []).map((row) => {
      const hasForecast =
        typeof row.forecast_mw === 'number' && !row.forecast_missing;
      if (!hasForecast && new Date(row.start_time).getUTCMinutes() === 0) {
        forecastSegment += 1;
      }
      return {
        ...row,
        label: new Date(row.start_time).toLocaleTimeString('en-GB', {
          timeZone: 'Europe/London',
          hour: '2-digit',
          minute: '2-digit',
          hourCycle: 'h23',
        }),
        forecast_segment: forecastSegment,
        [`forecast_${forecastSegment}`]: hasForecast ? row.forecast_mw : null,
        [`error_band_${forecastSegment}`]:
          hasForecast && typeof row.actual_mw === 'number'
            ? [
                Math.min(row.actual_mw, row.forecast_mw as number),
                Math.max(row.actual_mw, row.forecast_mw as number),
              ]
            : null,
      };
    });
  }, [data]);
  const forecastSegments = useMemo(
    () => [...new Set(chart.map((row) => row.forecast_segment))],
    [chart],
  );
  const timeTicks = useMemo(
    () =>
      chart
        .filter((_, index) => index % 8 === 0 || index === chart.length - 2)
        .map((row) => row.label),
    [chart],
  );
  const dailyBias = useMemo(() => {
    const errors =
      data?.rows
        .map((row) => row.error_mw)
        .filter(
          (error): error is number => error !== null && error !== undefined,
        ) ?? [];
    return errors.length
      ? errors.reduce((sum, error) => sum + error, 0) / errors.length
      : null;
  }, [data]);
  const yMinimum = useMemo(() => {
    const values = chart
      .flatMap((row) => [row.actual_mw, row.forecast_mw])
      .filter(
        (value): value is number => value !== null && value !== undefined,
      );
    return values.length ? Math.floor(Math.min(...values) / 1000) * 1000 : 0;
  }, [chart]);
  const hourlyBias = useMemo(
    () =>
      Array.from({ length: 24 }, (_, hour) => {
        const errors =
          data?.rows
            .filter(
              (row) =>
                new Date(row.start_time).toLocaleString('en-GB', {
                  timeZone: 'Europe/London',
                  hour: '2-digit',
                  hourCycle: 'h23',
                }) === String(hour).padStart(2, '0') && row.error_mw !== null,
            )
            .map((row) => row.error_mw as number) ?? [];
        return {
          hour: `${String(hour).padStart(2, '0')}:00`,
          bias: errors.length
            ? errors.reduce((sum, error) => sum + error, 0) / errors.length
            : null,
        };
      }),
    [data],
  );
  const biasShare =
    accuracy.data?.metrics.mae_mw &&
    accuracy.data.metrics.mean_error_mw !== null
      ? Math.round(
          (100 * Math.abs(accuracy.data.metrics.mean_error_mw)) /
            accuracy.data.metrics.mae_mw,
        )
      : 0;
  const weekday = new Date(`${query.date}T12:00:00Z`).toLocaleDateString(
    'en-GB',
    { weekday: 'long', day: 'numeric', month: 'short', timeZone: 'UTC' },
  );
  const biasHeadline =
    dailyBias === null || Math.abs(dailyBias) < 100
      ? `The forecast was close on ${weekday}`
      : `The forecast ran ${Math.abs(dailyBias / 1000).toFixed(1)} GW ${dailyBias > 0 ? 'too high' : 'too low'} on ${weekday}`;
  const dMinusOne = new Date(`${query.date}T12:00:00Z`);
  dMinusOne.setUTCDate(dMinusOne.getUTCDate() - 1);
  return (
    <main>
      <header className="page-title hero-layout">
        <div className="hero-copy">
          <p className="eyebrow">DAY-AHEAD WIND PROCUREMENT</p>
          <h1>{biasHeadline}</h1>
          <p>
            Latest national wind forecast available at the decision point,
            compared with what the wind actually delivered.
          </p>
        </div>
        <Panel
          title="Delivery date and decision cutoff"
          className="hero-controls"
        >
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
              Decision cutoff · London
              <input
                aria-label="Decision cutoff"
                type="time"
                value={cutoff}
                onChange={(e) => setCutoff(e.target.value)}
              />
            </label>
            <button>Update</button>
          </form>
          <p className="hint">
            Decision made{' '}
            {dMinusOne.toLocaleDateString('en-GB', {
              timeZone: 'UTC',
              day: 'numeric',
              month: 'short',
            })}
            , {query.cutoff}
          </p>
        </Panel>
      </header>
      <ErrorBanner message={metaError || error || accuracy.error} />
      {loading || accuracy.loading ? (
        <Loading />
      ) : (
        data &&
        accuracy.data && (
          <>
            <div className="scope-row">
              <span className="scope-tag">January 2026, all decision days</span>
            </div>
            <MetricKpis
              metrics={accuracy.data.metrics}
              includeCoverage
              forecastCaptions
            />
            <Panel
              title="Actual vs latest available forecast"
              className="forecast-chart-panel"
              extra={
                <div className="chart-legend">
                  <span>
                    <i className="legend-line actual-line" />
                    Actual
                  </span>
                  <span>
                    <i className="legend-line forecast-line" />
                    Forecast
                  </span>
                  <span>
                    <i className="legend-band" />
                    Forecast error
                  </span>
                </div>
              }
            >
              <p className="hint">
                Select a point to inspect forecast vintages. Vertical axis
                starts at {formatNumber(yMinimum, 'MW')}.
              </p>
              <div
                className="chart"
                role="img"
                aria-label="Line chart comparing actual wind generation and latest available forecast in megawatts by half-hour"
              >
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart
                    data={chart}
                    onClick={(e) => {
                      const row = e?.activePayload?.[0]?.payload as
                        (typeof chart)[number] | undefined;
                      if (row) setTarget(row.start_time);
                    }}
                    margin={{ top: 10, right: 20, left: 0, bottom: 5 }}
                  >
                    <CartesianGrid stroke="#e7eeeb" />
                    <XAxis dataKey="label" ticks={timeTicks} interval={0} />
                    <YAxis width={58} domain={[yMinimum, 'auto']} />
                    <Tooltip
                      content={({ active, payload, label }) =>
                        active && payload?.[0] ? (
                          <div className="chart-tooltip dark-tooltip">
                            <b>{label} London</b>
                            <br />
                            Forecast{' '}
                            {formatNumber(payload[0].payload.forecast_mw, 'MW')}
                            <br />
                            Actual{' '}
                            {formatNumber(payload[0].payload.actual_mw, 'MW')}
                            <br />
                            UTC {payload[0].payload.start_time}
                          </div>
                        ) : null
                      }
                    />
                    {forecastSegments.map((segment) => (
                      <Area
                        key={`band-${segment}`}
                        dataKey={`error_band_${segment}`}
                        name="Forecast error"
                        stroke="none"
                        fill="#e77d3c"
                        fillOpacity={0.18}
                        connectNulls
                        isAnimationActive={false}
                      />
                    ))}
                    <Line
                      type="linear"
                      dataKey="actual_mw"
                      name="Actual"
                      stroke="#7138c8"
                      strokeWidth={2}
                      dot={false}
                      connectNulls
                      isAnimationActive={false}
                    />
                    {forecastSegments.map((segment) => (
                      <Line
                        key={`forecast-${segment}`}
                        type="linear"
                        dataKey={`forecast_${segment}`}
                        name="Forecast"
                        stroke="#d9682b"
                        strokeWidth={2}
                        strokeDasharray="6 4"
                        dot={false}
                        connectNulls
                        isAnimationActive={false}
                      />
                    ))}
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </Panel>
            <div className="forecast-bottom-grid">
              <Panel title="Hourly bias">
                <p className="hint">
                  Forecast minus actual. Every bar above the line means
                  over-forecast.
                </p>
                <div
                  className="chart small"
                  role="img"
                  aria-label="Hourly average forecast bias in megawatts"
                >
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={hourlyBias}>
                      <CartesianGrid stroke="#edf1ef" />
                      <XAxis dataKey="hour" minTickGap={25} />
                      <YAxis hide />
                      <Tooltip
                        formatter={(value) => formatBias(Number(value))}
                      />
                      <ReferenceLine y={0} stroke="#60736b" />
                      <Bar
                        dataKey="bias"
                        name="Mean bias"
                        fill="#d9682b"
                        isAnimationActive={false}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Panel>
              <section className="insight-card">
                <p className="eyebrow">WHAT THIS MEANS</p>
                <h2>
                  {biasShare >= 50
                    ? 'The error is mostly bias, not noise.'
                    : 'The error is mostly noise, not bias.'}
                </h2>
                <p>
                  About {biasShare}% of average miss is consistent signed bias.
                  The bias direction is{' '}
                  {(accuracy.data.metrics.mean_error_mw ?? 0) > 0
                    ? 'over-forecast'
                    : 'under-forecast'}
                  .
                </p>
                <a
                  className="button-light"
                  href={`/decision?date=${query.date}`}
                >
                  Open decision helper
                </a>
              </section>
            </div>
            <Panel title="Why this forecast?" className="secondary-panel">
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
              <label className="vintage-time-control">
                Inspect a target time
                <select
                  aria-label="Inspect target time"
                  value={target ?? ''}
                  onChange={(e) => setTarget(e.target.value || null)}
                >
                  <option value="">Choose a target time</option>
                  {data.rows.map((row) => (
                    <option key={row.start_time} value={row.start_time}>
                      {formatTime(row.start_time, true)}
                      {row.forecast_missing ? ' · no forecast' : ''}
                    </option>
                  ))}
                </select>
              </label>
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
