# Phase 1: Accounts, Sharing & Exports — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add user authentication (Google/GitHub OAuth), trip ownership, shareable read-only trip links, and export capabilities (PDF, calendar .ics).

**Architecture:** OAuth login via `authlib` on the backend, JWT access tokens as httpOnly cookies. New `users` and `trip_shares` SQLAlchemy tables. React Router for shared trip pages. PDF export via `weasyprint`, calendar via `icalendar`.

**Tech Stack:** authlib, PyJWT, weasyprint, icalendar (backend). react-router-dom (frontend).

---

### Task 1: Install Backend Dependencies

**Files:**
- Modify: `backend/requirements.txt`

**Step 1: Add new dependencies**

Add to `backend/requirements.txt`:
```
# Auth
authlib>=1.3.0
PyJWT>=2.8.0
itsdangerous>=2.1.0

# Export
weasyprint>=62.0
icalendar>=5.0.0
```

**Step 2: Install**

Run: `cd backend && source venv/bin/activate && pip install authlib PyJWT itsdangerous weasyprint icalendar`

**Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add auth and export dependencies"
```

---

### Task 2: Add Settings for OAuth & JWT

**Files:**
- Modify: `backend/app/config/settings.py`
- Modify: `backend/.env.example`
- Modify: `backend/.env`

**Step 1: Add settings fields**

Add to `Settings` class in `settings.py`:
```python
# OAuth
google_oauth_client_id: str = ""
google_oauth_client_secret: str = ""
github_oauth_client_id: str = ""
github_oauth_client_secret: str = ""

# JWT
jwt_secret_key: str = "change-me-in-production"
jwt_algorithm: str = "HS256"
jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

# App
app_url: str = "http://localhost:5173"
```

**Step 2: Update .env.example**

Add the corresponding env vars with placeholder values.

**Step 3: Commit**

```bash
git add backend/app/config/settings.py backend/.env.example
git commit -m "feat: add OAuth and JWT settings"
```

---

### Task 3: Create User Database Model

**Files:**
- Modify: `backend/app/db/models.py`
- Create: `backend/app/models/user.py`

**Step 1: Write tests for User model**

Create `backend/tests/test_auth.py`:
```python
from app.models.user import UserResponse

def test_user_response_model():
    user = UserResponse(id="u1", email="a@b.com", name="Test", avatar_url=None, provider="google")
    assert user.email == "a@b.com"
```

Run: `pytest tests/test_auth.py -v` → should FAIL (module not found)

**Step 2: Create Pydantic model**

Create `backend/app/models/user.py`:
```python
from datetime import datetime
from pydantic import BaseModel

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    avatar_url: str | None = None
    provider: str
```

**Step 3: Add SQLAlchemy models**

Add to `backend/app/db/models.py`:
```python
class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    provider = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())

