import type { AccuracySummary, ByHourResponse, DailyResponse, DecisionResponse, DistributionResponse, ForecastResponse, HorizonResponse, Meta, VintagesResponse, WindLevelResponse } from './types';

const base = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '');
export class ApiError extends Error { status:number; constructor(message:string,status:number){super(message);this.name='ApiError';this.status=status;} }
async function request<T>(path:string, params?:Record<string,string|number|undefined>):Promise<T>{
  const url=new URL(`${base}${path}`, window.location.origin); Object.entries(params??{}).forEach(([k,v])=>{if(v!==undefined)url.searchParams.set(k,String(v));});
  let response:Response; try { response=await fetch(url.toString()); } catch { throw new ApiError('Backend unreachable. Check that the API is running at http://127.0.0.1:8000.',0); }
  if(!response.ok){let message=`Request failed (${response.status})`;try{const body=await response.json();message=typeof body.detail==='string'?body.detail:JSON.stringify(body.detail??body);}catch{} throw new ApiError(message,response.status);}
  return response.json() as Promise<T>;
}
export const getHealth=()=>request<{status:string}>('/health');
export const getMeta=()=>request<Meta>('/meta');
export const getForecast=(delivery_date:string,cutoff?:string)=>request<ForecastResponse>('/forecast',{delivery_date,cutoff});
export const getVintages=(target_time:string,cutoff?:string)=>request<VintagesResponse>('/forecast/vintages',{target_time,cutoff});
export const getAccuracySummary=(start?:string,end?:string,cutoff?:string)=>request<AccuracySummary>('/accuracy/summary',{start,end,cutoff});
export const getByHorizon=()=>request<HorizonResponse>('/accuracy/by-horizon');
export const getByHour=(cutoff?:string)=>request<ByHourResponse>('/accuracy/by-hour',{cutoff});
export const getDaily=(cutoff?:string)=>request<DailyResponse>('/accuracy/daily',{cutoff});
export const getDistribution=(bins=20,cutoff?:string)=>request<DistributionResponse>('/accuracy/distribution',{bins,cutoff});
export const getByWindLevel=(start?:string,end?:string,cutoff?:string)=>request<WindLevelResponse>('/accuracy/by-wind-level',{start,end,cutoff});
export const getDecision=(delivery_date:string,demand_mw:number,cutoff?:string,quantile=0.9)=>request<DecisionResponse>('/decision',{delivery_date,demand_mw,cutoff,quantile});
