# UX Improvements Backlog

_Generated: March 5, 2026_

## Critical (Fix Now)

### 1. Day plans hidden behind collapsed accordions
City cards default to collapsed — users might not realize day plans were generated. No "Expand All" button.
- **Fix:** Expand the first city by default, add expand/collapse all toggle.
- **Files:** `CompactCityCard.tsx`, `JourneyDashboard.tsx`

### 2. Empty states missing everywhere
No day plans yet? No saved trips? No search results? The UI shows nothing. No guidance, no CTA.
- **Fix:** Add empty state illustrations/messages with CTAs for: no saved trips, no day plans, no search results, first-time user.
- **Files:** `WizardForm.tsx`, `JourneyDashboard.tsx`, `DayTimeline.tsx`

### 3. Error messages are all generic
"Failed to load trip. Please try again." — no retry button, no context. Network/auth/validation errors all look the same.
- **Fix:** Distinguish error types, add retry buttons, show contextual recovery suggestions.
- **Files:** `App.tsx`, `tripStore.ts`, `ChatPanel.tsx`

### 4. Mobile touch targets too small
Counter buttons (adults/children) are 32×32px — below the 44px minimum for touch.
- **Fix:** Increase to h-10 w-10 or use numeric input fields.
- **Files:** `WizardStepWhen.tsx`, `WizardStepper.tsx`

---

## High Impact (Next Sprint)

### 5. Planning wait lacks engagement
Activity log shows checkmarks but repeats messages. No ETA. No indication if the LLM is retrying.
- **Fix:** Group repeated messages, add ETA estimate, show retry indicator when score <70.
- **Files:** `PlanningDashboard.tsx`

### 6. Results require excessive scrolling
Header → map → city cards → budget = 3+ screen heights. No tabs, no sticky nav.
- **Fix:** Add tabs (Overview | Cities | Budget | Map) or sticky city filter.
- **Files:** `JourneyDashboard.tsx`

### 7. Chat suggestions disappear after first message
Suggestion chips vanish once you send. No preview of AI changes.
- **Fix:** Keep suggestions visible, show diff preview before applying changes.
- **Files:** `ChatPanel.tsx`

### 8. Wizard state not persisted
All form state is useState — refresh mid-wizard and everything is lost.
- **Fix:** Save wizard state to sessionStorage, restore on mount.
- **Files:** `WizardForm.tsx`

### 9. No "Expand All" for city cards
Each city must be expanded individually. With 5 cities = 5 clicks.
- **Fix:** Add "Expand All / Collapse All" toggle in JourneyDashboard.
- **Files:** `JourneyDashboard.tsx`, `CompactCityCard.tsx`

---

## Medium (Polish)

### 10. Maps are decorative
Clicking a city marker doesn't zoom into day plans. No legends.
- **Fix:** Add click handlers, legend, zoom-to-city interaction.
- **Files:** `TripMap.tsx`, `DayMap.tsx`

### 11. No onboarding for first-time users
Users land on a blank form. Templates are below the fold.
- **Fix:** Add hero section, example trip preview, or "See how it works" walkthrough.
- **Files:** `WizardForm.tsx`, `WizardStepWhere.tsx`

### 12. Accessibility gaps
Missing ARIA labels on counter buttons, chat input, timeline routes. Modal doesn't trap focus.
- **Files:** `WizardStepWhen.tsx`, `ChatPanel.tsx`, `DayTimeline.tsx`, `SignIn.tsx`

### 13. Delete trip uses double-click pattern
Unusual — most users expect a modal confirmation.
- **Fix:** Add confirmation dialog or at minimum a toast with undo.
- **Files:** `WizardForm.tsx`

### 14. Budget summary $0 categories
Visually awkward empty cells in the grid.
- **Fix:** Hide zero-value categories or show "—".
- **Files:** `BudgetSummary.tsx`

### 15. Share URL feedback is fleeting
"Shared!" text shows briefly, easy to miss.
- **Fix:** Add toast notification or persistent share URL display.
- **Files:** `JourneyDashboard.tsx`
