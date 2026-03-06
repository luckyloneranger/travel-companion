# Plan: Prompt & Pipeline Robustness — 23 Opportunities

All fixes use LLM prompts + Google APIs. No hardcoding.

## Tasks

### Task 1: Seasonal awareness in Scout prompt
**File:** `backend/app/prompts/journey/scout_system.md`
Add to section 8 (SEASONAL AWARENESS): "Check if travel dates fall during monsoon, extreme heat, seasonal closures, or hurricane season for this region. If timing is poor, flag it explicitly and suggest alternative dates or destinations. Consider: Nepal monsoon (Jun-Sep), Iceland winter darkness (Nov-Feb), Caribbean hurricanes (Jun-Nov), SE Asia rainy season, African wildlife migration seasons."

### Task 2: Multi-country hard gate in Reviewer
**File:** `backend/app/prompts/journey/reviewer_system.md`
Update section 4 (CITY BALANCE): Add explicit rule: "If the destination is a multi-country region (continent, subcontinent like 'Europe', 'SE Asia', 'South America') and ALL cities are in the same country for trips of 7+ days, score this dimension 0 and set is_acceptable=false. This is a critical failure."

### Task 3: Family duration guidance in day planner
**File:** `backend/app/prompts/day_plan/planning_system.md`
Add new section after MEAL FLEXIBILITY: "## TRAVELER COMPOSITION ADJUSTMENTS\n- If the group includes **children**: add 20-30% buffer to activity durations (bathroom breaks, attention spans, slower pace). Prefer parks, interactive museums, and outdoor spaces over long gallery walks.\n- If the group includes **infants**: skip activities requiring stairs/hiking. Prefer ground-level, stroller-friendly venues.\n- If **senior travelers**: prefer accessible venues, shorter walking distances, seated dining over street food, morning activities over late nights."

### Task 4: Budget-aware place discovery
**File:** `backend/app/services/google/places.py`
In `_nearby_search()` and `text_search_places()`, add optional `price_levels` parameter. When provided, add `priceLevels` to the API request body to filter by price tier.
**File:** `backend/app/orchestrators/day_plan.py`
Pass budget tier to `discover_places()`: budget→[0,1], moderate→[1,2,3], luxury→[2,3,4].

### Task 5: Expand food interest types
**File:** `backend/app/config/planning.py`
Update `INTEREST_TO_TYPES["food"]` to add: `"market"`, `"food_court"`, `"meal_delivery"`. Also add `"cooking_class"` to `INTEREST_TO_TYPES["culture"]`.

### Task 6: Visa warning in Scout prompt
**File:** `backend/app/prompts/journey/scout_system.md`
Add new section after SAFETY & PRACTICALITY: "### 7c. VISA & ENTRY REQUIREMENTS\n- For multi-country routes, note visa requirements between each country pair\n- Flag if any destination requires advance visa (e.g., India, China, Russia, Brazil for many nationalities)\n- Note if border crossings require specific documents, fees, or advance booking\n- For Schengen area: note the 90/180 day limit for non-EU travelers\n- Add visa notes to travel_leg `notes` field"

### Task 7: Island transport constraint in Scout prompt
**File:** `backend/app/prompts/journey/scout_system.md`
Add to section 5 (TRANSPORT): "- For **island destinations** with no bridges or causeways, ONLY use ferry or flight between islands. Do NOT suggest driving.\n- For **remote islands** (Maldives atolls, small Greek islands), verify ferry/seaplane availability before suggesting the route\n- For **archipelago trips**, consider inter-island logistics carefully — not all islands have daily connections"

### Task 8: Dynamic discovery radius
**File:** `backend/app/services/google/places.py`
In `discover_places()`, after the initial search, if total results < 5, retry with expanded radius (15km). If still < 5, retry at 30km. Log the expansion.

### Task 9: Queue time buffer in day planner prompt
**File:** `backend/app/prompts/day_plan/planning_system.md`
Add to DURATION section or create new: "## QUEUE & ENTRANCE TIMES\n- Major museums and attractions in capital cities often have 20-60 min entrance queues. Add buffer time to your duration estimates.\n- Popular venues (Louvre, Vatican, Sagrada Familia, Taj Mahal) may need 30+ min queue time on top of visit time.\n- Consider suggesting early morning or late afternoon visits to avoid peak crowds."

