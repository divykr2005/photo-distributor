# Week 1 Testing Checklist

Run after `docker-compose up --build` OR with local dev servers running.

Set a shell variable for convenience:
```bash
API=http://localhost:8000/api/v1
```

---

## Happy Path

### Auth
```bash
# Register
curl -X POST $API/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice","email":"alice@test.com","password":"Test1234!"}'
# → 201 {id, name, email, created_at, updated_at}

# Login (form-encoded — FastAPI OAuth2 form)
curl -X POST $API/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'username=alice@test.com&password=Test1234!'
# → {access_token, refresh_token, token_type}
TOKEN=<access_token from above>

# Me
curl $API/auth/me -H "Authorization: Bearer $TOKEN"
# → {id, name, email}
```

### Events
```bash
# Create event
curl -X POST $API/events \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Wedding 2026","date":"2026-09-15T18:00:00Z","location":"Bangalore"}'
# → 201 {id, title, ...}
EVENT_ID=<id from above>

# List, get, update, delete
curl $API/events -H "Authorization: Bearer $TOKEN"
curl $API/events/$EVENT_ID -H "Authorization: Bearer $TOKEN"
curl -X PUT $API/events/$EVENT_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Wedding 2026 Updated"}'
```

### Guests
```bash
# Register guest (no photo)
curl -X POST $API/guests \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"event_id\":\"$EVENT_ID\",\"first_name\":\"Bob\",\"last_name\":\"Smith\",\"phone\":\"+919876543210\"}"
GUEST_ID=<id from above>

# Upload face photo (webcam capture or any JPEG)
curl -X POST $API/guests/$GUEST_ID/photo \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/face.jpg"
# → GuestResponse with embedding_status="success" (or 422 with reason if quality fails)

# List with pagination + search
curl "$API/guests?page=1&page_size=10" -H "Authorization: Bearer $TOKEN"
curl "$API/guests?search=Bob&event_id=$EVENT_ID" -H "Authorization: Bearer $TOKEN"

# Profile
curl $API/guests/$GUEST_ID -H "Authorization: Bearer $TOKEN"

# Dashboard stats
curl $API/dashboard/stats -H "Authorization: Bearer $TOKEN"
# → {total_events: 1, total_guests: 1, registered_today: 1}
```

---

## Negative / Edge Cases

### Auth
```bash
# Duplicate email → 400
curl -X POST $API/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice2","email":"alice@test.com","password":"Test1234!"}'
# → 400 "Email already registered"

# Wrong password → 401
curl -X POST $API/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'username=alice@test.com&password=wrong'
# → 401

# Rate limit: hit login 6 times quickly → 429 on 6th
for i in {1..6}; do
  curl -X POST $API/auth/login \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d 'username=alice@test.com&password=wrong'
done

# No token → 401
curl $API/auth/me
# → 401

# Expired/bad token → 401
curl $API/auth/me -H "Authorization: Bearer faketoken"
# → 401
```

### Guests / Embedding Quality Gates
```bash
# No face in photo → 422 "No face detected..."
curl -X POST $API/guests/$GUEST_ID/photo \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/landscape.jpg"

# Blurry photo → 422 "Image is too blurry..."
# Dark photo   → 422 "Image is too dark..."
# Two people   → 422 "2 faces detected..."
# All return specific, actionable messages — not generic errors.

# Wrong file type → 400
curl -X POST $API/guests/$GUEST_ID/photo \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.pdf"
# → 400 "Only JPEG, PNG, or WebP"

# File > 5 MB → 400
# (create a >5MB file and upload it)
```

### Security
```bash
# Embedding never appears in any API response
curl $API/guests/$GUEST_ID -H "Authorization: Bearer $TOKEN" | grep embedding
# → should only show "embedding_status", never the 512-dim vector

# Protected route with no token
curl $API/events
# → 401

# Access another user's event
# (register a second account, try to GET/PUT/DELETE first user's event ID → 404)
```

### Delete cascade
```bash
# Delete guest → face_embeddings row cascades (check DB directly)
curl -X DELETE $API/guests/$GUEST_ID -H "Authorization: Bearer $TOKEN"
# → 204; row gone from guests AND face_embeddings

# Delete event → guests cascade too
curl -X DELETE $API/events/$EVENT_ID -H "Authorization: Bearer $TOKEN"
# → 204; all child guests and their embeddings gone
```

---

## UI Smoke Test (browser)

1. Open `http://localhost:3000`
2. Register → lands on `/dashboard`
3. Stat cards show 0/0/0
4. Create event → stat updates to 1
5. Register guest → complete form, capture/upload photo
   - If quality fails: red toast with reason, stay on page
   - If succeeds: redirect to `/guests`, status badge = `success`
6. `/guests` — search by name, filter by event, paginate (if > 20)
7. Click guest name → profile page with photo, status badge, details
8. Hover photo → upload icon appears, click to retake
9. Dashboard quick-action cards: "Register Guest" and "View All" both navigate correctly
10. Log out and access `/dashboard` → redirect to `/login`
