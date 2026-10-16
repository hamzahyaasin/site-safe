import { Link, Stack } from 'expo-router';
import { Text } from 'react-native';

import { Screen, styles } from '@/components/ui';
import { C } from '@/constants/theme';

export default function NotFound() {
  return (
    <Screen style={{ alignItems: 'center', justifyContent: 'center', gap: 12 }}>
      <Stack.Screen options={{ title: 'Not found' }} />
      <Text style={styles.title}>This screen does not exist.</Text>
      <Link href="/" style={{ color: C.accent }}>
        Back to alerts
      </Link>
    </Screen>
  );
}
