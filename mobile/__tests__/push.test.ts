import { alertIdFrom, registerPush } from '@/lib/push';

jest.mock('expo-notifications', () => ({}));
jest.mock('expo-device', () => ({ isDevice: true, modelName: 'Test' }));
jest.mock('@/lib/api', () => ({ api: { post: jest.fn(), delete: jest.fn() } }));

test('reads alert_id from a tapped notification', () => {
  const response = (data: unknown) => ({ notification: { request: { content: { data } } } }) as any;
  expect(alertIdFrom(response({ alert_id: '42' }))).toBe(42);
  expect(alertIdFrom(response({ alert_id: 'x' }))).toBeNull();
  expect(alertIdFrom(null)).toBeNull();
});

test('non-Android platforms explain why push is unavailable', async () => {
  // jest-expo's default preset runs as iOS.
  const status = await registerPush();
  expect(status).toEqual({ ok: false, reason: 'Push alerts are delivered to Android builds only.' });
});
