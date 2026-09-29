# Deploy Trading Journal on Vercel

This repository contains two applications. Create **two Vercel projects** from the same GitHub repository: one with Root Directory `backend`, and one with Root Directory `frontend`. Deploy the backend first, then use its production URL for the frontend. Keep their deployment regions close to the database region.

## 1. Create the database and Firebase project

1. Create a PostgreSQL database through a Vercel Marketplace integration such as Neon, or use another hosted PostgreSQL provider. Copy its connection URI. The backend uses PostgreSQL for journal persistence; local SQLite files are not deployed or migrated automatically.
2. Create a Firebase project, enable **Authentication → Email/Password**, and create the account that should access this journal. Copy that account's Firebase UID from the Users screen.
3. In Firebase project settings, create a service account key. Copy the entire JSON as a single Vercel environment variable. Keep it out of Git and local logs.
4. Copy the Firebase web app config values: `apiKey`, `authDomain`, `projectId`, and `appId`. Firebase web config is public; the service account JSON is secret.

## 2. Deploy the backend project

Import the repository in Vercel with Root Directory **`backend`** and the FastAPI/Python framework preset. The `main.py` ASGI entrypoint, `.python-version`, `requirements.txt`, and `vercel.json` are already included. Add these environment variables for Production (and Preview if you want previews):

| Name | Value |
| --- | --- |
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | PostgreSQL connection URI, usually from your integration. SQLAlchemy accepts `postgres://` and `postgresql://`; this app uses psycopg. |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | The full Firebase service account JSON. |
| `ALLOWED_FIREBASE_UIDS` | The Firebase UID(s) allowed into the journal, comma separated. |

Optional reviewer keys are in `backend/.env.example`. The local rules reviewer works without them. Do not set `SQLITE_DB_PATH` for Vercel.

Deploy and check `https://<backend-domain>/` returns the API status. `https://<backend-domain>/api/trades` should return **401** without a Firebase token. The backend refuses to start on Vercel when persistent storage or Firebase access control is missing.

## 3. Deploy the frontend project

Import the same repository again with Root Directory **`frontend`** and the Next.js framework preset. Add these environment variables:

| Name | Value |
| --- | --- |
| `API_UPSTREAM_URL` | `https://<backend-domain>` (origin only, no `/api`) |
| `NEXT_PUBLIC_API_URL` | `/api` |
| `NEXT_PUBLIC_AUTH_REQUIRED` | `true` |
| `NEXT_PUBLIC_FIREBASE_API_KEY` | Firebase web config `apiKey` |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | Firebase web config `authDomain` |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | Firebase web config `projectId` |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | Firebase web config `appId` |

The frontend proxies `/api/*` requests to the backend. Set Firebase Authentication → Settings → Authorized domains to include your frontend production domain. Redeploy the frontend after changing `NEXT_PUBLIC_*` variables, since Next.js embeds them at build time.

## 4. Verify

Open the frontend production URL in a private window. The sign-in page should appear. Sign in with the Firebase account you allowed, add one manual trade, refresh the page, and confirm the trade remains. Sign out and confirm the journal is hidden. Try an account whose UID is not allowlisted; API requests should return 403. Export or back up the hosted PostgreSQL database according to your provider's policy.

## Limits and data migration

Vercel Functions have a **4.5 MB request and response payload limit**. The app caps uploaded CSV and Excel files at 4 MB to leave room for multipart overhead. A report producing more than 4.5 MB of JSON may still exceed the response limit; reduce the report size or add external object storage for larger reports. The app's local SQLite journal is not copied to PostgreSQL; migrate existing data separately before relying on the production journal.

The current schema is created automatically at startup. Before changing columns in a live deployment, add a migration instead of relying on `create_all`, which does not alter existing tables. Store service account credentials only in Vercel environment variables, never in the frontend or repository.
