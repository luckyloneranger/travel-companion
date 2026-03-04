# Regular Everyday Traveller — Product Direction & Phase 1 Design

**Date:** 2026-03-04
**Status:** Approved

## Vision

Regular Everyday Traveller evolves from a solo AI trip planner into a **platform** for trip planning — starting with individual travelers, expanding to friend groups, and eventually serving travel agencies/advisors as a B2B tool.

## Current State

Functional MVP with:
- Multi-city AI journey planning (Scout → Enrich → Review → Planner loop)
- Per-day itineraries with TSP optimization, scheduling, and route computation
- Weather integration, smart transport mode selection (WALK/DRIVE/TRANSIT)
- Dark mode, responsive design, chat editing, tips, maps, copy-to-clipboard
- 135 backend tests, clean TypeScript, production build passing

Key gaps: no user accounts, no sharing, no exports, no budget tracking, no monetization.

## Product Roadmap

| Phase | Focus | Description |
|-------|-------|-------------|
| **1** | **Accounts & Sharing** | OAuth login, trip ownership, shareable links, PDF/calendar export |
| **2** | Budget & Cost Tracking | Per-leg/activity costs, trip budget, currency display, daily spend |
| **3** | Collaboration | Invite-to-edit links, real-time co-editing, activity voting, comments |
| **4** | Booking & Revenue | Affiliate links (Booking.com, Skyscanner), price comparison, "Book Now" CTAs |
| **5** | Mobile & Offline | PWA/React Native, Service Worker for offline, push notifications |
| **6** | B2B / Travel Advisors | White-label, client management, pricing tiers, advisor dashboard |

---

## Phase 1 Design: Accounts & Sharing

### 1. Authentication

**Approach:** Google/GitHub OAuth with JWT tokens (self-hosted, no third-party auth service).

**Flow:**
1. User clicks "Sign in with Google" (or GitHub) in Header
2. Frontend redirects to `GET /api/auth/login/google`
3. Backend initiates OAuth flow → Google consent screen
4. Google redirects to `GET /api/auth/callback/google` with auth code
5. Backend exchanges code for user info, creates/finds user, issues JWT
6. JWT set as httpOnly secure cookie + returned in response
7. Frontend stores auth state in `authStore` (Zustand)

**Backend:**
- `app/routers/auth.py` — `/login/{provider}`, `/callback/{provider}`, `/logout`, `/me`
- `app/models/user.py` — `User` pydantic model
- `app/db/models.py` — `User` SQLAlchemy model
- `app/core/auth.py` — JWT utils, `get_current_user` FastAPI dependency
- Library: `authlib` or `httpx-oauth` for OAuth flow

**Frontend:**
- `stores/authStore.ts` — user state, login/logout
- Auth button in Header (sign-in → avatar dropdown when logged in)
- Protected routes: trip CRUD requires auth; viewing shared trips doesn't

**Migration:** On first login, trips created in the current anonymous session (tracked via temporary session cookie) are assigned to the new user.

### 2. Data Model

```sql
-- New table
CREATE TABLE users (
    id TEXT PRIMARY KEY,              -- UUID
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    avatar_url TEXT,
    provider TEXT NOT NULL,           -- "google" | "github"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Modified table
ALTER TABLE trips ADD COLUMN user_id TEXT REFERENCES users(id);

-- New table
CREATE TABLE trip_shares (
    id TEXT PRIMARY KEY,              -- UUID
    trip_id TEXT NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    share_token TEXT UNIQUE NOT NULL,  -- 12-char alphanumeric
    access_level TEXT DEFAULT 'view', -- "view" | "edit" (edit for Phase 3)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3. Sharing

**Flow:**
1. Trip owner clicks "Share" in JourneyPreview
2. `POST /api/trips/{id}/share` → creates share_token, returns URL
3. URL format: `https://app.example.com/shared/{token}`
4. Anyone with URL can view the trip (no auth required)
5. Owner can revoke: `DELETE /api/trips/{id}/share`

**API endpoints:**
- `POST /api/trips/{id}/share` → `{ url, token }`
- `GET /api/shared/{token}` → full trip (read-only)
- `DELETE /api/trips/{id}/share` → revoke

**Frontend:**
- React Router (`react-router-dom`) for `/shared/{token}` route
- Share button with copy-link UI in JourneyPreview
- Read-only trip view (same components, no edit/chat buttons)

### 4. Exports

**PDF Export:**
- Endpoint: `GET /api/trips/{id}/export/pdf`
- Library: `weasyprint` (HTML template → PDF)
- Content: journey summary, cities, day schedule, weather, accommodation photos
- Frontend: "Download PDF" button

**Calendar Export (.ics):**
- Endpoint: `GET /api/trips/{id}/export/calendar`
- Library: `icalendar`
- Each activity → calendar event (title, start/end, location, notes)
- Travel legs → all-day events on travel days
- Frontend: "Add to Calendar" button

**UI:**
- "Share & Export" dropdown (shadcn/ui `DropdownMenu`) on JourneyPreview action bar
- Options: Share Link, Download PDF, Add to Calendar, Copy Text (existing)

### 5. Key Files to Create/Modify

**New files:**
- `backend/app/routers/auth.py`
- `backend/app/models/user.py`
- `backend/app/core/auth.py`
- `backend/app/routers/export.py`
- `frontend/src/stores/authStore.ts`
- `frontend/src/components/auth/AuthButton.tsx`
- `frontend/src/pages/SharedTrip.tsx`

**Modified files:**
- `backend/app/db/models.py` — add User table, user_id to Trip, TripShare table
- `backend/app/db/repository.py` — filter by user_id
- `backend/app/dependencies.py` — add auth dependencies
- `backend/app/main.py` — register auth + export routers
- `frontend/src/App.tsx` — add React Router
- `frontend/src/components/layout/Header.tsx` — auth button
- `frontend/src/components/trip/JourneyPreview.tsx` — Share & Export dropdown

### 6. Testing

- Auth flow tests (OAuth mock, JWT validation, protected routes)
- Share creation/revocation tests
- Export endpoint tests (PDF returns binary, .ics returns valid calendar)
- Frontend: shared trip view renders correctly without auth
