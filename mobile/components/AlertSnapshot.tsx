import { useEffect, useState } from 'react';
import { ActivityIndicator, Image, Text, View } from 'react-native';

import { styles } from '@/components/ui';
import { C } from '@/constants/theme';
import { api, ApiError } from '@/lib/api';

/** The camera frame that confirmed an AI alert (FR-29), fetched with the session's token. */
export function AlertSnapshot({ path }: { path: string }) {
  const [uri, setUri] = useState<string | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    // The serializer gives "/api/alerts/<id>/snapshot/"; the client's base already ends in /api/.
    api
      .imageDataUri(path.replace(/^\/?api\//, ''))
      .then((data) => {
        if (!cancelled) setUri(data);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(
          e instanceof ApiError && e.status === 404
            ? 'Snapshot no longer available (removed by the retention policy).'
            : 'Snapshot could not be loaded.',
        );
      });
    return () => {
      cancelled = true;
    };
  }, [path]);

  return (
    <View style={{ gap: 6 }}>
      <Text style={styles.muted}>Evidence frame</Text>
      {error ? (
        <Text style={styles.faint}>{error}</Text>
      ) : uri ? (
        <Image
          source={{ uri }}
          accessibilityLabel="Camera frame that confirmed this alert"
          resizeMode="contain"
          style={{ width: '100%', aspectRatio: 16 / 9, borderRadius: 8, backgroundColor: '#000' }}
        />
      ) : (
        <View style={{ width: '100%', aspectRatio: 16 / 9, alignItems: 'center', justifyContent: 'center' }}>
          <ActivityIndicator color={C.accent} />
        </View>
      )}
    </View>
  );
}
