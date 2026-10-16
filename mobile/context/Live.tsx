import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { AppState } from 'react-native';

import { api } from '@/lib/api';
import { useSession } from './Session';

export type LiveEvent =
  | 'alert_created'
  | 'alert_updated'
  | 'alert_resolved'
  | 'vest_updated'
  | 'worker_status_update'
  | 'resync';
export type LiveStatus = 'connecting' | 'live' | 'offline';
type Listener = (event: LiveEvent, payload: any) => void;

const CLOSE_UNAUTHORIZED = 4401;
const MAX_DELAY_MS = 30000;

interface LiveValue {
  status: LiveStatus;
  subscribe: (fn: Listener) => () => void;
}

const LiveContext = createContext<LiveValue | null>(null);

/**
 * Dashboard websocket for the app's lifetime in the foreground.
 * Reconnects with backoff, renews an expired token on close code 4401,
 * and emits "resync" after every reconnect so screens reload whatever they
 * missed. In the background the socket is closed; push notifications cover
 * that time.
 */
export function LiveProvider({ children }: { children: ReactNode }) {
  const { signedIn } = useSession();
  // Signed-in sessions start out connecting; signed-out ones report offline below.
  const [status, setStatus] = useState<LiveStatus>('connecting');
  const listeners = useRef(new Set<Listener>());
  const socket = useRef<WebSocket | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const attempts = useRef(0);
  const connectedOnce = useRef(false);
  const active = useRef(true);
  // Lets the socket's close handler reconnect without a self-referencing callback.
  const connectRef = useRef<() => void>(() => undefined);

  const emit = useCallback((event: LiveEvent, payload: unknown) => {
    listeners.current.forEach((fn) => {
      try {
        fn(event, payload);
      } catch {
        // a broken screen must not stop other subscribers
      }
    });
  }, []);

  const disconnect = useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    const ws = socket.current;
    socket.current = null;
    ws?.close();
  }, []);

  const connect = useCallback(() => {
    if (!active.current || !api.accessToken) return;
    disconnect();
    setStatus('connecting');
    const ws = new WebSocket(api.socketUrl());
    socket.current = ws;

    ws.onopen = () => {
      attempts.current = 0;
      setStatus('live');
      if (connectedOnce.current) emit('resync', null);
      connectedOnce.current = true;
    };
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(String(e.data));
        if (msg.type && msg.type !== 'connection_established') emit(msg.type, msg.payload);
      } catch {
        // ignore malformed frames
      }
    };
    ws.onclose = (e) => {
      if (socket.current !== ws) return; // closed on purpose
      socket.current = null;
      setStatus('offline');
      if (!active.current) return;
      if (e.code === CLOSE_UNAUTHORIZED) {
        api.renew().then(() => connectRef.current(), () => api.signOut());
        return;
      }
      attempts.current += 1;
      const delay = Math.min(1000 * 2 ** attempts.current, MAX_DELAY_MS);
      timer.current = setTimeout(() => connectRef.current(), delay);
    };
  }, [disconnect, emit]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    if (!signedIn) {
      disconnect();
      connectedOnce.current = false;
      return undefined;
    }
    active.current = true;
    const first = setTimeout(connect, 0);
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active') {
        active.current = true;
        connect();
      } else if (state === 'background') {
        active.current = false;
        disconnect();
        setStatus('offline');
      }
    });
    return () => {
      clearTimeout(first);
      sub.remove();
      active.current = false;
      disconnect();
    };
  }, [signedIn, connect, disconnect]);

  const subscribe = useCallback((fn: Listener) => {
    listeners.current.add(fn);
    return () => {
      listeners.current.delete(fn);
    };
  }, []);

  const value = useMemo(
    () => ({ status: signedIn ? status : ('offline' as LiveStatus), subscribe }),
    [signedIn, status, subscribe],
  );
  return <LiveContext.Provider value={value}>{children}</LiveContext.Provider>;
}

export function useLive() {
  const ctx = useContext(LiveContext);
  if (!ctx) throw new Error('useLive must be used inside LiveProvider');
  return ctx;
}