class TripShare(Base):
    __tablename__ = "trip_shares"
    id = Column(String, primary_key=True)
    trip_id = Column(String, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    share_token = Column(String, unique=True, nullable=False)
    access_level = Column(String, default="view")
    created_at = Column(DateTime, default=func.now())
```

Add `user_id` column to existing `Trip` model:
```python
user_id = Column(String, ForeignKey("users.id"), nullable=True)
```

**Step 4: Run test** → PASS

**Step 5: Commit**

```bash
git add backend/app/db/models.py backend/app/models/user.py backend/tests/test_auth.py
git commit -m "feat: add User and TripShare database models"
```

---

### Task 4: Create JWT Utilities

**Files:**
- Create: `backend/app/core/auth.py`
- Modify: `backend/tests/test_auth.py`

**Step 1: Write tests**

Add to `tests/test_auth.py`:
```python
from app.core.auth import create_access_token, decode_access_token

def test_jwt_roundtrip():
    token = create_access_token({"sub": "user-123", "email": "a@b.com"})
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"

def test_jwt_invalid_token():
    payload = decode_access_token("invalid-token")
    assert payload is None
```

Run: `pytest tests/test_auth.py -v` → FAIL

**Step 2: Implement JWT utils**

Create `backend/app/core/auth.py`:
```python
from datetime import datetime, timedelta, timezone
import jwt
from app.config import get_settings

def create_access_token(data: dict) -> str:
    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {**data, "exp": expires}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def decode_access_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
```

**Step 3: Run tests** → PASS

**Step 4: Commit**

```bash
git add backend/app/core/auth.py backend/tests/test_auth.py
git commit -m "feat: add JWT token creation and validation"
```

---

### Task 5: Create Auth Router (OAuth Endpoints)

**Files:**
- Create: `backend/app/routers/auth.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/dependencies.py`
- Modify: `backend/tests/test_auth.py`

**Step 1: Create auth router**

Create `backend/app/routers/auth.py` with:
- `GET /api/auth/login/{provider}` — redirects to OAuth consent screen
- `GET /api/auth/callback/{provider}` — handles OAuth callback, creates/finds user, sets JWT cookie
- `POST /api/auth/logout` — clears JWT cookie
- `GET /api/auth/me` — returns current user from JWT

**Step 2: Add get_current_user dependency**

In `dependencies.py`, add:
```python
from fastapi import Request, HTTPException
from app.core.auth import decode_access_token

async def get_current_user(request: Request) -> dict | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_access_token(token)
    return payload

async def require_user(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(401, "Not authenticated")
    return user
```

**Step 3: Register router in main.py**

Add `from app.routers import auth` and `application.include_router(auth.router)`.

**Step 4: Add tests for /me and /logout**

**Step 5: Commit**

```bash
git add backend/app/routers/auth.py backend/app/main.py backend/app/dependencies.py backend/tests/test_auth.py
git commit -m "feat: add OAuth auth router with login, callback, logout, me"
```

---

### Task 6: Add User Ownership to Trips

**Files:**
- Modify: `backend/app/routers/trips.py`
- Modify: `backend/app/db/repository.py`
- Modify: `backend/tests/test_api.py`

**Step 1: Update repository**

- `list_trips(user_id=None)` — filter by user_id when provided
- `save_trip(request, journey, trip_id, user_id)` — store user_id
- Add ownership check in `get_trip`, `delete_trip`

**Step 2: Update trip router**

- Inject `user = Depends(get_current_user)` (optional, not required — allows anonymous browsing)
- Pass `user["sub"]` to repository methods when user is authenticated
- `list_trips` returns only the user's trips when logged in

**Step 3: Add tests for ownership filtering**

**Step 4: Commit**

```bash
git add backend/app/routers/trips.py backend/app/db/repository.py backend/tests/test_api.py
git commit -m "feat: add user ownership to trips"
```

---

### Task 7: Implement Trip Sharing

**Files:**
- Modify: `backend/app/routers/trips.py`
- Modify: `backend/app/db/repository.py`
- Create: `backend/tests/test_sharing.py`

**Step 1: Add sharing endpoints to trips router**

- `POST /api/trips/{id}/share` — generates share token, returns URL
- `GET /api/shared/{token}` — returns trip data (no auth required)
- `DELETE /api/trips/{id}/share` — revokes sharing

**Step 2: Add repository methods**

- `create_share(trip_id) -> str` — generates 12-char token, inserts TripShare, returns token
- `get_trip_by_share_token(token) -> TripResponse | None`
- `delete_share(trip_id)`

**Step 3: Write tests**

Test sharing creation, retrieval, revocation, and 404 for invalid tokens.

**Step 4: Commit**

```bash
git add backend/app/routers/trips.py backend/app/db/repository.py backend/tests/test_sharing.py
git commit -m "feat: add trip sharing with unique tokens"
```

---

### Task 8: Implement PDF Export

**Files:**
- Create: `backend/app/routers/export.py`
- Create: `backend/app/services/export.py`
- Create: `backend/tests/test_export.py`

**Step 1: Create export service**

`backend/app/services/export.py`:
- `generate_pdf(trip: TripResponse) -> bytes` — renders HTML template → PDF via weasyprint
- HTML template includes: journey theme, summary, cities, day-by-day schedule, weather, accommodation

**Step 2: Create export router**

`backend/app/routers/export.py`:
- `GET /api/trips/{id}/export/pdf` — returns PDF bytes with `application/pdf` content type
- `GET /api/trips/{id}/export/calendar` — returns .ics file

**Step 3: Register in main.py**

**Step 4: Write tests** (PDF returns 200 with correct content-type, .ics returns valid text)

**Step 5: Commit**

```bash
git add backend/app/routers/export.py backend/app/services/export.py backend/tests/test_export.py backend/app/main.py
git commit -m "feat: add PDF and calendar export endpoints"
```

---

### Task 9: Implement Calendar Export (.ics)

**Files:**
- Modify: `backend/app/services/export.py`
- Modify: `backend/tests/test_export.py`

**Step 1: Add calendar generation**

Add to `export.py`:
- `generate_ics(trip: TripResponse) -> str` — uses `icalendar` library
- Each activity → VEVENT with DTSTART, DTEND, SUMMARY (place name), LOCATION (address), DESCRIPTION (notes + weather)
- Travel legs → all-day events

**Step 2: Wire into export router (already created in Task 8)**

**Step 3: Write tests** (valid .ics content, correct event count)

**Step 4: Commit**

```bash
git add backend/app/services/export.py backend/tests/test_export.py
git commit -m "feat: add calendar (.ics) export"
```

---

### Task 10: Install Frontend Dependencies

**Files:**
- Modify: `frontend/package.json`

**Step 1: Install react-router-dom**

Run: `cd frontend && npm install react-router-dom`

**Step 2: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: add react-router-dom"
```

---

### Task 11: Add Frontend Auth Store & Types

**Files:**
- Create: `frontend/src/stores/authStore.ts`
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/services/api.ts`

**Step 1: Add User type**

Add to `types/index.ts`:
```typescript
export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
  provider: string;
}
```

**Step 2: Create auth store**

`stores/authStore.ts`:
```typescript
interface AuthState {
  user: User | null;
  isLoading: boolean;
  fetchUser: () => Promise<void>;
  logout: () => Promise<void>;
}
```

**Step 3: Add API methods**

Add to `api.ts`:
- `getMe()` — `GET /api/auth/me`
- `logout()` — `POST /api/auth/logout`
- `shareTip(tripId)` — `POST /api/trips/{id}/share`
- `getSharedTrip(token)` — `GET /api/shared/{token}`
- `exportPdf(tripId)` — `GET /api/trips/{id}/export/pdf` (blob download)
- `exportCalendar(tripId)` — `GET /api/trips/{id}/export/calendar` (file download)

**Step 4: Commit**

```bash
git add frontend/src/stores/authStore.ts frontend/src/types/index.ts frontend/src/services/api.ts
git commit -m "feat: add auth store, user types, and API methods"
```

---

### Task 12: Add Auth UI (Header + Login)

**Files:**
- Modify: `frontend/src/components/layout/Header.tsx`
- Create: `frontend/src/components/auth/AuthButton.tsx`

**Step 1: Create AuthButton component**

Shows "Sign In" when logged out, avatar dropdown (with name + logout) when logged in. Login links to `/api/auth/login/google`.

**Step 2: Add to Header**

Replace/augment the dark mode toggle area with AuthButton.

**Step 3: Commit**

```bash
git add frontend/src/components/auth/AuthButton.tsx frontend/src/components/layout/Header.tsx
git commit -m "feat: add auth button to header"
```

---

### Task 13: Add React Router & Shared Trip Page

**Files:**
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/pages/SharedTrip.tsx`

**Step 1: Wrap App in BrowserRouter**

Update `main.tsx` to use `BrowserRouter` from `react-router-dom`.

**Step 2: Add routes**

In `App.tsx`, add:
- `/` — existing trip planning UI
- `/shared/:token` — read-only shared trip view
- `/auth/callback` — OAuth callback handler

**Step 3: Create SharedTrip page**

`pages/SharedTrip.tsx`:
- Fetches trip via `api.getSharedTrip(token)`
- Renders JourneyPreview + DayCards in read-only mode (no edit/chat/new-trip buttons)

**Step 4: Commit**

```bash
git add frontend/src/main.tsx frontend/src/App.tsx frontend/src/pages/SharedTrip.tsx
git commit -m "feat: add React Router with shared trip page"
```

---

### Task 14: Add Share & Export Dropdown

**Files:**
- Modify: `frontend/src/components/trip/JourneyPreview.tsx`

**Step 1: Replace individual buttons with dropdown**

Replace the "Copy" + "New Trip" buttons with a "Share & Export" dropdown menu (shadcn/ui `DropdownMenu`):
- Share Link (generates + copies)
- Download PDF
- Add to Calendar
- Copy as Text (existing)

**Step 2: Implement handlers**

- Share: calls `api.shareTrip()`, copies URL to clipboard
- PDF: calls `api.exportPdf()`, triggers browser download
- Calendar: calls `api.exportCalendar()`, triggers .ics download

**Step 3: Commit**

```bash
git add frontend/src/components/trip/JourneyPreview.tsx
git commit -m "feat: add Share & Export dropdown menu"
```

---

### Task 15: Final Verification & Cleanup

**Step 1: Run all backend tests**

```bash
cd backend && source venv/bin/activate && pytest -v
```

**Step 2: TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

**Step 3: Production build**

```bash
cd frontend && npm run build
```

**Step 4: Manual test flow**

1. Start backend: `uvicorn app.main:app --reload --port 8000`
2. Start frontend: `npm run dev`
3. Test: login with Google/GitHub, create trip, share link, open shared link, export PDF, export calendar

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat: Phase 1 complete — accounts, sharing, and exports"
```
