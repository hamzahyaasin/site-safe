import { useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import { FlatList, Pressable, RefreshControl, Text, View } from 'react-native';

import { Badge, Empty, ErrorText, Screen, styles } from '@/components/ui';
import { C } from '@/constants/theme';
import { useCameraMap } from '@/hooks/useCameraMap';
import { cameraStatus, STATUS_COLOR, STATUS_LABEL } from '@/lib/cameras';
import { formatType, timeAgo } from '@/lib/format';
import type { MapCamera } from '@/lib/types';

/** Every camera with its live status, people in view and alerts; tap for its live picture and danger areas. */
export default function Cameras() {
  const { cameras, alerting, now, loading, error, reload } = useCameraMap();
  const [refreshing, setRefreshing] = useState(false);
  const live = cameras.filter((c) => c.live).length;

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await reload();
    setRefreshing(false);
  }, [reload]);

  return (
    <Screen>
      <FlatList
        data={cameras}
        keyExtractor={(c) => c.camera_id}
        contentContainerStyle={{ padding: 12, gap: 10 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={C.accent} />}
        ListHeaderComponent={
          <View style={{ gap: 8, marginBottom: 4 }}>
            {error ? <ErrorText>{error}</ErrorText> : null}
            <Text style={styles.muted}>
              {live} of {cameras.length} live · a camera shows red for a minute after it raises an alert
            </Text>
          </View>
        }
        ListEmptyComponent={
          loading ? undefined : <Empty title="No cameras yet" detail="Cameras appear once assigned to a zone or started." />
        }
        renderItem={({ item }) => <CameraRow camera={item} status={cameraStatus(item, alerting, now)} now={now} />}
      />
    </Screen>
  );
}

function CameraRow({ camera, status, now }: { camera: MapCamera; status: keyof typeof STATUS_COLOR; now: number }) {
  const router = useRouter();
  const color = STATUS_COLOR[status];
  const last = camera.last_alert;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`Camera ${camera.camera_id}, ${STATUS_LABEL[status]}`}
      onPress={() => router.push({ pathname: '/camera/[id]', params: { id: camera.camera_id } })}
      style={({ pressed }) => [styles.card, { borderLeftWidth: 4, borderLeftColor: color, gap: 6 }, pressed && { opacity: 0.7 }]}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
        <Text style={[styles.title, { fontFamily: 'Menlo' }]}>{camera.camera_id}</Text>
        <Badge label={STATUS_LABEL[status]} color={color} />
      </View>
      <Text style={styles.muted}>
        {camera.zone ?? 'No zone'}
        {camera.people_in_view !== null ? ` · ${camera.people_in_view} in view` : ''}
        {camera.live ? '' : ` · last picture ${timeAgo(camera.last_frame_at, now)}`}
      </Text>
      <Text style={styles.faint}>
        {camera.open_alerts} open alert{camera.open_alerts === 1 ? '' : 's'}
        {last ? ` · last ${formatType(last.alert_type).toLowerCase()} ${timeAgo(last.timestamp, now)}` : ''}
        {camera.placement ? '' : ' · not on the site map'}
      </Text>
    </Pressable>
  );
}
