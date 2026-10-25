import { useState } from 'react';
import { useMeta } from '../hooks/useApi';
import { useDecision } from '../hooks/useDecision';
import { ErrorBanner, Loading, Panel } from '../components';
import { formatNumber } from '../lib/format';
function CompareBar({
  label,
  wind,
  buy,
  demand,
}: {
  label: string;
  wind: number;
  buy: number;
  demand: number;
}) {
  return (
    <div className="compare">
      <b>{label}</b>
      <div
        className="bar-track"
        role="img"
        aria-label={`${label}: wind ${formatNumber(wind, 'MW')}, additional power ${formatNumber(buy, 'MW')}, demand ${formatNumber(demand, 'MW')}`}
      >
        <div
          className="wind-fill"
          style={{ width: `${Math.min(100, (wind / demand) * 100)}%` }}
        />
        <div
          className="buy-fill"
          style={{
            left: `${Math.min(100, (wind / demand) * 100)}%`,
            width: `${Math.max(0, Math.min(100, (buy / demand) * 100))}%`,
          }}
        />
      </div>
      <small>
        Wind {formatNumber(wind, 'MW')} · Buy {formatNumber(buy, 'MW')} · Demand{' '}
        {formatNumber(demand, 'MW')}
      </small>
    </div>
  );
}
export default function DecisionPage() {
  const { data: meta } = useMeta();
  const [date, setDate] = useState('2026-01-04');
  const [demand, setDemand] = useState('18000');
  const [quantile, setQuantile] = useState('0.90');
  const [query, setQuery] = useState<{
    date: string;
    demand: number;
    q: number;
  } | null>(null);
  const { data, error, loading } = useDecision(
    query?.date ?? date,
    query?.demand ?? Number(demand),
    meta?.default_cutoff ?? '09:00',
    query?.q ?? Number(quantile),
    !!query,
  );
  return (
    <main>
      <header className="page-title">
        <div>
          <p className="eyebrow">PROCUREMENT SUPPORT</p>
          <h1>Decision helper</h1>
          <p>
            Compare forecast-led procurement with a prior-error safety buffer.
          </p>
        </div>
      </header>
      <Panel title="Decision inputs">
        <form
          className="controls"
          onSubmit={(e) => {
            e.preventDefault();
            setQuery({ date, demand: Number(demand), q: Number(quantile) });
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
            Demand (MW){' '}
            <span className="hint">entered by you, not from Elexon</span>
            <input
              aria-label="Demand MW entered by you, not from Elexon"
              type="number"
              min="1"
              max="200000"
              step="1"
              value={demand}
              onChange={(e) => setDemand(e.target.value)}
            />
          </label>
          <label>
            Safety level quantile
            <input
              aria-label="Safety level quantile"
              type="number"
              min="0"
              max="1"
              step="0.01"
              value={quantile}
              onChange={(e) => setQuantile(e.target.value)}
            />
          </label>
          <button>Calculate</button>
        </form>
      </Panel>
      <ErrorBanner message={error} />
      {loading ? (
        <Loading />
      ) : (
        query &&
        data && (
          <Panel title="Procurement comparison">
            {data.buffer_status === 'insufficient_history' && (
              <div className="banner">
                Insufficient prior-day history is available for this date.
                Conservative estimates are not calculated.
              </div>
            )}
            <div className="decision-grid">
              {data.rows
                .filter((r) => r.forecast_mw !== null)
                .slice(0, 4)
                .map((r) => (
                  <div className="decision-time" key={r.start_time}>
                    <h3>
                      {new Date(r.start_time).toLocaleTimeString('en-GB', {
                        timeZone: 'Europe/London',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}{' '}
                      London
                    </h3>
                    <CompareBar
                      label="Forecast as is"
                      wind={r.forecast_mw ?? 0}
                      buy={r.additional_power_point_mw ?? 0}
                      demand={r.demand_mw}
                    />
                    {data.buffer_status !== 'insufficient_history' &&
                      r.conservative_wind_mw !== null &&
                      r.additional_power_conservative_mw !== null && (
                        <CompareBar
                          label="With safety buffer"
                          wind={r.conservative_wind_mw}
                          buy={r.additional_power_conservative_mw}
                          demand={r.demand_mw}
                        />
                      )}
                  </div>
                ))}
            </div>
            {data.buffer_status !== 'insufficient_history' && (
              <div className="buffer-summary">
                <b>Buffer:</b>{' '}
                {formatNumber(data.historical_error_quantile_mw, 'MW')} ·{' '}
                <b>Prior-day samples:</b> {data.buffer_sample_count} ·{' '}
                <b>History dates:</b>{' '}
                {data.buffer_history_end_date
                  ? `${meta?.delivery_date_start ?? '—'} to ${data.buffer_history_end_date}`
                  : '—'}{' '}
                · <b>Quantile:</b> {Math.round(data.error_quantile * 100)}%
              </div>
            )}
            <p>
              {data.buffer_note} No future delivery-day data is used to build
              the buffer.
            </p>
          </Panel>
        )
      )}
      {!query && (
        <Panel title="How the safety buffer works">
          <p>
            The buffer is the selected quantile of signed forecast errors from
            earlier delivery days only. It is subtracted from each forecast,
            with conservative wind floored at zero. Demand is entered by you and
            is not sourced from Elexon.
          </p>
        </Panel>
      )}
    </main>
  );
}