### Task 10: Packed pace rest breaks in day planner prompt
**File:** `backend/app/prompts/day_plan/planning_system.md`
Add to MEAL FLEXIBILITY section: "- **Packed pace warning:** Even at packed pace, include at least one lighter activity (café, park rest, viewpoint) between every 2-3 intensive activities (museums, temples, tours). Burnout prevention is critical for enjoyable travel."

### Task 11: Solo traveler safety in Scout prompt
**File:** `backend/app/prompts/journey/scout_system.md`
Add to section 7 (SAFETY & PRACTICALITY): "- For **solo travelers**: prefer well-lit, tourist-friendly areas for evening activities. Avoid isolated neighborhoods at night.\n- For **solo female travelers**: note destinations with known harassment risks and suggest safer alternatives or precautions in `best_time_to_visit`\n- Always consider traveler composition when recommending nightlife or late-night activities"

### Task 12: Accommodation quality validation in Enricher
**File:** `backend/app/agents/enricher.py`
In `_enrich_accommodation()`, after finding a result, validate: if `result.rating < 3.5` or `result.user_ratings_total < 20`, log a warning and keep the LLM's original accommodation data instead of replacing with low-quality enrichment.

### Task 13: Chat edit budget awareness
**File:** `backend/app/prompts/chat/journey_edit_system.md`
Add: "When the user asks to add a city or change accommodation, consider the trip's budget tier. If the edit would significantly increase costs beyond the budget, warn the user and suggest alternatives."
**File:** `backend/app/services/chat.py`
Pass budget info to the chat prompt context.

### Task 14: Excursion day validation in Scout
**File:** `backend/app/agents/scout.py`
In `_validate_plan()`, add check: for each city, sum excursion days (full_day + multi_day). If total exceeds city.days, log warning and remove excess excursions.

### Task 15: Altitude/acclimatization in Scout prompt
**File:** `backend/app/prompts/journey/scout_system.md`
Add to SAFETY section: "- For destinations above **3,000m altitude** (e.g., Cusco, La Paz, Leh, Everest region), build in acclimatization rest days. Recommend 1 rest day per 1,000m gained above 3,000m.\n- Flag altitude risks in highlight descriptions"

### Task 16: Geocoding (0,0) validation
**File:** `backend/app/agents/enricher.py`
After geocoding, validate that coordinates are not (0,0): `if abs(lat) < 0.01 and abs(lng) < 0.01: treat as failed geocoding`.

### Task 17: Weather fallback for long trips
**File:** `backend/app/orchestrators/day_plan.py`
When weather API returns data for fewer days than the trip, log info message. Frontend already shows "Weather unavailable" text (implemented earlier).

### Task 18: Date line / timezone awareness
**File:** `backend/app/prompts/journey/scout_system.md`
Add to ROUTE section: "- When crossing time zones, account for jet lag recovery time (suggest lighter first-day schedules after long flights crossing 5+ time zones)\n- For date line crossings (Pacific routes), note the day gain/loss in travel leg notes"

### Task 19: Peak season pricing awareness
**File:** `backend/app/prompts/journey/scout_system.md`
Add to ACCOMMODATION section: "- Factor in seasonal pricing when estimating `estimated_nightly_usd`. Peak season (summer in Europe, Dec-Jan in tropical destinations) can be 50-100% more expensive than off-peak."

### Task 20: Currency context in Scout
**File:** `backend/app/prompts/journey/scout_user.md`
Add note: "Include local currency context in travel_leg notes where relevant (e.g., 'Japanese Yen trades ~150 to 1 USD'). Helps travelers prepare cash."

### Task 21: Religious/cultural etiquette in Tips
**File:** `backend/app/prompts/tips/tips_system.md`
Add: "Always include cultural etiquette notes: dress codes for religious sites, photography rules, tipping customs, greeting norms. Flag if the activity requires specific clothing (head covering, modest dress, shoe removal)."

### Task 22: Hidden costs awareness in day planner
**File:** `backend/app/prompts/day_plan/planning_user.md`
After cost estimation guidelines, add: "Note: Cost estimates should account for local taxes and service charges that tourists pay (e.g., 18% IVA in Peru, 10% service charge in Singapore, consumption tax in Japan)."

### Task 23: Validate geocoding != (0,0) before day planning
**File:** `backend/app/orchestrators/day_plan.py`
Before `discover_places()`, add check: if `city.location.lat` and `city.location.lng` are both near 0, skip with warning "Invalid coordinates for {city}".

## Verification
```bash
cd backend && ./venv/bin/python -m pytest -q --tb=short
cd frontend && npx tsc --noEmit && npm run build
```
