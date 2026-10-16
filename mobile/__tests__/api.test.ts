import { ApiClient, ApiError } from '@/lib/api';

const store: Record<string, string> = {};
jest.mock('@/lib/storage', () => ({
  KEYS: { server: 's', access: 'a', refresh: 'r', email: 'e', pushToken: 'p' },
  getItem: jest.fn(async (k: string) => store[k] ?? null),
  setItem: jest.fn(async (k: string, v: string) => {
    store[k] = v;
  }),
  removeItem: jest.fn(async (k: string) => {
    delete store[k];
  }),
}));

function json(status: number, body: unknown) {
  return Promise.resolve({ ok: status < 400, status, json: async () => body } as Response);
}

beforeEach(() => {
  for (const k of Object.keys(store)) delete store[k];
  globalThis.fetch = jest.fn() as unknown as typeof fetch;
});

test('normalises a bare server address', () => {
  expect(ApiClient.normaliseServer('192.168.1.20:8000')).toBe('http://192.168.1.20:8000/api/');
  expect(ApiClient.normaliseServer('https://site.example/api/')).toBe('https://site.example/api/');
});

test('sign in stores tokens and builds the socket URL', async () => {
  (fetch as jest.Mock).mockReturnValueOnce(json(200, { access: 'A1', refresh: 'R1' }));
  const client = new ApiClient();
  await client.signIn('10.0.0.5:8000', ' o@x.io ', 'pw');
  expect(store).toMatchObject({ s: 'http://10.0.0.5:8000/api/', a: 'A1', r: 'R1', e: 'o@x.io' });
  expect(client.socketUrl()).toBe('ws://10.0.0.5:8000/ws/dashboard/?token=A1');
});

test('a failed sign-in surfaces the API message', async () => {
  (fetch as jest.Mock).mockReturnValueOnce(json(401, { detail: 'No active account found' }));
  await expect(new ApiClient().signIn('h:1', 'a@b.c', 'x')).rejects.toThrow('No active account found');
});

test('concurrent 401s share one refresh and then retry', async () => {
  Object.assign(store, { s: 'http://h/api/', a: 'OLD', r: 'R1' });
  const client = new ApiClient();
  await client.load();
  const calls: string[] = [];
  (fetch as jest.Mock).mockImplementation((url: string, init: RequestInit) => {
    calls.push(url);
    if (url.endsWith('token/refresh/')) return json(200, { access: 'NEW', refresh: 'R2' });
    const auth = (init.headers as Record<string, string>).Authorization;
    return auth === 'Bearer NEW' ? json(200, [{ id: 1 }]) : json(401, { detail: 'expired' });
  });
  const [a, b] = await Promise.all([client.get('alerts/'), client.get('workers/')]);
  expect(a).toEqual([{ id: 1 }]);
  expect(b).toEqual([{ id: 1 }]);
  expect(calls.filter((u) => u.endsWith('token/refresh/'))).toHaveLength(1);
  expect(store.a).toBe('NEW');
  expect(store.r).toBe('R2');
});

test('a failed refresh ends the session', async () => {
  Object.assign(store, { s: 'http://h/api/', a: 'OLD', r: 'BAD' });
  const client = new ApiClient();
  await client.load();
  const seen: boolean[] = [];
  client.onSessionChange((v) => seen.push(v));
  (fetch as jest.Mock).mockImplementation((url: string) =>
    url.endsWith('token/refresh/') ? json(401, { detail: 'invalid' }) : json(401, {}),
  );
  await expect(client.get('alerts/')).rejects.toBeInstanceOf(ApiError);
  expect(seen).toEqual([false]);
  expect(store.a).toBeUndefined();
  expect(store.r).toBeUndefined();
});

test('field errors become readable messages', () => {
  expect(new ApiError(400, { vest: ['Already assigned.'] }).message).toBe('vest: Already assigned.');
});
