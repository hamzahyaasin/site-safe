import { useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';

import { useLive } from '@/context/Live';
import { api } from '@/lib/api';
import { ALERT_FLASH_MS, type Alerting, reduceCameras } from '@/lib/cameras';
import type { MapCamera } from '@/lib/types';

// Live status follows each camera's frames, which have no event of their own.
const POLL_MS = 10000;

/**
 * Every known camera from /api/v1/camera-map/ (FR-33), kept current while
 * the screen is in view: polled for live status, updated on camera_updated,
 * and marked as alerting for a minute when one of its alerts arrives.
 */
export function useCameraMap() {
  const { subscribe } = useLive();
  const [cameras, setCameras] = useState<MapCamera[]>([]);
  const [alerting, setAlerting] = useState<Alerting>({});
  const [now, setNow] = useState(() => Date.now());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      setCameras(await api.get<MapCamera[]>('v1/camera-map/'));
      setError('');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
      setNow(Date.now());
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      const first = setTimeout(load, 0);
      const timer = setInterval(load, POLL_MS);
      return () => {
        clearTimeout(first);
        clearInterval(timer);
      };
    }, [load]),
  );

  useEffect(
    () =>
      subscribe((event, payload) => {
        if (event === 'resync') void load();
        else if (event === 'camera_updated') setCameras((list) => reduceCameras(list, event, payload));
        else if (event === 'alert_created' && payload?.camera_id) {
          setAlerting((a) => ({ ...a, [payload.camera_id]: Date.now() }));
          setNow(Date.now());
          void load();
        } else if (event === 'alert_resolved' && payload?.camera_id) void load();
      }),
    [subscribe, load],
  );

  // Re-render while a highlight is showing, so it ends on time.
  const highlighted = Object.values(alerting).some((at) => now - at < ALERT_FLASH_MS);
  useEffect(() => {
    if (!highlighted) return undefined;
    const t = setInterval(() => setNow(Date.now()), 5000);
    return () => clearInterval(t);
  }, [highlighted]);

  return { cameras, alerting, now, loading, error, reload: load };
}
