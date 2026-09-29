import type { NextConfig } from "next";

if (process.env.VERCEL) {
  const required = [
    'API_UPSTREAM_URL', 'NEXT_PUBLIC_FIREBASE_API_KEY',
    'NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN', 'NEXT_PUBLIC_FIREBASE_PROJECT_ID',
    'NEXT_PUBLIC_FIREBASE_APP_ID',
  ];
  const missing = required.filter((name) => !process.env[name]);
  if (missing.length || process.env.NEXT_PUBLIC_AUTH_REQUIRED !== 'true' || process.env.NEXT_PUBLIC_API_URL !== '/api') {
    throw new Error(`Vercel deployment configuration is incomplete. Set ${missing.join(', ') || 'NEXT_PUBLIC_AUTH_REQUIRED=true and NEXT_PUBLIC_API_URL=/api'}.`);
  }
  if (!process.env.API_UPSTREAM_URL?.startsWith('https://')) {
    throw new Error('API_UPSTREAM_URL must be an HTTPS backend origin.');
  }
}

const nextConfig: NextConfig = {
  async rewrites() {
    const upstream = process.env.API_UPSTREAM_URL?.replace(/\/$/, '');
    return upstream ? [{ source: '/api/:path*', destination: `${upstream}/api/:path*` }] : [];
  },
};

export default nextConfig;
