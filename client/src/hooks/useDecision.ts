import { useCallback } from 'react';
import { getDecision } from '../api/client';
import { useLoad } from './useApi';
export function useDecision(date:string,demand:number,cutoff:string,quantile:number,enabled:boolean){const load=useCallback(()=>enabled?getDecision(date,demand,cutoff,quantile):Promise.resolve(null),[date,demand,cutoff,quantile,enabled]);return useLoad(load,[load]);}
