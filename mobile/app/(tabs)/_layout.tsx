import { SymbolView } from 'expo-symbols';
import { Tabs } from 'expo-router';
import { Text, View } from 'react-native';

import { C } from '@/constants/theme';
import { useLive } from '@/context/Live';

function LiveDot() {
  const { status } = useLive();
  const color = status === 'live' ? C.good : status === 'connecting' ? C.accent : C.faint;
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginRight: 16 }} accessibilityLabel={`Connection ${status}`}>
      <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: color }} />
      <Text style={{ color: C.muted, fontSize: 12 }}>{status === 'live' ? 'Live' : status === 'connecting' ? 'Connecting' : 'Offline'}</Text>
    </View>
  );
}

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: C.accent,
        tabBarInactiveTintColor: C.faint,
        tabBarStyle: { backgroundColor: C.card, borderTopColor: C.border },
        headerStyle: { backgroundColor: C.card },
        headerTintColor: C.text,
        headerRight: () => <LiveDot />,
      }}>
      <Tabs.Screen
        name="index"
        options={{
          title: 'Alerts',
          tabBarIcon: ({ color }) => (
            <SymbolView name={{ ios: 'exclamationmark.triangle', android: 'warning', web: 'warning' }} tintColor={color} size={26} />
          ),
        }}
      />
      <Tabs.Screen
        name="map"
        options={{
          title: 'Map',
          tabBarIcon: ({ color }) => (
            <SymbolView name={{ ios: 'map', android: 'map', web: 'map' }} tintColor={color} size={26} />
          ),
        }}
      />
      <Tabs.Screen
        name="cameras"
        options={{
          title: 'Cameras',
          tabBarIcon: ({ color }) => (
            <SymbolView name={{ ios: 'video', android: 'videocam', web: 'videocam' }} tintColor={color} size={26} />
          ),
        }}
      />
      <Tabs.Screen
        name="workers"
        options={{
          title: 'Workers',
          tabBarIcon: ({ color }) => (
            <SymbolView name={{ ios: 'person.2', android: 'group', web: 'group' }} tintColor={color} size={26} />
          ),
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: 'Settings',
          tabBarIcon: ({ color }) => (
            <SymbolView name={{ ios: 'gearshape', android: 'settings', web: 'settings' }} tintColor={color} size={26} />
          ),
        }}
      />
    </Tabs>
  );
}
