import { Stack, useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { Pressable, ScrollView, Switch, Text, View } from 'react-native';

import { LiveCameraView } from '@/components/LiveCameraView';
import { Badge, Card, ErrorText, Screen, styles } from '@/components/ui';
import { C } from '@/constants/theme';
import { useLive } from '@/context/Live';
import { useSession } from '@/context/Session';
import { useCameraMap } from '@/hooks/useCameraMap';
import { api, asList } from '@/lib/api';
import { cameraStatus, STATUS_COLOR, STATUS_LABEL } from '@/lib/cameras';
import { canOperate, formatType, SEVERITY_COLOR, timeAgo } from '@/lib/format';
import type { Alert, CameraArea } from '@/lib/types';

const RECENT_ALERTS = 10;

/**
 * One camera: its live picture with danger areas (Safety Officers and
 * Admins), its areas (Admins can switch one off while the hazard is absent),
 * and its latest alerts. Areas are drawn on the web Cameras page.
 */
export default function CameraDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { profile } = useSession();
  const { subscribe } = useLive();
  const { cameras, alerting, now } = useCameraMap();
  const [areas, setAreas] = useState<CameraArea[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [error, setError] = useState('');
  const camera = cameras.find((c) => c.camera_id === id);
  const status = camera ? cameraStatus(camera, alerting, now) : 'offline';
  const isAdmin = profile?.role === 'ADMIN';

  const load = useCallback(async () => {
    try {
      const q = encodeURIComponent(id);
      const [a, recent] = await Promise.all([
        api.get<CameraArea[]>(`v1/camera-areas/?camera_id=${q}`),
        api.get<Alert[]>(`alerts/?camera_id=${q}&limit=${RECENT_ALERTS}`),
      ]);
      setAreas(asList(a));
      setAlerts(asList(recent));
      setError('');
    } catch (e) {
      setError((e as Error).message);
    }
  }, [id]);

  useEffect(() => {
    const t = setTimeout(load, 0);
    return () => clearTimeout(t);
  }, [load]);

  useEffect(
    () =>
      subscribe((event, payload) => {
        if (event === 'resync') void load();
        else if (event === 'alert_created' && payload?.camera_id === id) {
          setAlerts((list) => [payload, ...list.filter((a) => a.id !== payload.id)].slice(0, RECENT_ALERTS));
        } else if ((event === 'alert_updated' || event === 'alert_resolved') && payload?.camera_id === id) {
          setAlerts((list) => list.map((a) => (a.id === payload.id ? payload : a)));
        }
      }),
    [subscribe, load, id],
  );

  async function toggle(area: CameraArea) {
    setError('');
    try {
      const updated = await api.patch<CameraArea>(`v1/camera-areas/${area.id}/`, { is_active: !area.is_active });
      setAreas((list) => list.map((a) => (a.id === area.id ? updated : a)));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <Screen>
      <Stack.Screen options={{ title: id }} />
      <ScrollView contentContainerStyle={{ padding: 16, gap: 14 }}>
        <View style={{ flexDirection: 'row', gap: 8, alignItems: 'center' }}>
          <Badge label={STATUS_LABEL[status]} color={STATUS_COLOR[status]} />
          <Text style={styles.muted}>
            {camera?.zone ?? 'No zone'}
            {camera?.people_in_view != null ? ` · ${camera.people_in_view} in view` : ''}
          </Text>
        </View>

        {canOperate(profile?.role) ? (
          <LiveCameraView cameraId={id} areas={areas} />
        ) : (
          <Text style={styles.faint}>Live pictures are for Safety Officers and Admins.</Text>
        )}
        {error ? <ErrorText>{error}</ErrorText> : null}

        <Card style={{ gap: 10 }}>
          <Text style={styles.title}>Danger areas</Text>
          <Text style={styles.faint}>
            A person whose feet stay inside an active area for 1 s raises a Danger area alert. Areas are drawn on the web
            Cameras page.
          </Text>
          {areas.length === 0 ? <Text style={styles.muted}>No areas on this camera.</Text> : null}
          {areas.map((a) => (
            <View key={a.id} style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <Text style={[styles.text, { flex: 1 }, !a.is_active && { color: C.faint, textDecorationLine: 'line-through' }]}>
                {a.name}
              </Text>
              <Badge label={a.severity} color={SEVERITY_COLOR[a.severity]} />
              {isAdmin ? (
                <Switch
                  value={a.is_active}
                  onValueChange={() => toggle(a)}
                  accessibilityLabel={`${a.name} ${a.is_active ? 'on' : 'off'}`}
                  trackColor={{ true: C.accent, false: C.border }}
                />
              ) : (
                <Text style={styles.faint}>{a.is_active ? 'On' : 'Off'}</Text>
              )}
            </View>
          ))}
        </Card>

        <Card style={{ gap: 8 }}>
          <Text style={styles.title}>Latest alerts</Text>
          {alerts.length === 0 ? <Text style={styles.muted}>No alerts from this camera.</Text> : null}
          {alerts.map((a) => (
            <Pressable
              key={a.id}
              accessibilityRole="button"
              onPress={() => router.push({ pathname: '/alert/[id]', params: { id: String(a.id) } })}
              style={({ pressed }) => [
                { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 4 },
                pressed && { opacity: 0.6 },
              ]}>
              <View style={{ width: 4, alignSelf: 'stretch', borderRadius: 2, backgroundColor: SEVERITY_COLOR[a.severity] }} />
              <View style={{ flex: 1 }}>
                <Text style={styles.text}>{formatType(a.alert_type)}</Text>
                <Text style={styles.faint} numberOfLines={1}>
                  {a.worker_name ?? 'Not identified'} · {timeAgo(a.timestamp)}
                </Text>
              </View>
              {a.is_resolved ? <Badge label="Resolved" color={C.good} /> : null}
            </Pressable>
          ))}
        </Card>
      </ScrollView>
    </Screen>
  );
}
