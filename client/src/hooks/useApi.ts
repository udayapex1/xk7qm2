import { useEffect, useState } from 'react';
import { getMeta } from '../api/client';
import type { Meta } from '../api/types';
let metaPromise: Promise<Meta> | null = null;
export function useMeta() {
  const [data, setData] = useState<Meta | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    metaPromise ??= getMeta();
    metaPromise.then(setData).catch((e) => {
      setError(e.message);
      metaPromise = null;
    });
  }, []);
  return { data, error, loading: !data && !error };
}
export function useLoad<T>(loader: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let live = true;
    setLoading(true);
    setError('');
    loader()
      .then((v) => {
        if (live) setData(v);
      })
      .catch((e) => {
        if (live) setError(e.message);
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, [loader]);
  return { data, error, loading };
}
