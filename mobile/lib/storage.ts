import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

// Tokens live in the OS keychain/keystore on devices. expo-secure-store has
// no web implementation, so the web build (used for development and
// screenshots) falls back to localStorage.
const isWeb = Platform.OS === 'web';

export async function getItem(key: string): Promise<string | null> {
  if (isWeb) return globalThis.localStorage?.getItem(key) ?? null;
  return SecureStore.getItemAsync(key);
}

export async function setItem(key: string, value: string): Promise<void> {
  if (isWeb) {
    globalThis.localStorage?.setItem(key, value);
    return;
  }
  await SecureStore.setItemAsync(key, value);
}

export async function removeItem(key: string): Promise<void> {
  if (isWeb) {
    globalThis.localStorage?.removeItem(key);
    return;
  }
  await SecureStore.deleteItemAsync(key);
}

export const KEYS = {
  server: 'sitesafe.server',
  access: 'sitesafe.access',
  refresh: 'sitesafe.refresh',
  email: 'sitesafe.email',
  pushToken: 'sitesafe.pushToken',
} as const;
