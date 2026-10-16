import { getItem, KEYS, removeItem, setItem } from './storage';

/** Thrown for any non-2xx response, carrying the API's error body. */
export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
  ) {
    super(ApiError.describe(status, body));
  }

  static describe(status: number, body: unknown): string {
    if (body && typeof body === 'object') {
      const b = body as Record<string, unknown>;
      if (typeof b.detail === 'string') return b.detail;
      const first = Object.entries(b)[0];
      if (first) return `${first[0]}: ${[first[1]].flat().join(' ')}`;
    }
    return `Request failed (${status})`;
  }
}

type Listener = (signedIn: boolean) => void;

/**
 * Minimal API client for the Site-Safe backend.
 *
 * Access tokens are short-lived (30 min by default). On a 401 the client
 * renews once with the refresh token — one renewal at a time, shared by
 * concurrent requests — and retries; if renewal fails the session ends and
 * listeners are told, so the app returns to the sign-in screen.
 */
export class ApiClient {
  private server = '';
  private access: string | null = null;
  private refreshing: Promise<string> | null = null;
  private listeners = new Set<Listener>();

  async load(): Promise<{ server: string; signedIn: boolean; email: string | null }> {
    this.server = (await getItem(KEYS.server)) ?? '';
    this.access = await getItem(KEYS.access);
    return { server: this.server, signedIn: Boolean(this.access), email: await getItem(KEYS.email) };
  }

  get baseUrl() {
    return this.server;
  }

  get accessToken() {
    return this.access;
  }

  onSessionChange(fn: Listener): () => void {
    this.listeners.add(fn);
    return () => {
      this.listeners.delete(fn);
    };
  }

  private emit(signedIn: boolean) {
    this.listeners.forEach((fn) => fn(signedIn));
  }

  /** "192.168.1.20:8000" → "http://192.168.1.20:8000/api/" */
  static normaliseServer(input: string): string {
    let s = input.trim().replace(/\/+$/, '');
    if (!/^https?:\/\//i.test(s)) s = `http://${s}`;
    if (!/\/api$/i.test(s)) s = `${s}/api`;
    return `${s}/`;
  }

  async signIn(serverInput: string, email: string, password: string) {
    const server = ApiClient.normaliseServer(serverInput);
    const res = await fetch(`${server}token/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.trim(), password }),
    });
    const body = await res.json().catch(() => null);
    if (!res.ok) throw new ApiError(res.status, body);
    this.server = server;
    this.access = body.access;
    await setItem(KEYS.server, server);
    await setItem(KEYS.access, body.access);
    await setItem(KEYS.refresh, body.refresh);
    await setItem(KEYS.email, email.trim());
    this.emit(true);
  }

  async signOut() {
    this.access = null;
    await removeItem(KEYS.access);
    await removeItem(KEYS.refresh);
    this.emit(false);
  }

  /** Renew the access token; concurrent callers share one request. */
  renew(): Promise<string> {
    if (this.refreshing) return this.refreshing;
    this.refreshing = (async () => {
      const refresh = await getItem(KEYS.refresh);
      if (!refresh) throw new ApiError(401, { detail: 'Session expired.' });
      const res = await fetch(`${this.server}token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh }),
      });
      const body = await res.json().catch(() => null);
      if (!res.ok) throw new ApiError(res.status, body);
      this.access = body.access;
      await setItem(KEYS.access, body.access);
      if (body.refresh) await setItem(KEYS.refresh, body.refresh);
      return body.access as string;
    })().finally(() => {
      this.refreshing = null;
    });
    return this.refreshing;
  }

  async request<T>(path: string, init: RequestInit = {}, retried = false): Promise<T> {
    const res = await fetch(`${this.server}${path.replace(/^\//, '')}`, {
      ...init,
      headers: {
        Accept: 'application/json',
        ...(init.body ? { 'Content-Type': 'application/json' } : {}),
        ...(this.access ? { Authorization: `Bearer ${this.access}` } : {}),
        ...init.headers,
      },
    });
    if (res.status === 401 && !retried) {
      try {
        await this.renew();
      } catch {
        await this.signOut();
        throw new ApiError(401, { detail: 'Your session has ended. Please sign in again.' });
      }
      return this.request<T>(path, init, true);
    }
    if (res.status === 204) return undefined as T;
    const body = await res.json().catch(() => null);
    if (!res.ok) throw new ApiError(res.status, body);
    return body as T;
  }

  get<T>(path: string) {
    return this.request<T>(path);
  }

  post<T>(path: string, data?: unknown) {
    return this.request<T>(path, { method: 'POST', body: data === undefined ? undefined : JSON.stringify(data) });
  }

  patch<T>(path: string, data: unknown) {
    return this.request<T>(path, { method: 'PATCH', body: JSON.stringify(data) });
  }

  delete<T>(path: string) {
    return this.request<T>(path, { method: 'DELETE' });
  }

  /** ws:// URL for the dashboard socket, carrying the current access token. */
  socketUrl(): string {
    const base = this.server.replace(/^http/i, 'ws').replace(/\/api\/$/, '/');
    return `${base}ws/dashboard/?token=${encodeURIComponent(this.access ?? '')}`;
  }
}

export const api = new ApiClient();

export function asList<T>(data: T[] | { results: T[] }): T[] {
  return Array.isArray(data) ? data : (data?.results ?? []);
}
