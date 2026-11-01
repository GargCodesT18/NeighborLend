# NeighborLend

A peer-to-peer lending platform with a React/Vite website, FastAPI API, SQLAlchemy database models, Supabase PostgreSQL and Storage support, and an Android app packaged from the same frontend with Capacitor.

## Features

- Browse listings, upload item photos, create borrowing requests, and negotiate rental offers.
- Conversations are between borrowers and lenders independently of listings. Each offer identifies its listing; messages remain linked by `conversation_id`.
- Chat shows an initial loading state, then quietly refreshes the open conversation every five seconds while visible. Supabase Realtime is not configured for chat.
- CAPTCHA-protected registration, email OTP verification, JWT login, and optional Google sign-in.
- Existing YOLO listing-photo analysis. A separate Gemini CLI compares before/after damage photos and saves JSON; it is not connected to borrowing workflows.
- The website and installable Android app are separate clients of the same deployed API.

## Local development

Requirements: Python 3.10+, Node.js/npm, and Git. Create `.env` from `.env.example` only if you do not already have one. For local work, set `DATABASE_URL` to SQLite or your PostgreSQL URL and generate a private `JWT_SECRET`:

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Keep `.env`, SMTP keys, database credentials, Supabase service-role keys, and signing keys private. Never place backend secrets in `VITE_*` variables.

Start the backend in one terminal:

```powershell
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Start the website in another terminal:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open `http://localhost:5173`; FastAPI docs are at `http://localhost:8000/docs`, and readiness is at `/api/health`. Local Vite proxies `/api` and `/uploads` to FastAPI. Do not run `backend/seed_data.py` against data you need: it drops and recreates database tables.

## Deploy the backend (Render)

A Render Blueprint is provided in `render.yaml`. Create a Render Blueprint from this repository, or create a Docker web service with repository root as the Docker context and `backend/Dockerfile` as the Dockerfile. The container binds to Render's `PORT` and exposes `/api/health` for readiness. Set these values in Render's private environment settings; do not commit them:

| Variable | Value |
|---|---|
| `APP_ENV` | `production` (set by the Render Blueprint). |
| `DATABASE_URL` | Supabase PostgreSQL connection URL (prefer its session pooler if the host requires IPv4); include SSL as required by Supabase. |
| `JWT_SECRET` | A new random secret, at least 32 characters. |
| `CORS_ORIGINS` | Comma-separated exact origins: the deployed website URL and `https://localhost` for Capacitor Android. |
| `SUPABASE_URL` | Supabase project URL. |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend-only service-role key. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_USE_TLS` | Brevo SMTP values for registration OTP delivery. |
| `GOOGLE_CLIENT_ID` | Google OAuth Web client ID used to validate ID tokens. |
| `PUBLIC_BASE_URL` | Public API URL, needed for local-disk upload fallback; use Supabase Storage for persistent production photos. |

`AI_MODEL_PATH` defaults to `/app/ai_service/best_model.pt` in the Render Blueprint; the backend image includes the YOLO weights. The server health check checks database connectivity. The API applies its existing startup schema migration; it preserves conversation/message rows and leaves `borrow_requests.listing_id` and `listing_photos.listing_id` intact.

## Configure Supabase

1. In Supabase, create or select the PostgreSQL project and copy its connection URL into Render's `DATABASE_URL`. Keep the password private.
2. Create a public Storage bucket named `listing-images`, or let the backend configure it on the first upload. Set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` only on the backend.
3. Public listing-photo URLs returned by Supabase load directly in the website and Android app. The client also maps legacy `/uploads/` paths to the configured API origin.

The API falls back to local disk if Supabase Storage variables are absent. Render's container filesystem is ephemeral, so that fallback is not suitable for persistent production uploads unless you also configure a persistent disk and correct `PUBLIC_BASE_URL`.

## Deploy the website (Vercel)

Create a Vercel project with **Root Directory** `frontend`. `frontend/vercel.json` configures the Vite build, `dist` output, and SPA route fallback. Set these build-time variables in Vercel:

- `VITE_API_BASE_URL=https://<your-render-service>.onrender.com/api`
- `VITE_GOOGLE_CLIENT_ID=<your-google-web-client-id>` (only if Google sign-in is enabled)

Deploy the website independently; users can access its Vercel URL without installing the Android app. Never add database, JWT, SMTP, Supabase service-role, or private AI keys to Vercel/Vite variables. For local builds, `VITE_API_BASE_URL` may be omitted and Axios uses `/api`; `npm run build:web` requires a public HTTPS API URL ending in `/api`.

