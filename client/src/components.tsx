import type { ReactNode } from 'react';
import { formatBias,formatNumber,formatPct } from './lib/format';
import type { Metrics } from './api/types';
export function ErrorBanner({message}:{message:string}){return message?<div className="banner" role="alert">{message}</div>:null;}
export function Loading(){return <div className="skeleton" aria-label="Loading data"><i/><i/><i/></div>;}
export function Panel({title,children,extra}:{title:string;children:ReactNode;extra?:ReactNode}){return <section className="panel"><div className="panel-head"><h2>{title}</h2>{extra}</div>{children}</section>;}
export function Kpi({label,value,note}:{label:string;value:string;note?:string}){return <article className="kpi"><span>{label}</span><strong>{value}</strong>{note&&<small>{note}</small>}</article>;}
export function MetricKpis({metrics,includeCoverage=false}:{metrics:Metrics;includeCoverage?:boolean}){return <div className="kpis">{includeCoverage&&<Kpi label="Forecast-grid coverage" value={formatPct(metrics.coverage_pct)}/>}<Kpi label="Mean bias" value={formatBias(metrics.mean_error_mw)}/><Kpi label="MAE" value={formatNumber(metrics.mae_mw,'MW')}/><Kpi label="WAPE" value={formatPct(metrics.wape_pct)}/></div>;}
