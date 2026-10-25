import { useCallback } from 'react';
import { getForecast, getVintages } from '../api/client';
import { useLoad } from './useApi';
export function useForecast(date: string, cutoff: string) {
  const load = useCallback(() => getForecast(date, cutoff), [date, cutoff]);
  return useLoad(load);
}
export function useVintages(target: string | null, cutoff: string) {
  const load = useCallback(
    () => (target ? getVintages(target, cutoff) : Promise.resolve(null)),
    [target, cutoff],
  );
  return useLoad(load);
}
