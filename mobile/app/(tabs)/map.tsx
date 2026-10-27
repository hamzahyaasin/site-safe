import { useRouter } from 'expo-router';
import { useCallback, useMemo, useState } from 'react';
import { Text, View } from 'react-native';

import { SiteMapView } from '@/components/SiteMapView';
import { ErrorText, Screen, styles } from '@/components/ui';
import { useCameraMap } from '@/hooks/useCameraMap';
import { useLiveList } from '@/hooks/useLiveList';
import { cameraStatus, STATUS_COLOR } from '@/lib/cameras';
import { reduceVests, reduceZones } from '@/lib/reducers';
import { siteMapData } from '@/lib/siteMap';
import type { SmartVest, Zone } from '@/lib/types';

/**
 * The live site map (FR-33): zones with head counts, vests, and cameras with
 * their view cones, green live, grey offline, red for a minute after an
 * alert. Tapping a camera opens it. Drawn by Leaflet, the same map as the
 * web dashboard, so no map API key is needed on any platform.
 */
export default function SiteMapScreen() {
  const router = useRouter();
  const zones = useLiveList<Zone>('v1/zones/', reduceZones);
  const vests = useLiveList<SmartVest>('v1/vests/', reduceVests);
  const { cameras, alerting, now, error } = useCameraMap();
  const [mapError, setMapError] = useState('');

  const data = useMemo(
    () => siteMapData(zones.items, vests.items, cameras, alerting, now),
    [zones.items, vests.items, cameras, alerting, now],
  );
  const onCamera = useCallback(
    (id: string) => router.push({ pathname: '/camera/[id]', params: { id } }),
    [router],
  );
  const onError = useCallback(
    () => setMapError('The map could not load. It needs an internet connection for its base map.'),
    [],
  );

  const counts = { live: 0, offline: 0, alerting: 0 };
  for (const c of cameras.filter((c) => c.placement)) counts[cameraStatus(c, alerting, now)] += 1;
  const unplaced = cameras.filter((c) => !c.placement).length;

  return (
    <Screen>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 12, paddingHorizontal: 12, paddingVertical: 8 }}>
        <Legend color={STATUS_COLOR.live} label={`${counts.live} live`} />
        <Legend color={STATUS_COLOR.offline} label={`${counts.offline} offline`} />
        {counts.alerting ? <Legend color={STATUS_COLOR.alerting} label={`${counts.alerting} alerting`} /> : null}
        {unplaced ? <Text style={styles.faint}>{unplaced} not on the map</Text> : null}
      </View>
      {error || zones.error || mapError ? (
        <View style={{ paddingHorizontal: 12, paddingBottom: 8 }}>
          <ErrorText>{mapError || error || zones.error}</ErrorText>
        </View>
      ) : null}
      <SiteMapView data={data} onCamera={onCamera} onError={onError} />
    </Screen>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
      <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: color }} />
      <Text style={styles.muted}>{label}</Text>
    </View>
  );
}
