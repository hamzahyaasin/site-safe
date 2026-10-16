import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

import { api } from './api';
import { getItem, KEYS, removeItem, setItem } from './storage';

// Must match ANDROID_CHANNEL_ID in backend/sitesafe/notifications.py.
export const ANDROID_CHANNEL_ID = 'safety-alerts';

export type PushStatus =
  | { ok: true; token: string }
  | { ok: false; reason: string };

/**
 * Register this phone for alert pushes.
 *
 * The backend sends through Firebase Cloud Messaging, so this registers the
 * native FCM device token. That needs an Android development or release
 * build that includes the project's google-services.json; Expo Go, iOS and
 * the web build cannot receive these pushes and rely on the live socket
 * while the app is open. The reason is returned so Settings can show it.
 */
export async function registerPush(): Promise<PushStatus> {
  if (Platform.OS !== 'android') {
    return { ok: false, reason: 'Push alerts are delivered to Android builds only.' };
  }
  if (!Device.isDevice) {
    return { ok: false, reason: 'Push alerts need a physical Android phone.' };
  }
  // On Android 13+ the channel must exist before the permission prompt.
  await Notifications.setNotificationChannelAsync(ANDROID_CHANNEL_ID, {
    name: 'Safety alerts',
    // eslint-disable-next-line import/namespace -- re-exported enum the import plugin cannot see
    importance: Notifications.AndroidImportance.MAX,
    vibrationPattern: [0, 400, 200, 400],
    lightColor: '#ef4444',
  });
  let { status } = await Notifications.getPermissionsAsync();
  if (status !== 'granted') {
    ({ status } = await Notifications.requestPermissionsAsync());
  }
  if (status !== 'granted') {
    return { ok: false, reason: 'Notification permission was not granted.' };
  }
  try {
    const { data } = await Notifications.getDevicePushTokenAsync();
    const token = String(data);
    await api.post('v1/fcm-tokens/', { token, device_name: Device.modelName ?? 'Android phone' });
    await setItem(KEYS.pushToken, token);
    return { ok: true, token };
  } catch (e) {
    return {
      ok: false,
      reason: `Could not get a push token (${(e as Error).message}). This build may be missing Firebase configuration.`,
    };
  }
}

export async function unregisterPush(): Promise<void> {
  const token = await getItem(KEYS.pushToken);
  if (!token) return;
  try {
    await api.delete(`v1/fcm-tokens/${encodeURIComponent(token)}/`);
  } finally {
    await removeItem(KEYS.pushToken);
  }
}

/** Show alerts as banners even while the app is open. */
export function configureForegroundDisplay() {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
    }),
  });
}

/** alert_id carried in a tapped notification, if any. */
export function alertIdFrom(response: Notifications.NotificationResponse | null): number | null {
  const raw = response?.notification.request.content.data?.alert_id;
  const id = Number(raw);
  return Number.isInteger(id) && id > 0 ? id : null;
}
