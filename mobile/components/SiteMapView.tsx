import { useEffect, useMemo, useRef, useState } from 'react';
import { WebView, type WebViewMessageEvent } from 'react-native-webview';

import { C } from '@/constants/theme';
import { api } from '@/lib/api';
import { DEFAULT_CENTER, parseMapMessage, type SiteMapData, siteMapHtml } from '@/lib/siteMap';

export interface SiteMapViewProps {
  data: SiteMapData;
  onCamera: (id: string) => void;
  onError: () => void;
}

/** The site map page in a WebView; the web build uses SiteMapView.web.tsx. */
export function SiteMapView({ data, onCamera, onError }: SiteMapViewProps) {
  const html = useMemo(() => siteMapHtml(DEFAULT_CENTER), []);
  // WebView's props are ``WebViewProps & P``; the default P (undefined) would make them ``never``.
  const web = useRef<WebView<object>>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (ready) web.current?.injectJavaScript(`window.render(${JSON.stringify(data)}); true;`);
  }, [ready, data]);

  function onMessage(e: WebViewMessageEvent) {
    const msg = parseMapMessage(e.nativeEvent.data);
    if (msg?.type === 'ready') setReady(true);
    else if (msg?.type === 'error') onError();
    else if (msg?.type === 'camera') onCamera(msg.id);
  }

  return (
    <WebView<object>
      ref={web}
      originWhitelist={['*']}
      // A real origin gives the map tiles a referrer, as OpenStreetMap asks.
      source={{ html, baseUrl: api.baseUrl.replace(/api\/$/, '') }}
      onMessage={onMessage}
      style={{ flex: 1, backgroundColor: C.bg }}
      javaScriptEnabled
      setSupportMultipleWindows={false}
      accessibilityLabel="Site map with zones, vests and cameras"
    />
  );
}
