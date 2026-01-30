# Background Removal API

**Open-source** production-ready API that removes backgrounds from product images using **rembg** (u2net), uploads results to an S3-compatible storage bucket (e.g. Railway Storage), and returns a URL to the processed image. Designed for deployment on **Railway** and integration with **n8n** or any HTTP client.

- **Two endpoints:** upload an image (binary) or pass an image URL.
- **API key auth**, 10MB max image size, PNG/JPG/JPEG/WEBP.
- **Railway-ready:** Procfile + `railway.json` included; see [DEPLOYMENT.md](DEPLOYMENT.md) for a full deployment guide.

## Tech Stack

- **Python 3.10+**
- **FastAPI** – web framework
- **rembg** – background removal (u2net model)
- **Pillow** – image processing
- **boto3** – S3-compatible storage (AWS S3, Cloudflare R2, MinIO, etc.)
- **uvicorn** – ASGI server

## Project Structure

```
project-root/
├── main.py                 # FastAPI application
├── requirements.txt        # Python dependencies
├── .env.example            # Env template (copy to .env locally)
├── .gitignore
├── Procfile                # Railway start command
├── railway.json            # Railway config (health check, etc.)
├── DEPLOYMENT.md            # Deployment guide for open-source users
├── LICENSE                 # MIT
├── utils/
│   ├── __init__.py
│   ├── auth.py             # API key validation
│   ├── image_processor.py  # Background removal (rembg u2net)
│   └── storage.py          # S3-compatible bucket upload
└── README.md
```

## Setup

### 1. Clone and install

```bash
cd bg-remover-api
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 2. Environment variables

Copy `.env.example` to `.env` and fill in your values:

```powershell
# Windows (PowerShell)
Copy-Item .env.example .env
```

Then edit `.env`: set `API_KEY` to any secret you'll use in the `X-API-Key` header (e.g. `my-local-secret`). For Railway storage use `BUCKET`, `ENDPOINT`, `ACCESS_KEY_ID`, `SECRET_ACCESS_KEY`, `REGION` from your bucket's Credentials tab (see `.env.example`).

### 3. Run locally

From the project folder, with your venv activated:

```powershell
# Windows
.\.venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

```bash
# macOS/Linux
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

Then open:

- **API root:** http://localhost:8000  
- **Docs (Swagger):** http://localhost:8000/docs  
- **Health:** http://localhost:8000/health  

Use the same `API_KEY` value in the `X-API-Key` header when calling the remove-bg endpoints.  

## API Endpoints

### Health check

```bash
GET /health
```

Response: `{"status": "healthy"}`

### 1. Remove background (binary upload)

```bash
POST /api/v1/remove-bg/binary
```

- **Auth:** `X-API-Key: your-api-key`
- **Body:** `multipart/form-data`, field name: `image`
- **Formats:** PNG, JPG, JPEG, WEBP
- **Max size:** 10MB

**Example (curl):**

```bash
curl -X POST http://localhost:8000/api/v1/remove-bg/binary \
  -H "X-API-Key: your-secure-api-key-here" \
  -F "image=@/path/to/product-image.jpg"
```

### 2. Remove background (image URL)

```bash
POST /api/v1/remove-bg/url
```

- **Auth:** `X-API-Key: your-api-key`
- **Body:** `{"image_url": "https://example.com/image.jpg"}`

**Example (curl):**

```bash
curl -X POST http://localhost:8000/api/v1/remove-bg/url \
  -H "X-API-Key: your-secure-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://example.com/product.jpg"}'
```

### Success response (both endpoints)

```json
{
  "success": true,
  "original_url": "https://...",
  "processed_url": "https://your-bucket-url/bg-removed-xxx-xxx.png",
  "processing_time": 2.34,
  "image_dimensions": {
    "width": 1920,
    "height": 1080
  }
}
```

For `/binary`, `original_url` is `""`.

### Error response

All errors return:

```json
{
  "error": "Error message"
}
```

| Code | Meaning |
|------|---------|
| 400 | Invalid format, corrupted image, missing fields |
| 401 | Invalid or missing API key |
| 413 | Image larger than 10MB |
| 422 | Could not download image from URL |
| 500 | Processing or storage error |

## Deployment (Railway & open-source)

The repo includes a **Procfile** and **railway.json** for one-click style deployment. For a step-by-step guide (env vars, Railway Storage bucket, health check, troubleshooting), see **[DEPLOYMENT.md](DEPLOYMENT.md)**.

## n8n usage

- Use **HTTP Request** in n8n.
- **Binary upload:** method POST, send body as multipart, add header `X-API-Key`.
- **URL:** method POST, JSON body `{"image_url": "..."}`, header `X-API-Key`.
- Use the `processed_url` from the JSON response as the final image URL.

## Contributing

Contributions are welcome. Open an issue or a pull request on GitHub.

## License

[MIT](LICENSE)
