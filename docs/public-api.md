# Public API Reference (Week 3)

All public endpoints reside under `/api/v1/public` and do not require JWT authorization headers. Access control is managed strictly through magic-link access tokens or short-lived selfie search session tokens.

---

## Rate Limits (Decision D29)

Rate limiting uses a Redis sliding window algorithm keyed by IP address or access token:

| Endpoint | Method | Rate Limit | Key |
|---|---|---|---|
| `/public/events/{id}/search-selfie` | `POST` | 5 / min, 30 / hour | Client IP |
| `/public/guest/{code}` | `GET` | 60 / min, 600 / hour | Client IP |
| `/public/media/{photo_id}/{variant}` | `GET` | 300 / min | Access Token |
| `/public/photos/{photo_id}/download` | `GET` | 30 / min | Access Token |
| `/public/guest/{token}/zip` | `POST` | 5 / min | Access Token |

Exceeding any rate limit returns HTTP `429 Too Many Requests` with a `Retry-After: 60` header and JSON body `{"detail": "Rate limit exceeded. Please try again later."}`.

---

## Endpoints

### 1. `GET /api/v1/public/guest/{access_code}`
Validate access code and fetch guest portal overview.

- **URL Parameter:** `access_code` (22-character base64url magic token)
- **Response (200 OK):**
  ```json
  {
    "first_name": "Sarah",
    "event_title": "Annual Gala 2026",
    "event_date": "2026-08-20T18:00:00Z",
    "photo_count": 42
  }
  ```
- **Error Codes:**
  - `404 Not Found`: Token invalid or revoked (uniform timing, constant-time comparison).
  - `410 Gone`: Token expired.

---

### 2. `GET /api/v1/public/guest/{access_code}/photos`
Fetch paginated photos visible to the guest.

- **Query Parameters:**
  - `page` (default: `1`)
  - `limit` (default: `24`, max: `100`)
- **Response (200 OK):**
  ```json
  {
    "total": 42,
    "page": 1,
    "limit": 24,
    "total_pages": 2,
    "photos": [
      {
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "thumb_url": "/api/v1/public/media/3fa85f64-5717-4562-b3fc-2c963f66afa6/thumb?token=XYZ",
        "web_url": "/api/v1/public/media/3fa85f64-5717-4562-b3fc-2c963f66afa6/web?token=XYZ",
        "taken_at": "2026-08-20T19:15:30Z",
        "filename": "IMG_1042.JPG"
      }
    ]
  }
  ```

---

### 3. `GET /api/v1/public/media/{photo_id}/{variant}`
Stream image derivative bytes (no direct static file exposure).

- **URL Parameters:**
  - `photo_id` (UUID)
  - `variant`: `thumb` (400px) or `web` (1200px)
- **Query Parameters:**
  - `token` (magic token) OR `session` (selfie search session ID)
- **Headers:** Supports standard HTTP `ETag` and `If-None-Match` (returns `304 Not Modified` on cache hit).

---

### 4. `POST /api/v1/public/events/{event_id}/search-selfie`
Ephemeral selfie face search (D22–D24).

- **URL Parameter:** `event_id` (UUID)
- **Form Data:** `file` (JPEG, PNG, WEBP, or HEIC image; max 10 MB)
- **Response (200 OK):**
  ```json
  {
    "session_id": "sess_8f9a2b1c...",
    "total": 12,
    "photos": [...]
  }
  ```
- **Error Codes:**
  - `422 Unprocessable Entity`: Quality check failure (e.g., `NO_FACE_DETECTED`, `MULTIPLE_FACES_DETECTED`, `BLURRY_IMAGE`).

---

### 5. `GET /api/v1/public/photos/{photo_id}/download`
Stream full-resolution original photo.

- **Query Parameters:**
  - `token` OR `session`
- **Headers:** Supports `Range: bytes=start-end` for HTTP 206 chunked resume.

---

### 6. `POST /api/v1/public/guest/{token}/zip`
Request uncompressed ZIP archive (`ZIP_STORED`) of all visible photos.

- **Response (200 OK / 202 Accepted):**
  ```json
  {
    "job_id": "archive_uuid",
    "status": "completed",
    "photo_count": 42,
    "total_bytes": 184500120,
    "processed_photos": 42,
    "processed_bytes": 184500120,
    "download_url": "/api/v1/public/guest/{token}/zip/{archive_id}/download"
  }
  ```
- **Error Codes:**
  - `503 Service Unavailable`: Disk watermark above 80% (`Retry-After: 300`).
