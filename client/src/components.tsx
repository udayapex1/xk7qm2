import type { ReactNode } from 'react';
import { formatBias, formatNumber, formatPct } from './lib/format';
import type { Metrics } from './api/types';
import { NumberTicker } from './components/ui/number-ticker';
export function ErrorBanner({ message }: { message: string }) {
  return message ? (
    <div className="banner" role="alert">
      {message}
    </div>
  ) : null;
}
export function Loading() {
  return (
    <div className="skeleton" aria-label="Loading data">
      <i />
      <i />
      <i />
    </div>
  );
}
export function Panel({
  title,
  children,
  extra,
}: {
  title: string;
  children: ReactNode;
  extra?: ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>{title}</h2>
        {extra}
      </div>
      {children}
    </section>
  );
}
export function Kpi({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note?: string;
}) {
  const numericValue = value.match(/^([+-]?)([\d,]+(?:\.\d+)?)(.*)$/);
  const tickerValue = numericValue
    ? Number(numericValue[2].replace(/,/g, ''))
    : null;
  const decimals = numericValue?.[2].split('.')[1]?.length ?? 0;
  return (
    <article className="kpi">
      <span>{label}</span>
      <strong aria-label={value}>
        {tickerValue === null ? (
          value
        ) : (
          <span className="kpi-number">
            {numericValue?.[1]}
            <NumberTicker value={tickerValue} decimalPlaces={decimals} />
            {numericValue?.[3]}
          </span>
        )}
      </strong>
      {note && <small>{note}</small>}
    </article>
  );
}
export function MetricKpis({
  metrics,
  includeCoverage = false,
}: {
  metrics: Metrics;
  includeCoverage?: boolean;
}) {
  return (
    <div className="kpis">
      {includeCoverage && (
        <Kpi
          label="Forecast-grid coverage"
          value={formatPct(metrics.coverage_pct)}
        />
      )}
      <Kpi label="Mean bias" value={formatBias(metrics.mean_error_mw)} />
      <Kpi label="MAE" value={formatNumber(metrics.mae_mw, 'MW')} />
      <Kpi label="WAPE" value={formatPct(metrics.wape_pct)} />
    </div>
  );
}
