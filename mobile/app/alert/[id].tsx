import { Stack, useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, Text, View } from 'react-native';

import { Badge, Button, Card, ErrorText, Screen, styles } from '@/components/ui';
import { C } from '@/constants/theme';
import { useLive } from '@/context/Live';
import { useSession } from '@/context/Session';
import { api } from '@/lib/api';
import { canOperate, formatDateTime, formatType, SEVERITY_COLOR } from '@/lib/format';
import type { Alert } from '@/lib/types';

const SOURCE: Record<Alert['source'], string> = {
  AI_CAMERA: 'AI camera',
  SMART_VEST: 'Smart vest',
  SIMULATED: 'Simulated test',
};

export default function AlertDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { profile } = useSession();
  const { subscribe } = useLive();
  const [alert, setAlert] = useState<Alert | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setAlert(await api.get<Alert>(`alerts/${id}/`));
      setError('');
    } catch (e) {
      setError((e as Error).message);
    }
  }, [id]);

  useEffect(() => {
    const t = setTimeout(load, 0);
    return () => clearTimeout(t);
  }, [load]);

  // Another supervisor may resolve it on the web while this is open.
  useEffect(
    () =>
      subscribe((event, payload) => {
        if (event === 'resync') void load();
        else if ((event === 'alert_updated' || event === 'alert_resolved') && payload?.id === Number(id)) setAlert(payload);
      }),
    [subscribe, load, id],
  );

  async function resolve() {
    setBusy(true);
    setError('');
    try {
      setAlert(await api.post<Alert>(`alerts/${id}/resolve/`));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (!alert) {
    return (
      <Screen style={{ padding: 16 }}>
        {error ? <ErrorText>{error}</ErrorText> : <ActivityIndicator color={C.accent} style={{ marginTop: 40 }} />}
      </Screen>
    );
  }
  const color = SEVERITY_COLOR[alert.severity];
  const rows: [string, string][] = [
    ['Raised', formatDateTime(alert.timestamp)],
    ['Worker', alert.worker_name ?? 'Not identified'],
    ['Vest', alert.vest_id ?? '—'],
    ['Zone', alert.zone_name ?? '—'],
    ['Source', SOURCE[alert.source] ?? alert.source],
    ['Camera', alert.camera_id || '—'],
    ['Confidence', alert.confidence === null ? '—' : `${Math.round(alert.confidence * 100)}%`],
    ['Location', alert.location ? `${alert.location.lat.toFixed(5)}, ${alert.location.lng.toFixed(5)}` : '—'],
    ['Status', alert.is_resolved ? `Resolved ${formatDateTime(alert.resolved_at)}` : 'Open'],
  ];

  return (
    <Screen>
      <Stack.Screen options={{ title: formatType(alert.alert_type) }} />
      <ScrollView contentContainerStyle={{ padding: 16, gap: 14 }}>
        <View style={{ flexDirection: 'row', gap: 8 }}>
          <Badge label={alert.severity} color={color} />
          {alert.is_resolved ? <Badge label="Resolved" color={C.good} /> : <Badge label="Open" color={C.accent} />}
        </View>
        {alert.description ? <Text style={[styles.text, { fontSize: 16 }]}>{alert.description}</Text> : null}
        <Card style={{ gap: 10 }}>
          {rows.map(([k, v]) => (
            <View key={k} style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 12 }}>
              <Text style={styles.muted}>{k}</Text>
              <Text style={[styles.text, { flexShrink: 1, textAlign: 'right' }]}>{v}</Text>
            </View>
          ))}
        </Card>
        {error ? <ErrorText>{error}</ErrorText> : null}
        {!alert.is_resolved && canOperate(profile?.role) ? (
          <Button title="Mark resolved" onPress={resolve} busy={busy} />
        ) : null}
        {!alert.is_resolved && profile && !canOperate(profile.role) ? (
          <Text style={styles.faint}>Viewers cannot resolve alerts.</Text>
        ) : null}
      </ScrollView>
    </Screen>
  );
}
