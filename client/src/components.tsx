import type { ReactNode } from 'react';
import { formatBias, formatNumber, formatPct } from './lib/format';
import type { Metrics } from './api/types';
import { BentoCard, BentoGrid } from './components/ui/bento-grid';
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
  className = '',
}: {
  title: string;
  children: ReactNode;
  extra?: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
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
  className,
  caption,
}: {
  label: string;
  value: string;
  note?: string;
  className?: string;
  caption?: string;
}) {
  return (
    <BentoCard className={`kpi ${className ?? ''}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {(note || caption) && <small>{note ?? caption}</small>}
    </BentoCard>
  );
}
export function MetricKpis({
  metrics,
  includeCoverage = false,
  forecastCaptions = false,
}: {
  metrics: Metrics;
  includeCoverage?: boolean;
  forecastCaptions?: boolean;
}) {
  return (
    <BentoGrid
      className={`metric-bento ${forecastCaptions ? 'forecast-kpis' : ''}`}
    >
      <Kpi
        label="Mean bias"
        value={formatBias(metrics.mean_error_mw)}
        caption={
          forecastCaptions ? 'Forecast above actual, on average' : undefined
        }
      />
      <Kpi
        label="MAE"
        value={formatNumber(metrics.mae_mw, 'MW')}
        caption={forecastCaptions ? 'Typical absolute miss' : undefined}
      />
      <Kpi
        label="WAPE"
        value={formatPct(metrics.wape_pct)}
        caption={
          forecastCaptions ? 'Error as a share of actual output' : undefined
        }
      />
      {includeCoverage && (
        <Kpi
          label="Forecast coverage"
          value={formatPct(metrics.coverage_pct)}
          caption={forecastCaptions ? 'Every hour had a forecast' : undefined}
        />
      )}
    </BentoGrid>
  );
}
