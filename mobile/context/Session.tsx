import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { api } from '@/lib/api';
import { registerPush, unregisterPush, type PushStatus } from '@/lib/push';
import type { Profile } from '@/lib/types';

interface SessionValue {
  ready: boolean;
  signedIn: boolean;
  server: string;
  email: string | null;
  profile: Profile | null;
  push: PushStatus | null;
  signIn: (server: string, email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const SessionContext = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [signedIn, setSignedIn] = useState(false);
  const [server, setServer] = useState('');
  const [email, setEmail] = useState<string | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [push, setPush] = useState<PushStatus | null>(null);

  const refreshProfile = useCallback(async () => {
    try {
      setProfile(await api.get<Profile>('v1/profile/'));
    } catch {
      setProfile(null);
    }
  }, []);

  useEffect(() => {
    api.load().then((state) => {
      setServer(state.server);
      setEmail(state.email);
      setSignedIn(state.signedIn);
      setReady(true);
    });
    return api.onSessionChange((value) => {
      setSignedIn(value);
      if (!value) setProfile(null);
    });
  }, []);

  useEffect(() => {
    if (!signedIn) return;
    const t = setTimeout(refreshProfile, 0);
    // Register this phone for alert pushes as soon as the user is signed in.
    registerPush().then(setPush, (e) => setPush({ ok: false, reason: String(e?.message ?? e) }));
    return () => clearTimeout(t);
  }, [signedIn, refreshProfile]);

  const signIn = useCallback(async (serverInput: string, mail: string, password: string) => {
    await api.signIn(serverInput, mail, password);
    setServer(api.baseUrl);
    setEmail(mail.trim());
  }, []);

  const signOut = useCallback(async () => {
    // Stop pushes to this phone before the credentials needed to do so go.
    await unregisterPush().catch(() => undefined);
    await api.signOut();
  }, []);

  const value = useMemo(
    () => ({ ready, signedIn, server, email, profile, push: signedIn ? push : null, signIn, signOut, refreshProfile }),
    [ready, signedIn, server, email, profile, push, signIn, signOut, refreshProfile],
  );
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error('useSession must be used inside SessionProvider');
  return ctx;
}
