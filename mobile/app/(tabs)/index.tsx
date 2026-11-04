import { useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import { FlatList, Pressable, RefreshControl, Text, View } from 'react-native';

import { Badge, Empty, ErrorText, Screen, styles } from '@/components/ui';
import { C } from '@/constants/theme';
import { useLiveList } from '@/hooks/useLiveList';
import { alertSubject, formatType, SEVERITY_COLOR, timeAgo } from '@/lib/format';
import { reduceAlerts } from '@/lib/reducers';
import type { Alert } from '@/lib/types';

type Filter = 'open' | 'all';

const REDUCERS = { open: reduceAlerts(true), all: reduceAlerts(false) };

export default function Alerts() {
  const [filter, setFilter] = useState<Filter>('open');
  const path = filter === 'open' ? 'alerts/?is_resolved=false' : 'alerts/';
  const { items, loading, error, reload } = useLiveList<Alert>(path, REDUCERS[filter]);
  const [refreshing, setRefreshing] = useState(false);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await reload();
    setRefreshing(false);
  }, [reload]);

  return (
    <Screen>
      <View style={{ flexDirection: 'row', gap: 8, padding: 12 }}>
        {(['open', 'all'] as Filter[]).map((f) => (
          <Pressable
            key={f}
            accessibilityRole="button"
            accessibilityState={{ selected: filter === f }}
            onPress={() => setFilter(f)}
            style={{
              paddingHorizontal: 14,
              paddingVertical: 7,
              borderRadius: 16,
              borderWidth: 1,
              borderColor: filter === f ? C.accent : C.border,
              backgroundColor: filter === f ? `${C.accent}22` : 'transparent',
            }}
          >
            <Text
              style={{
                color: filter === f ? C.accent : C.muted,
                fontWeight: '600',
              }}
            >
              {f === 'open' ? 'Open' : 'All'}
            </Text>
          </Pressable>
        ))}
      </View>
      {error ? (
        <View style={{ paddingHorizontal: 12 }}>
          <ErrorText>{error}</ErrorText>
        </View>
      ) : null}
      <FlatList
        data={items}
        keyExtractor={(a) => String(a.id)}
        contentContainerStyle={{ padding: 12, paddingTop: 0, gap: 10 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={C.accent} />}
        ListEmptyComponent={
          loading ? undefined : <Empty title={filter === 'open' ? 'No open alerts' : 'No alerts yet'} />
        }
        renderItem={({ item }) => <AlertRow alert={item} />}
      />
    </Screen>
  );
}

function AlertRow({ alert }: { alert: Alert }) {
  const router = useRouter();
  const color = SEVERITY_COLOR[alert.severity];
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${formatType(alert.alert_type)}, ${alert.severity}`}
      onPress={() =>
        router.push({
          pathname: '/alert/[id]',
          params: { id: String(alert.id) },
        })
      }
      style={({ pressed }) => [
        styles.card,
        { borderLeftWidth: 4, borderLeftColor: color, gap: 6 },
        pressed && { opacity: 0.7 },
      ]}
    >
      <View
        style={{
          flexDirection: 'row',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 8,
        }}
      >
        <Text style={styles.title}>{formatType(alert.alert_type)}</Text>
        <Badge label={alert.severity} color={color} />
      </View>
      <Text style={styles.muted} numberOfLines={2}>
        {alertSubject(alert)}
        {alert.zone_name && !alert.zone ? ` · ${alert.zone_name}` : ''}
        {alert.camera_id ? ` · ${alert.camera_id}` : ''}
      </Text>
      <View style={{ flexDirection: 'row', gap: 8, alignItems: 'center' }}>
        <Text style={styles.faint}>{timeAgo(alert.timestamp)}</Text>
        {alert.is_resolved ? <Badge label="Resolved" color={C.good} /> : null}
        {alert.source === 'SIMULATED' ? <Badge label="Simulated" color={C.faint} /> : null}
      </View>
    </Pressable>
  );
}
