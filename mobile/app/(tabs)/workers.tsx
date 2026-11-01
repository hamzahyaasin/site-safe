import { useCallback, useState } from 'react';
import { FlatList, RefreshControl, Text, View } from 'react-native';

import { Badge, Empty, ErrorText, Screen, styles } from '@/components/ui';
import { C } from '@/constants/theme';
import { useLiveList } from '@/hooks/useLiveList';
import { describeLocation, formatGas, timeAgo, workerPresence } from '@/lib/format';
import { reduceWorkers } from '@/lib/reducers';
import type { Worker } from '@/lib/types';

const TONE = { good: C.good, bad: C.bad, muted: C.faint, alert: C.bad };

export default function Workers() {
  const { items, loading, error, reload } = useLiveList<Worker>('workers/', reduceWorkers);
  const [refreshing, setRefreshing] = useState(false);
  const active = items.filter((w) => w.is_active);
  const onSite = active.filter((w) => w.location?.current || w.smart_vest?.is_online).length;

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await reload();
    setRefreshing(false);
  }, [reload]);

  return (
    <Screen>
      <FlatList
        data={active}
        keyExtractor={(w) => String(w.id)}
        contentContainerStyle={{ padding: 12, gap: 10 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={C.accent} />}
        ListHeaderComponent={
          <View style={{ gap: 8, marginBottom: 4 }}>
            {error ? <ErrorText>{error}</ErrorText> : null}
            <Text style={styles.muted}>
              {onSite} on site · {active.length} active · located by camera badge sightings and vest GPS
            </Text>
          </View>
        }
        ListEmptyComponent={loading ? undefined : <Empty title="No active workers" />}
        renderItem={({ item }) => {
          const p = workerPresence(item);
          const vest = item.smart_vest;
          return (
            <View style={[styles.card, { gap: 4 }]}>
              <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text style={styles.title}>{item.name}</Text>
                <Badge label={p.label} color={TONE[p.tone]} />
              </View>
              <Text style={[styles.text, { color: item.location?.current ? C.good : C.muted }]}>
                {describeLocation(item) ?? (vest ? 'Vest has not reported a position yet' : 'No camera has read this badge yet')}
              </Text>
              <Text style={styles.muted}>
                {[item.role, item.zone_name ? `assigned ${item.zone_name}` : null].filter(Boolean).join(' · ') || '—'}
              </Text>
              <Text style={styles.faint}>
                {vest
                  ? `${vest.vest_id} · last report ${timeAgo(vest.last_seen)} · battery ${vest.battery_level === null ? 'unknown' : `${vest.battery_level}%`}` +
                    (formatGas(vest) ? ` · gas ${formatGas(vest)}${vest.gas_over_limit ? ' (over limit)' : ''}` : '')
                  : 'No vest assigned'}
              </Text>
            </View>
          );
        }}
      />
    </Screen>
  );
}
