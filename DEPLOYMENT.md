# Deployment Guide

This guide walks open-source users through deploying the Background Removal API, with **Railway** as the primary target. The same steps apply to any platform that supports Python and provides S3-compatible storage (e.g. Render, Fly.io + external storage).

---

## Prerequisites

- A [Railway](https://railway.app) account (or another host)
- A **Railway Storage Bucket** (or any S3-compatible bucket) for storing processed images
- Git

---

## 1. Deploy to Railway

### 1.1 Create a new project

1. Go to [railway.app](https://railway.app) and sign in.
2. Click **New Project**.
3. Choose **Deploy from GitHub repo** and connect your GitHub account.
4. Select the `bg-remover-api` repository (or your fork).
5. Railway will detect the Python app and use the **Procfile**:
   ```text
   web: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

### 1.2 Configure the service

- **Root directory:** Leave default (project root).
- **Build command:** Railway usually auto-detects; if needed, leave empty or use `pip install -r requirements.txt`.
- **Start command:** From Procfile (`uvicorn main:app --host 0.0.0.0 --port $PORT`).
- **Health check:** In the service **Settings**, set **Health Check Path** to `/health` so Railway can verify the app is running.

### 1.3 Add a Storage Bucket (Railway)

1. In the same project, click **+ New** → **Database** / **More** → **Bucket** (or **Storage**).
2. Create a bucket and choose a region.
3. Open the bucket → **Credentials** tab.
4. You will see:
   - **BUCKET** (bucket name, e.g. `my-bucket-abc123`)
   - **ENDPOINT** (`https://storage.railway.app`)
   - **ACCESS_KEY_ID**
   - **SECRET_ACCESS_KEY**
   - **REGION** (e.g. `auto`)

Keep this tab open; you will inject these into your API service.

### 1.4 Set environment variables

1. Click your **API service** (the one deployed from the repo).
2. Go to **Variables**.
3. Add:

   | Variable | Value | Notes |
   |----------|--------|--------|
   | `API_KEY` | A strong random string | Used in `X-API-Key` header; generate with e.g. `openssl rand -hex 32` |
   | `BUCKET` | From bucket Credentials tab | Exact value from Railway |
   | `ENDPOINT` | `https://storage.railway.app` | From bucket Credentials |
   | `ACCESS_KEY_ID` | From bucket Credentials | |
   | `SECRET_ACCESS_KEY` | From bucket Credentials | |
   | `REGION` | `auto` (or value from Credentials) | |

4. **Optional:** Use **Variable References** so the bucket injects its own variables into the service:
   - In the API service Variables, click **Add Reference** and select the bucket.
   - Choose the preset (e.g. **AWS SDK** or **Generic**) so `BUCKET`, `ENDPOINT`, `ACCESS_KEY_ID`, `SECRET_ACCESS_KEY`, `REGION` are set automatically.
   - Then add only `API_KEY` manually.

### 1.5 Deploy and get the URL

1. Trigger a deploy (push to the connected branch or **Deploy** in the dashboard).
2. In the API service, open **Settings** → **Networking** → **Generate Domain** to get a public URL (e.g. `https://your-app.up.railway.app`).

---

## 2. Verify deployment

### Health check

```bash
curl https://your-app.up.railway.app/health
```

Expected: `{"status":"healthy"}`

### Remove background (binary upload)

```bash
curl -X POST https://your-app.up.railway.app/api/v1/remove-bg/binary \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "image=@/path/to/your/image.jpg"
```

### Remove background (image URL)

```bash
curl -X POST https://your-app.up.railway.app/api/v1/remove-bg/url \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://example.com/sample.jpg"}'
```

Replace `YOUR_API_KEY` with the value you set for `API_KEY`.

---

## 3. Railway configuration files (included in repo)

| File | Purpose |
|------|--------|
| **Procfile** | Tells Railway how to start the app: `web: uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **railway.json** | Optional; can set health check path and restart policy for Railway |

You do not need to change these unless you want a custom start command or health path.

---

## 4. Using a different S3-compatible storage

If you use **AWS S3**, **Cloudflare R2**, **MinIO**, or another S3-compatible provider instead of Railway Storage:

1. Set the same variables, but use your provider’s values:
   - `BUCKET` or `RAILWAY_BUCKET_NAME` → bucket name  
   - `ENDPOINT` or `RAILWAY_BUCKET_ENDPOINT` → provider endpoint (e.g. R2: `https://<account_id>.r2.cloudflarestorage.com`)  
   - `ACCESS_KEY_ID` / `SECRET_ACCESS_KEY` (or `RAILWAY_BUCKET_ACCESS_KEY` / `RAILWAY_BUCKET_SECRET_KEY`)  
   - `REGION` if required  

2. For **public read access** (optional): set `RAILWAY_BUCKET_URL` to the public base URL (e.g. your CDN or bucket URL). Then the API will return that URL instead of a presigned URL.

3. Railway buckets are **private**; the app returns **presigned URLs** (7-day validity) when `RAILWAY_BUCKET_URL` is not set.

---

## 5. Security checklist

- [ ] Use a **strong, random `API_KEY`** (e.g. 32+ character secret).
- [ ] Never commit `.env` or real credentials; only commit `.env.example` with placeholders.
- [ ] Restrict CORS in production if you know your front-end origins (edit `main.py` `allow_origins`).
- [ ] Consider rate limiting or firewall rules if the API is public.

---

## 6. Troubleshooting

| Issue | What to check |
|-------|----------------|
| 401 Unauthorized | `API_KEY` in Variables matches the `X-API-Key` header. |
| 500 / storage error | Bucket variables (`BUCKET`, `ENDPOINT`, `ACCESS_KEY_ID`, `SECRET_ACCESS_KEY`) are set and correct; check Railway bucket Credentials. |
| Health check failing | Health path is exactly `/health`; app listens on `$PORT`. |
| Build fails | Ensure `requirements.txt` is in the repo and Railway uses Python; `rembg[cpu]` may take a few minutes to install. |

For more details, see the main [README](README.md) and [Railway docs](https://docs.railway.com/).