After the site has a stable URL, set Render's `CORS_ORIGINS` to that exact origin, separated by a comma from `https://localhost` (for example `https://your-site.vercel.app,https://localhost`). Add the website origin to the Google OAuth Web client's authorized JavaScript origins. Set the same Web client ID as `GOOGLE_CLIENT_ID` on Render and `VITE_GOOGLE_CLIENT_ID` on Vercel.

## Email verification (Brevo)

For Brevo, use `smtp-relay.brevo.com`, port `587`, the SMTP login shown in Brevo, an SMTP key (not an API key/account password), and a sender verified in Brevo. Enable STARTTLS with `SMTP_USE_TLS=true`. Restart the backend after changing settings.

If registration returns `503`, the backend logs a safe SMTP error type and response code:

- `525`: authorize the backend's public outbound IP in Brevo SMTP security settings; `127.0.0.1` is not that address.
- `535`: check the SMTP login and SMTP key.
- `550`/`553`: check the verified sender address.

## Android APK (Capacitor)

The existing Android project and application ID `com.neighborlend.app` are preserved. `webDir` is `dist`; the release build bundles the frontend and does not need a development server. Install Android Studio with Android SDK Platform 36. In Android Studio, set **Settings → Build, Execution, Deployment → Build Tools → Gradle → Gradle JDK** to its bundled JDK. From `frontend/`, set the same deployed HTTPS API URL used by Vercel, then sync and open the existing project:

```powershell
$env:VITE_API_BASE_URL = "https://<your-render-service>.onrender.com/api"
$env:VITE_GOOGLE_CLIENT_ID = "<your-google-web-client-id>"
npm.cmd install
npm.cmd run assets:android
npm.cmd run build:mobile
npm.cmd run cap:sync:android
npm.cmd run cap:open:android
```

Build a debug/test APK from `frontend/android/`:

```powershell
.\gradlew.bat assembleDebug
```

Output: `frontend/android/app/build/outputs/apk/debug/app-debug.apk`.

### Sign a shareable release APK

Create a keystore **outside the repository** and keep a secure backup. Do not lose it: future updates must use the same signing identity.

```powershell
keytool -genkeypair -v -keystore "$env:USERPROFILE\neighborlend-release.jks" -alias neighborlend -keyalg RSA -keysize 2048 -validity 10000
```

Set these PowerShell variables to the keystore path and credentials (do not save them in Git), then build from `frontend/android/`:

```powershell
$env:ANDROID_KEYSTORE_PATH = "$env:USERPROFILE\neighborlend-release.jks"
$env:ANDROID_KEYSTORE_PASSWORD = "<keystore-password>"
$env:ANDROID_KEY_ALIAS = "neighborlend"
$env:ANDROID_KEY_PASSWORD = "<key-password>"
.\gradlew.bat assembleRelease
```

With all four variables set, Gradle signs the APK at `app/build/outputs/apk/release/app-release.apk`. Without them, Gradle creates an unsigned release APK that users cannot install as a normal shareable release. Android Studio alternative: **Build → Generate Signed Bundle / APK → APK**, select/create the keystore, choose the `release` variant, and finish the wizard. Save the keystore and passwords in a secure password manager and offline backup; never regenerate it for an update to this app ID.

Google sign-in on Android also needs an Android OAuth client registered for package `com.neighborlend.app` and the signing certificate SHA-1 (debug and release certificates have different fingerprints). The Web client ID remains the ID-token audience.

## Checks and troubleshooting

Run from the repository root or the indicated directory:

```powershell
# Backend tests (requires pytest in the selected Python environment)
cd backend
python -m pytest -q

# Website build; requires VITE_API_BASE_URL in the shell
cd ..\frontend
npm.cmd run build:web

# Android sync/build
npm.cmd run cap:sync:android
.\android\gradlew.bat assembleDebug
```

Common issues: an HTTP API URL is blocked by HTTPS websites and Android; set the deployed `VITE_API_BASE_URL` to HTTPS and ending in `/api`. CORS failures mean the website origin or `https://localhost` is missing from backend `CORS_ORIGINS`. Supabase images require public read access to `listing-images`; upload errors usually indicate missing backend Supabase settings or bucket permissions. Google login requires matching Web client IDs and the Android package/SHA-1 registration. Render `503`/unhealthy status: inspect backend logs and verify its database URL and connectivity.
