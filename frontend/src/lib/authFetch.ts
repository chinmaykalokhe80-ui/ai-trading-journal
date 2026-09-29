export async function authFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  if (process.env.NEXT_PUBLIC_AUTH_REQUIRED !== 'true') return fetch(input, init);
  const { auth } = await import('@/lib/firebase');
  const user = auth.currentUser;
  if (!user) throw new Error('Please sign in to access your journal.');
  const headers = new Headers(init.headers);
  headers.set('Authorization', `Bearer ${await user.getIdToken()}`);
  return fetch(input, { ...init, headers });
}
