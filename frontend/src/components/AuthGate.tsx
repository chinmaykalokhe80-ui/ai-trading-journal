'use client';

import { useEffect, useState } from 'react';
import type { User } from 'firebase/auth';

export function AuthGate({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  useEffect(() => {
    let unsubscribe = () => {};
    let active = true;
    Promise.all([import('@/lib/firebase'), import('firebase/auth')]).then(([{ auth }, { onAuthStateChanged }]) => {
      if (active) unsubscribe = onAuthStateChanged(auth, (nextUser) => { setUser(nextUser); setReady(true); });
    }).catch(() => { if (active) { setError('Firebase configuration is unavailable.'); setReady(true); } });
    return () => { active = false; unsubscribe(); };
  }, []);
  if (!ready) return <main className="min-h-screen bg-slate-950 p-8 text-slate-200">Checking sign-in…</main>;
  if (!user) return <main className="min-h-screen bg-slate-950 flex items-center justify-center p-4 text-slate-100">
    <form className="w-full max-w-sm rounded-2xl border border-slate-700 bg-slate-900 p-6 space-y-4" onSubmit={async (event) => {
      event.preventDefault(); setError('');
      try { const [{ auth }, { signInWithEmailAndPassword }] = await Promise.all([import('@/lib/firebase'), import('firebase/auth')]); await signInWithEmailAndPassword(auth, email, password); }
      catch { setError('Sign-in failed. Check your credentials or ask the journal owner for access.'); }
    }}>
      <h1 className="text-xl font-bold">Sign in to Trading Journal</h1>
      <label className="block text-sm">Email<input required type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-950 p-2" /></label>
      <label className="block text-sm">Password<input required type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-950 p-2" /></label>
      {error && <p role="alert" className="text-sm text-rose-300">{error}</p>}
      <button className="w-full rounded-lg bg-cyan-600 p-2 font-semibold hover:bg-cyan-500">Sign in</button>
    </form>
  </main>;
  return <><div className="bg-slate-950 px-4 pt-3 text-right text-xs text-slate-400">{user.email} · <button onClick={async () => { const [{ auth }, { signOut }] = await Promise.all([import('@/lib/firebase'), import('firebase/auth')]); await signOut(auth); }} className="text-cyan-300 underline">Sign out</button></div>{children}</>;
}
