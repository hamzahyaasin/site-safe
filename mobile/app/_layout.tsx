import { DarkTheme, Stack, ThemeProvider, useRouter, useSegments } from 'expo-router';
import * as Notifications from 'expo-notifications';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { Platform } from 'react-native';
import 'react-native-reanimated';

import { C } from '@/constants/theme';
import { LiveProvider } from '@/context/Live';
import { SessionProvider, useSession } from '@/context/Session';
import { alertIdFrom, configureForegroundDisplay } from '@/lib/push';

export { ErrorBoundary } from 'expo-router';

SplashScreen.preventAutoHideAsync();
if (Platform.OS !== 'web') configureForegroundDisplay();

const theme = {
  ...DarkTheme,
  colors: { ...DarkTheme.colors, background: C.bg, card: C.card, border: C.border, primary: C.accent, text: C.text },
};

export default function RootLayout() {
  return (
    <SessionProvider>
      <LiveProvider>
        <ThemeProvider value={theme}>
          <StatusBar style="light" />
          <Gate />
        </ThemeProvider>
      </LiveProvider>
    </SessionProvider>
  );
}

/** Send signed-out users to sign-in, and open alerts from tapped pushes. */
function Gate() {
  const { ready, signedIn } = useSession();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (!ready) return;
    SplashScreen.hideAsync();
    const onLogin = segments[0] === 'login';
    if (!signedIn && !onLogin) router.replace('/login');
    else if (signedIn && onLogin) router.replace('/');
  }, [ready, signedIn, segments, router]);

  useEffect(() => {
    if (!ready || !signedIn || Platform.OS === 'web') return undefined;
    const open = (response: Notifications.NotificationResponse | null) => {
      const id = alertIdFrom(response);
      if (id) router.push({ pathname: '/alert/[id]', params: { id: String(id) } });
    };
    Notifications.getLastNotificationResponseAsync().then((r) => {
      open(r);
      if (r) void Notifications.clearLastNotificationResponseAsync();
    });
    const sub = Notifications.addNotificationResponseReceivedListener(open);
    return () => sub.remove();
  }, [ready, signedIn, router]);

  if (!ready) return null;
  return (
    <Stack screenOptions={{ headerStyle: { backgroundColor: C.card }, headerTintColor: C.text }}>
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen name="login" options={{ headerShown: false }} />
      <Stack.Screen name="alert/[id]" options={{ title: 'Alert' }} />
    </Stack>
  );
}
