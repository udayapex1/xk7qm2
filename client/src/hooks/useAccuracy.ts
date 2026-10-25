import { useCallback } from 'react';
import {
  getAccuracySummary,
  getByHorizon,
  getByHour,
  getDaily,
  getDistribution,
  getByWindLevel,
} from '../api/client';
import { useLoad } from './useApi';
export function useAccuracySummary(cutoff: string) {
  const load = useCallback(
    () => getAccuracySummary(undefined, undefined, cutoff),
    [cutoff],
  );
  return useLoad(load);
}
export function useAccuracy(start: string, end: string, cutoff: string) {
  const load = useCallback(
    async () =>
      Promise.all([
        getAccuracySummary(start, end, cutoff),
        getByHorizon(),
        getByHour(cutoff),
        getDaily(cutoff),
        getDistribution(24, cutoff),
        getByWindLevel(start, end, cutoff),
      ]),
    [start, end, cutoff],
  );
  return useLoad(load);
}
