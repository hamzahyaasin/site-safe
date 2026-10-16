import { useState } from 'react';
import { ScrollView, Switch, Text, View } from 'react-native';

import { Button, Card, ErrorText, Screen, styles } from '@/components/ui';
import { C } from '@/constants/theme';
import { useSession } from '@/context/Session';
import { api } from '@/lib/api';
import type { Profile } from '@/lib/types';

export default function Settings() {
  const { profile, email, server, push, signOut, refreshProfile } = useSession();
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  async function setPushPreference(value: boolean) {
    setSaving(true);
    setError('');
    try {
      await api.patch<Profile>('v1/profile/', { notify_push: value });
      await refreshProfile();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 14 }}>
        <Card style={{ gap: 4 }}>
          <Text style={styles.title}>{profile?.full_name || email}</Text>
          <Text style={styles.muted}>{profile?.role_label ?? '…'}</Text>
          <Text style={styles.faint}>{server}</Text>
        </Card>

        <Card style={{ gap: 10 }}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
            <View style={{ flex: 1, paddingRight: 12 }}>
              <Text style={styles.text}>Push alerts</Text>
              <Text style={styles.faint}>Your account setting; it applies to every device you sign in on.</Text>
            </View>
            <Switch
              accessibilityLabel="Push alerts"
              value={profile?.notify_push ?? false}
              disabled={!profile || saving}
              onValueChange={setPushPreference}
              trackColor={{ true: C.accent, false: C.border }}
            />
          </View>
          <Text style={[styles.faint, { color: push?.ok ? C.good : C.faint }]}>
            {push === null
              ? 'Checking this device…'
              : push.ok
                ? 'This device is registered to receive alerts.'
                : push.reason}
          </Text>
          {push && !push.ok ? (
            <Text style={styles.faint}>While the app is open, alerts still arrive live.</Text>
          ) : null}
        </Card>

        {error ? <ErrorText>{error}</ErrorText> : null}
        <Button title="Sign out" tone="secondary" onPress={signOut} />
      </ScrollView>
    </Screen>
  );
}
