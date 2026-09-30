# Deploy Trading Journal on Vercel

This repository uses one Vercel **Services** project for the Next.js frontend and FastAPI backend. Import the repository with the project Root Directory left at the repository root and Framework Preset set to **Services**. The root `vercel.json` builds both services and routes `/api/*` to FastAPI and all other paths to Next.js on the same domain.

## 1. Prepare storage and authentication

1. Create a hosted PostgreSQL database through a Vercel Marketplace integration such as Neon, or use an existing hosted PostgreSQL provider. Copy its connection URI. Local SQLite data is not migrated automatically.
2. Create a Firebase project, enable **Authentication → Email/Password**, and create the account that should access the journal. Copy that account's Firebase UID from Authentication → Users.
3. In Firebase project settings, create a service account key. Copy the entire JSON for the backend. Keep it out of Git and local logs.
4. Register a Firebase web app and copy its `apiKey`, `authDomain`, `projectId`, and `appId`. These web config values are public; the service account JSON is secret.

## 2. Configure the Vercel project

In Project Settings → Environment Variables, add the following variables to Production. Add them to Preview too if preview deployments should work.

| Name | Value |
| --- | --- |
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | Hosted PostgreSQL connection URI. `postgres://` and `postgresql://` are accepted. |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Full Firebase service account JSON. |
| `ALLOWED_FIREBASE_UIDS` | Allowed Firebase UID(s), comma separated. |
| `NEXT_PUBLIC_API_URL` | `/api` |
| `NEXT_PUBLIC_AUTH_REQUIRED` | `true` |
| `NEXT_PUBLIC_FIREBASE_API_KEY` | Firebase web config `apiKey` |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | Firebase web config `authDomain` |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | Firebase web config `projectId` |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | Firebase web config `appId` |

The backend refuses to start without persistent storage and Firebase access control. Do not set `SQLITE_DB_PATH` on Vercel. `API_UPSTREAM_URL` is only for a separate frontend project; leave it unset in the Services project because the root routing table handles `/api/*`.

In Firebase Authentication → Settings → Authorized domains, add the Vercel production domain. Redeploy after changing environment variables; Next.js embeds `NEXT_PUBLIC_*` values at build time.

## 3. Verify

Open the Vercel production URL in a private window and sign in. `/api/trades` should return **401** without a Firebase token. Add one manual trade, refresh, and confirm it persists. Sign out and confirm the journal is hidden. An account whose UID is not allowlisted should receive **403** from API requests. Back up the hosted PostgreSQL database according to the provider's policy.

## Limits and data migration

Vercel Functions have a **4.5 MB request and response payload limit**. The app caps uploaded CSV and Excel files at 4 MB to leave room for multipart overhead. A large report response may still exceed the limit. The local SQLite journal is not copied to PostgreSQL; migrate existing data separately before relying on the production journal.

The current schema is created automatically at startup. Before changing columns in a live deployment, add a migration because `create_all` does not alter existing tables. Keep service account credentials only in Vercel environment variables.
