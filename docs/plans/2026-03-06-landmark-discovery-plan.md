# Landmark Discovery — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a pre-Scout landmark discovery step that queries Google Places for a destination's most-reviewed attractions, then feeds this data through the entire pipeline to ensure iconic attractions are included.

**Architecture:** New `discover_landmarks()` method queries Google Places text search sorted by prominence. Results flow to Scout (must-consider), Reviewer (validate coverage), Planner (fix missing), Day Planner (must-include + text search in discovery). Duration fallbacks fixed for full-day venues.

**Tech Stack:** Python (Google Places API, Pydantic), Markdown prompts

---

### Task 1: Add discover_landmarks() to Places service

**Files:**
- Modify: `backend/app/services/google/places.py`

**Step 1:** Add method to `GooglePlacesService`:
```python
async def discover_landmarks(
    self, destination: str, max_results: int = 10
) -> list[PlaceCandidate]:
    """Discover a destination's most popular attractions by review count.

    Uses text search for "top attractions in {destination}" and sorts
    by user_ratings_total to surface iconic venues.
    """
    results = await self.text_search_places(
        query=f"top attractions and landmarks in {destination}",
        location=Location(lat=0, lng=0),  # No location bias — destination-wide
        max_results=max(max_results, 20),
    )
    # Sort by review count (prominence proxy)
    results.sort(key=lambda p: p.user_ratings_total or 0, reverse=True)
    return results[:max_results]
```

Wait — `text_search_places` requires a location for bias. For destination-wide search, we should use `text_search` (the raw dict version) instead, or geocode the destination first. Actually, `text_search_places` has `location` as required. Let's pass a dummy and rely on the query text for relevance. OR better: first geocode the destination, then search near that location.

**Revised approach:** The orchestrator already has the destination. We can geocode it first, then search nearby. But the orchestrator calls Scout before geocoding cities. So we need a lightweight geocode → search flow.

Simpler: use `text_search()` (the raw dict version at line 282) which doesn't require location:

```python
async def discover_landmarks(
    self, destination: str, max_results: int = 10
) -> list[dict]:
    """Discover a destination's most popular attractions by review count."""
    results = await self.text_search(
        query=f"top attractions and landmarks in {destination}",
        max_results=20,
    )
    # Sort by review count
    results.sort(key=lambda p: p.get("user_ratings_total") or 0, reverse=True)
    return results[:max_results]
```

This returns raw dicts with `name`, `rating`, `user_ratings_total`, `types`, `photo_reference`.

**Step 2:** Run tests: 199 passed
**Step 3:** Commit

---

### Task 2: Orchestrator calls discover_landmarks before Scout

**Files:**
- Modify: `backend/app/orchestrators/journey.py`

**Step 1:** Find `_scout_plan()` or wherever Scout is called. BEFORE the Scout call, add landmark discovery:

```python
# Discover destination's most popular attractions via Google
landmarks = []
try:
    landmarks = await self.places.discover_landmarks(request.destination)
    logger.info("[Orchestrator] Discovered %d landmarks for %s", len(landmarks), request.destination)
except Exception as exc:
    logger.warning("[Orchestrator] Landmark discovery failed: %s", exc)
```

**Step 2:** Format landmarks for the Scout prompt:
```python
landmarks_section = ""
if landmarks:
    lines = ["## DESTINATION'S MOST POPULAR ATTRACTIONS (from Google, by visitor reviews)",
             "You MUST consider including the top-ranked attractions in your highlights.",
             "If you exclude a top-5 attraction, explain why in why_visit.\n"]
    for i, lm in enumerate(landmarks):
        reviews = lm.get("user_ratings_total", 0)
        rating = lm.get("rating", 0)
        name = lm.get("name", "")
        lines.append(f"{i+1}. {name} ({rating}★, {reviews:,} reviews)")
    landmarks_section = "\n".join(lines)
```

**Step 3:** Pass `landmarks_section` to Scout agent. Update `scout.generate_plan()` to accept `landmarks_context: str = ""` parameter. Store landmarks for later stages.

**Step 4:** Pass same landmarks to Reviewer and Planner calls.

**Step 5:** Run tests, commit.

---

### Task 3: Scout prompt receives landmarks

**Files:**
- Modify: `backend/app/agents/scout.py`
- Modify: `backend/app/prompts/journey/scout_user.md`

