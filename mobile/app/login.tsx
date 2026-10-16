import { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, Text, View } from 'react-native';

import { Button, ErrorText, Field, Screen, styles } from '@/components/ui';
import { C } from '@/constants/theme';
import { useSession } from '@/context/Session';

export default function Login() {
  const { signIn, server: savedServer, email: savedEmail } = useSession();
  const [server, setServer] = useState(savedServer.replace(/\/api\/$/, '') || '');
  const [email, setEmail] = useState(savedEmail ?? '');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submit() {
    setBusy(true);
    setError('');
    try {
      await signIn(server, email, password);
    } catch (e) {
      const msg = (e as Error).message;
      setError(
        msg === 'Network request failed' || msg.startsWith('Failed to fetch')
          ? 'Cannot reach the server. Check the address and that this phone is on the same network.'
          : msg,
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={{ flexGrow: 1, justifyContent: 'center', padding: 24, gap: 16 }}>
          <View style={{ gap: 4, marginBottom: 8 }}>
            <Text style={{ color: C.accent, fontSize: 28, fontWeight: '800' }}>Site-Safe</Text>
            <Text style={styles.muted}>Safety alerts for site supervisors</Text>
          </View>
          <Field
            label="Server address"
            value={server}
            onChangeText={setServer}
            placeholder="192.168.1.20:8000"
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="url"
          />
          <Field
            label="Email"
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            autoComplete="email"
            keyboardType="email-address"
          />
          <Field label="Password" value={password} onChangeText={setPassword} secureTextEntry onSubmitEditing={submit} />
          {error ? <ErrorText>{error}</ErrorText> : null}
          <Button title="Sign in" onPress={submit} busy={busy} disabled={!server || !email || !password} />
          <Text style={styles.faint}>Use the address of the computer running the Site-Safe backend.</Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </Screen>
  );
}
