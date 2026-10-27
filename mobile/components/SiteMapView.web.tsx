import { useEffect, useMemo, useRef, useState } from 'react';

import { DEFAULT_CENTER, parseMapMessage, siteMapHtml } from '@/lib/siteMap';
import type { SiteMapViewProps } from './SiteMapView';

/** The same map page as the app's WebView, in an iframe for the web build. */
export function SiteMapView({ data, onCamera, onError }: SiteMapViewProps) {
  const html = useMemo(() => siteMapHtml(DEFAULT_CENTER), []);
  const frame = useRef<HTMLIFrameElement>(null);
  const [ready, setReady] = useState(false);
  // Latest handlers, so the message listener is added once and never misses "ready".
  const handlers = useRef({ onCamera, onError });
  useEffect(() => {
    handlers.current = { onCamera, onError };
  }, [onCamera, onError]);

  useEffect(() => {
    function onMessage(e: MessageEvent) {
      if (e.source !== frame.current?.contentWindow) return;
      const msg = parseMapMessage(e.data);
      if (msg?.type === 'ready') setReady(true);
      else if (msg?.type === 'error') handlers.current.onError();
      else if (msg?.type === 'camera') handlers.current.onCamera(msg.id);
    }
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, []);

  useEffect(() => {
    const win = frame.current?.contentWindow as (Window & { render?: (d: unknown) => void }) | null | undefined;
    if (ready) win?.render?.(data);
  }, [ready, data]);

  return (
    <iframe
      ref={frame}
      srcDoc={html}
      title="Site map with zones, vests and cameras"
      style={{ border: 0, width: '100%', height: '100%', flex: 1 }}
    />
  );
}