**Step 1:** Update `generate_plan()` signature to accept `landmarks_context: str = ""`.
Pass to the user prompt: add `landmarks_context=landmarks_context` to `.format()` call.

**Step 2:** In `scout_user.md`, add placeholder before the JSON example:
```
{landmarks_context}
```

**Step 3:** Run tests, commit.

---

### Task 4: Reviewer receives + validates landmarks

**Files:**
- Modify: `backend/app/agents/reviewer.py`
- Modify: `backend/app/prompts/journey/reviewer_user.md`
- Modify: `backend/app/prompts/journey/reviewer_system.md`

**Step 1:** Update `review()` to accept `landmarks_context: str = ""`. Pass to user prompt.

**Step 2:** In `reviewer_user.md`, add after travel detail:
```
{landmarks_context}
```

**Step 3:** In `reviewer_system.md`, add new section after HIGHLIGHT & EXCURSION VALIDATION:
```
### 8. LANDMARK COVERAGE CHECK (does not contribute to score, but flag as issues)
- Compare the plan's highlights against the destination's top 5 most-reviewed attractions listed above
- If any top-5 attraction by review count is missing from ALL highlights across ALL cities, flag as a **major** issue with category `interest_alignment`
- The traveler expects to see a destination's signature attractions — omitting them requires justification
```

**Step 4:** Run tests, commit.

---

### Task 5: Planner receives landmarks

**Files:**
- Modify: `backend/app/agents/planner.py`
- Modify: `backend/app/prompts/journey/planner_user.md`

**Step 1:** Update `fix_plan()` to accept `landmarks_context: str = ""`. Pass to user prompt.

**Step 2:** In `planner_user.md`, add:
```
{landmarks_context}
```

Add to step-by-step process:
```
9. When fixing INTEREST ALIGNMENT: check if top-5 landmarks are missing and add them as highlights
```

**Step 3:** Run tests, commit.

---

### Task 6: Day Planner discovery includes landmark text search

**Files:**
- Modify: `backend/app/orchestrators/day_plan.py`

**Step 1:** After `_discover_highlights()` call, also search for landmark names from the journey highlights:

This is already partially done — `_discover_highlights()` searches for Scout highlight names. The missing piece is that if the Scout now includes landmarks (from Task 3), they'll automatically be searched here. No additional code needed IF Scout properly includes landmarks in highlights.

**Verify:** The existing `_discover_highlights()` flow text-searches for each `city.highlights[].name`. If Scout included "Universal Studios Singapore" as a highlight, it will be searched. No change needed.

**Step 2:** Run tests, commit (verify existing flow).

---

### Task 7: Day Planner selection enforces must-include

**Files:**
- Modify: `backend/app/prompts/day_plan/planning_user.md`

**Step 1:** Find `{scout_highlights_section}` placeholder. The section header says "SCOUT'S RECOMMENDED HIGHLIGHTS (prioritize including these)". Change to:
```
## MUST-INCLUDE ATTRACTIONS
These are the destination's signature attractions identified for this trip.
You MUST include each one in a day plan unless it's scheduled as a
full-day excursion on a separate day. Missing a must-include attraction
is a critical error.
```

**Step 2:** Run tests, commit.

---

### Task 8: Fix duration fallbacks for full-day venues

**Files:**
- Modify: `backend/app/config/planning.py`

**Step 1:** Update `_FALLBACK_DURATION_BY_TYPE`:
```python
"amusement_park": 480,   # was 180 — full-day parks need 8 hours
"zoo": 240,              # was 120 — zoos need 4 hours
"aquarium": 180,         # was 90 — aquariums need 3 hours
"theme_park": 480,       # add new entry
"water_park": 300,       # add new entry (5 hours)
```

**Step 2:** Run tests, commit.

---

### Task 9: Integration test with curl

**Step 1:** Plan Singapore 10-day trip, verify Universal Studios is in highlights
**Step 2:** Plan Japan 10-day trip, verify Mt Fuji area is mentioned
**Step 3:** Check landmark list appears in journey data
**Step 4:** Final commit

---

## Execution Notes
- Tasks 1-3: Core pipeline (sequential — each depends on previous)
- Tasks 4-5: Reviewer + Planner (independent of each other, depend on Task 2)
- Tasks 6-7: Day Planner (independent)
- Task 8: Config fix (independent)
- Task 9: Integration test (depends on all)

Can batch: [1,2,3] then [4,5,6,7,8] then [9]
