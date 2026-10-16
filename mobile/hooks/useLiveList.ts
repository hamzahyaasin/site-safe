import { useCallback, useEffect, useState } from 'react';

import { useLive, type LiveEvent } from '@/context/Live';
import { asList, api } from '@/lib/api';

/**
 * Load a list from the API and keep it current from live events.
 * ``reduce`` applies one event to the list; "resync" (after a reconnect)
 * always reloads, so nothing missed while offline is lost.
 */
export function useLiveList<T extends { id: number }>(
  path: string,
  reduce: (list: T[], event: LiveEvent, payload: any) => T[],
) {
  const { subscribe } = useLive();
  const [items, setItems] = useState<T[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      setItems(asList(await api.get<T[]>(path)));
      setError('');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    // Deferred so the load's state updates happen outside the effect body.
    const t = setTimeout(load, 0);
    return () => clearTimeout(t);
  }, [load]);

  useEffect(
    () =>
      subscribe((event, payload) => {
        if (event === 'resync') void load();
        else setItems((list) => reduce(list, event, payload));
      }),
    [subscribe, load, reduce],
  );

  return { items, loading, error, reload: load, setItems };
}
