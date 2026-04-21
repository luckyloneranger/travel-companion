# UX Visual Overhaul — 12 Improvements in 8 Tasks

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the app from a generic Tailwind+shadcn template into a visually distinctive travel experience that evokes wanderlust and delight.

**Architecture:** All changes are frontend-only (React, TypeScript, Tailwind CSS v4). No backend changes. Focused on CSS animations, component restructuring, and visual enhancements. No new dependencies — leverage existing Tailwind v4 + lucide-react + tw-animate-css.

**Tech Stack:** React 19, TypeScript 5.8, Tailwind CSS v4, shadcn/ui, lucide-react

---

## Execution Order

| Order | Task | Files | Improvements | Complexity |
|-------|------|-------|--------------|------------|
| 1 | CSS Foundation | index.css | #4 stagger, #11 scroll-reveal, #7 wizard transitions, #12 dark mode | Medium |
| 2 | Photo-First Cards | DayTimeline.tsx | #2 photo-first activity cards, #8 skeleton loaders | Medium |
| 3 | Weather Atmosphere | DayTimeline.tsx, CompactCityCard.tsx | #5 weather-driven day gradients | Small |
| 4 | Hero Destination | JourneyDashboard.tsx | #1 destination hero imagery | Medium |
| 5 | Planning Animation | PlanningDashboard.tsx | #3 immersive planning experience | Medium |
| 6 | Wizard Transitions | WizardForm.tsx, index.css | #7 wizard step slide transitions | Small |
| 7 | Budget & Celebration | BudgetSummary.tsx, JourneyDashboard.tsx | #6 budget visualization, #9 confetti celebration | Medium |
| 8 | Mobile & Navigation | FullDayView.tsx, NavigationSidebar.tsx | #10 swipe navigation, #11 scroll reveal | Small |

Each task: implement → `npm run build` → commit.

---

### Task 1: CSS Animation Foundation (#4, #11, #12)

Add staggered entry keyframes, scroll-reveal utility class, wizard slide transitions, and intentional dark mode improvements to the CSS foundation.

**Files:**
- Modify: `frontend/src/index.css`

**Step 1: Add staggered fade-in keyframes and scroll-reveal**

After the existing `celebration-glow` animation (line 207), add:

```css
/* Staggered entry — use with animation-delay utilities */
@keyframes fade-in-up-stagger {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-stagger-in {
  animation: fade-in-up-stagger 0.4s ease-out both;
}

.stagger-1 { animation-delay: 0ms; }
.stagger-2 { animation-delay: 80ms; }
.stagger-3 { animation-delay: 160ms; }
.stagger-4 { animation-delay: 240ms; }
.stagger-5 { animation-delay: 320ms; }
.stagger-6 { animation-delay: 400ms; }
.stagger-7 { animation-delay: 480ms; }
.stagger-8 { animation-delay: 560ms; }

/* Scroll-triggered reveal — elements start invisible, JS adds .revealed */
.scroll-reveal {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.5s ease-out, transform 0.5s ease-out;
}
.scroll-reveal.revealed {
  opacity: 1;
  transform: translateY(0);
}

/* Wizard step slide transitions */
@keyframes slide-in-right {
  from { opacity: 0; transform: translateX(30px); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes slide-in-left {
  from { opacity: 0; transform: translateX(-30px); }
  to { opacity: 1; transform: translateX(0); }
}
.animate-slide-right { animation: slide-in-right 0.3s ease-out; }
.animate-slide-left { animation: slide-in-left 0.3s ease-out; }

/* Confetti keyframes */
@keyframes confetti-fall {
  0% { transform: translateY(-100%) rotate(0deg); opacity: 1; }
  100% { transform: translateY(100vh) rotate(720deg); opacity: 0; }
}

/* Photo shimmer loading placeholder */
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
.animate-shimmer {
  background: linear-gradient(90deg, var(--theme-surface-muted) 25%, var(--theme-surface) 50%, var(--theme-surface-muted) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

/* Swipe hint pulse */
@keyframes swipe-hint {
  0%, 100% { transform: translateX(0); }
  50% { transform: translateX(8px); }
}
.animate-swipe-hint {
  animation: swipe-hint 1.5s ease-in-out 2;
}
```

**Step 2: Enhance dark mode with intentional travel-themed colors**

Update the `.dark` section (line 128) — replace the flat dark surface with deep navy tones:

```css
.dark {
  --theme-surface: #0f1219;
  --theme-surface-dim: #0a0d14;
  --theme-surface-muted: #1a1f2e;
  --theme-border-default: #2a3245;
  --theme-text-primary: #e8ecf4;
  --theme-text-secondary: #b8c4d8;
  --theme-text-muted: #6b7a94;
  /* ... keep all oklch values unchanged ... */
}
```

**Step 3: Build and commit**

```bash
cd frontend && npm run build
```

Commit: `feat(css): animation foundation — stagger, scroll-reveal, slide transitions, dark mode`

---

### Task 2: Photo-First Activity Cards + Skeleton Loaders (#2, #8)

Restructure DayTimeline activity cards to make photos the visual hero, and add content-shaped skeleton loaders.

**Files:**
- Modify: `frontend/src/components/trip/DayTimeline.tsx`

**Step 1: Add ImageWithShimmer component**

After the imports (around line 22), add a reusable image loader:

```tsx
function ImageWithShimmer({ src, alt, className }: { src: string; alt: string; className?: string }) {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);

  if (error) return null;

  return (
    <div className={`relative overflow-hidden ${className ?? ''}`}>
      {!loaded && <div className="absolute inset-0 animate-shimmer rounded-md" />}
      <img
        src={src}
        alt={alt}
        loading="lazy"
        onLoad={() => setLoaded(true)}
        onError={() => setError(true)}
        className={`h-full w-full object-cover transition-opacity duration-300 ${loaded ? 'opacity-100' : 'opacity-0'}`}
      />
    </div>
  );
}
```

**Step 2: Redesign activity card photo layout**

In the `TimelineActivity` component, replace the photo section (around lines 260-277) with a photo-first layout. The new design puts photos as a prominent banner at the top of the card:

Replace the existing photo rendering block:
```tsx
{activity.place.photo_urls && activity.place.photo_urls.length > 0 && (
  <div className="flex gap-1.5 overflow-x-auto -mx-1 px-1 items-center">
    {activity.place.photo_urls.slice(0, 2).map((url, i) => (
      <img
        key={i}
        src={`${photoUrl(url)}${url.includes('?') ? '&' : '?'}w=400`}
        alt={`${activity.place.name} photo ${i + 1}`}
        loading="lazy"
        onClick={() => onPhotoClick?.(`${photoUrl(url)}${url.includes('?') ? '&' : '?'}w=800`)}
        className="h-16 w-24 max-w-[30vw] sm:h-24 sm:w-32 sm:max-w-none rounded-md object-cover shrink-0 cursor-pointer hover:opacity-90 transition-opacity"
        onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
      />
    ))}
    {activity.place.photo_urls.length > 2 && (
      <span className="text-xs text-text-muted">+{activity.place.photo_urls.length - 2} more</span>
    )}
  </div>
)}
```

With the new photo-hero layout:
```tsx
{activity.place.photo_urls && activity.place.photo_urls.length > 0 && (
  <div className="-mx-3 -mt-3 mb-2">
    <div className="relative group">
      <ImageWithShimmer
        src={`${photoUrl(activity.place.photo_urls[0])}${activity.place.photo_urls[0].includes('?') ? '&' : '?'}w=600`}
        alt={activity.place.name}
        className="h-32 sm:h-40 w-full rounded-t-lg cursor-pointer"
      />
      <div
        className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent rounded-t-lg opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
        onClick={() => onPhotoClick?.(`${photoUrl(activity.place.photo_urls![0])}${activity.place.photo_urls![0].includes('?') ? '&' : '?'}w=800`)}
      />
      {activity.place.photo_urls.length > 1 && (
        <div className="absolute bottom-2 right-2 flex gap-1">
          {activity.place.photo_urls.slice(1, 3).map((url, i) => (
            <ImageWithShimmer
              key={i}
              src={`${photoUrl(url)}${url.includes('?') ? '&' : '?'}w=200`}
              alt={`${activity.place.name} photo ${i + 2}`}
              className="h-10 w-14 rounded border-2 border-white/80 shadow-sm cursor-pointer"
            />
          ))}
          {activity.place.photo_urls.length > 3 && (
            <span className="flex items-center justify-center h-10 w-14 rounded border-2 border-white/80 bg-black/50 text-white text-xs font-medium shadow-sm">
              +{activity.place.photo_urls.length - 3}
            </span>
          )}
        </div>
      )}
    </div>
  </div>
)}
```

**Step 3: Add stagger classes to activity list rendering**

In `renderActivityList()` (around line 522), wrap each activity with a stagger class:

In the `return` for onReorder case and the non-reorder case, add stagger classes. Modify both returns to include `className`:

For the non-reorder case (around line 560):
```tsx
return (
  <div key={activity.id} className={`animate-stagger-in stagger-${Math.min(i + 1, 8)}`}>
    {activityElement}
  </div>
);
```

**Step 4: Build and commit**

```bash
cd frontend && npm run build
```

Commit: `feat(timeline): photo-first activity cards with shimmer loading and stagger animation`

---

### Task 3: Weather-Driven Day Atmosphere (#5)

Set the DayTimeline container background based on weather conditions, creating a visual mood for each day.

**Files:**
- Modify: `frontend/src/components/trip/DayTimeline.tsx`
- Modify: `frontend/src/components/trip/CompactCityCard.tsx`

**Step 1: Add weather atmosphere helper in DayTimeline.tsx**

After the `getCategoryColor` function (around line 52), add:

```tsx
function getWeatherAtmosphere(condition?: string): string {
  if (!condition) return '';
  const c = condition.toLowerCase();
  if (c.includes('rain') || c.includes('shower'))
    return 'bg-gradient-to-b from-blue-50/50 to-slate-50/30 dark:from-blue-950/20 dark:to-slate-950/10';
  if (c.includes('cloud') || c.includes('overcast'))
    return 'bg-gradient-to-b from-gray-50/50 to-slate-50/30 dark:from-gray-950/20 dark:to-slate-950/10';
  if (c.includes('snow'))
    return 'bg-gradient-to-b from-sky-50/40 to-white/30 dark:from-sky-950/20 dark:to-slate-950/10';
  if (c.includes('thunder') || c.includes('storm'))
    return 'bg-gradient-to-b from-slate-100/50 to-purple-50/20 dark:from-slate-950/30 dark:to-purple-950/10';
  // Sunny / clear / partly cloudy
  return 'bg-gradient-to-b from-amber-50/30 to-orange-50/10 dark:from-amber-950/10 dark:to-orange-950/5';
}
```

**Step 2: Apply atmosphere to the main container**

In the `DayTimeline` return (around line 567), wrap the `<div className="space-y-0">` with the weather atmosphere:

```tsx
return (
  <div className={`space-y-0 rounded-lg px-1 py-1 ${getWeatherAtmosphere(dayPlan.weather?.condition)}`}>
```

**Step 3: Add subtle weather indicator in CompactCityCard day header**

In CompactCityCard.tsx, in the day header section (around line 297-303), after the day number badge and theme text, add a weather emoji indicator:

After `· {dp.theme}`, add:
```tsx
{dp.weather && (
  <span className="text-xs text-text-muted ml-1">
    {dp.weather.temperature_high_c.toFixed(0)}°
  </span>
)}
```

**Step 4: Build and commit**

```bash
cd frontend && npm run build
```

Commit: `feat(weather): weather-driven day atmosphere gradients`

---

### Task 4: Destination Hero Imagery (#1)

Add a hero destination photo banner behind the journey theme in JourneyDashboard.

**Files:**
- Modify: `frontend/src/components/trip/JourneyDashboard.tsx`

**Step 1: Extract hero photo from journey data**

After the existing state declarations (around line 50), add hero photo extraction:

```tsx
// Use the first city's first highlight photo or accommodation photo as hero
const heroPhoto = (() => {
  for (const city of journey?.cities ?? []) {
    // Check day plan activities for photos first (higher quality)
    const cityDays = dayPlans?.filter(dp => dp.city_name.toLowerCase() === city.name.toLowerCase());
    for (const dp of cityDays ?? []) {
      for (const act of dp.activities) {
        if (act.place.photo_urls?.[0]) return act.place.photo_urls[0];
      }
    }
    // Fall back to accommodation photo
    if (city.accommodation?.photo_url) return city.accommodation.photo_url;
  }
  return null;
})();
```

**Step 2: Replace the header Card with a hero-banner card**

Replace the header card section (the `<Card>` starting around line 269) — wrap the CardHeader in a hero container:

Replace `<Card>` opening through `<CardHeader>` with:

```tsx
<Card className="overflow-hidden">
  {heroPhoto && (
    <div className="relative h-36 sm:h-48">
      <img
        src={`${photoUrl(heroPhoto)}${heroPhoto.includes('?') ? '&' : '?'}w=1200`}
        alt={journey.theme}
        className="absolute inset-0 h-full w-full object-cover"
      />
      <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/30 to-black/10" />
      <div className="absolute bottom-0 left-0 right-0 p-4 sm:p-5">
        <div className="flex items-end justify-between gap-4">
          <div className="min-w-0 flex-1">
            <h2 className="text-xl sm:text-2xl font-display font-bold text-white drop-shadow-sm break-words">
              {journey.theme}
            </h2>
            <p className="mt-1 text-sm text-white/80 line-clamp-2 break-words">
              {journey.summary}
            </p>
          </div>
          {journey.review_score != null && (
            <Badge
              className={`shrink-0 text-xs border-white/30 ${
                journey.review_score >= 80 ? 'bg-green-500/80 text-white'
                  : journey.review_score >= 70 ? 'bg-green-500/60 text-white'
                    : 'bg-amber-500/60 text-white'
              }`}
            >
              Score: {journey.review_score}
            </Badge>
          )}
        </div>
      </div>
    </div>
  )}
  {!heroPhoto && (
    <CardHeader>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <CardTitle className="text-xl font-display flex items-center gap-2 min-w-0">
            <Sparkles className="h-5 w-5 text-primary-500 shrink-0" />
            <span className="break-words">{journey.theme}</span>
          </CardTitle>
          <CardDescription className="mt-2 text-base leading-relaxed break-words">
            {journey.summary}
          </CardDescription>
        </div>
        {journey.review_score != null && (
          <Badge
            variant={journey.review_score >= 70 ? 'default' : 'outline'}
            className={`shrink-0 text-xs ${
              journey.review_score >= 80 ? 'bg-green-600 text-white'
                : journey.review_score >= 70 ? 'bg-green-600/80 text-white'
                  : 'border-amber-400 text-amber-700 dark:text-amber-400'
            }`}
          >
            Score: {journey.review_score}
          </Badge>
        )}
      </div>
    </CardHeader>
  )}
```

Remove the existing `<CardHeader>` block that this replaces (lines 270-293). The `<CardContent>` block starting at line 295 stays unchanged.

**Step 3: Add `photoUrl` to imports**

Add `photoUrl` to the import from `@/services/api` (line 23):

```tsx
import { api, photoUrl } from '@/services/api';
```

**Step 4: Build and commit**

```bash
cd frontend && npm run build
```

Commit: `feat(dashboard): destination hero imagery banner with gradient overlay`

---

### Task 5: Immersive Planning Animation (#3)

Replace the generic spinner in PlanningDashboard with a visually rich animated route-drawing experience.

**Files:**
- Modify: `frontend/src/components/trip/PlanningDashboard.tsx`
- Modify: `frontend/src/index.css`

**Step 1: Add planning animation keyframes to index.css**

In `index.css`, after the confetti keyframes, add:

```css
/* Planning route animation */
@keyframes draw-path {
  to { stroke-dashoffset: 0; }
}

@keyframes plane-fly {
  0% { offset-distance: 0%; }
  100% { offset-distance: 100%; }
}

@keyframes city-pop {
  0% { transform: scale(0); opacity: 0; }
  50% { transform: scale(1.3); }
  100% { transform: scale(1); opacity: 1; }
}
.animate-city-pop {
  animation: city-pop 0.4s ease-out both;
}
```

**Step 2: Add animated route SVG component in PlanningDashboard.tsx**

After the `formatElapsed` function (around line 126), add:

```tsx
function PlanningAnimation({ phase, elapsed }: { phase: string; elapsed: number }) {
  // Show 3 city nodes that pop in as planning progresses
  const cityCount = phase === 'scouting' ? 1 : phase === 'enriching' ? 2 : 3;
  const showPath = phase !== 'scouting';
  const showPlane = phase === 'reviewing' || phase === 'improving';

  return (
    <div className="relative flex items-center justify-center py-4">
      <svg viewBox="0 0 300 60" className="w-full max-w-xs h-16" fill="none">
        {/* Path between cities */}
        {showPath && (
          <path
            d="M 50 30 Q 100 10 150 30 Q 200 50 250 30"
            stroke="currentColor"
            strokeWidth="2"
            strokeDasharray="200"
            strokeDashoffset="200"
            className="text-primary-300 dark:text-primary-700"
            style={{ animation: 'draw-path 2s ease-out forwards' }}
          />
        )}
        {/* City nodes */}
        {[50, 150, 250].slice(0, cityCount).map((cx, i) => (
          <g key={i}>
            <circle
              cx={cx}
              cy={30}
              r={8}
              className={`fill-primary-500 dark:fill-primary-400 animate-city-pop`}
              style={{ animationDelay: `${i * 0.3}s` }}
            />
            <circle
              cx={cx}
              cy={30}
              r={12}
              className="fill-none stroke-primary-300 dark:stroke-primary-700"
              strokeWidth="1"
              opacity={0.5}
              style={{ animationDelay: `${i * 0.3}s` }}
            />
          </g>
        ))}
        {/* Plane icon */}
        {showPlane && (
          <text
            fontSize="14"
            style={{
              offsetPath: 'path("M 50 30 Q 100 10 150 30 Q 200 50 250 30")',
              animation: 'plane-fly 3s linear infinite',
            }}
          >
            ✈
          </text>
        )}
      </svg>
    </div>
  );
}
```

**Step 3: Insert the animation into the PlanningDashboard render**

In the component render (around line 210), after the Header `<div>` (line 225) and before the Pipeline stepper, add:

```tsx
<PlanningAnimation phase={phase} elapsed={elapsedSeconds} />
```

**Step 4: Build and commit**

```bash
cd frontend && npm run build
```

Commit: `feat(planning): immersive route-drawing animation during trip planning`

---

### Task 6: Wizard Step Slide Transitions (#7)

Add directional slide animations when navigating between wizard steps.

**Files:**
- Modify: `frontend/src/components/trip/WizardForm.tsx`

**Step 1: Track slide direction**

Add a `slideDirection` state after the existing form state declarations (around line 65):

```tsx
const [slideDirection, setSlideDirection] = useState<'right' | 'left'>('right');
```

**Step 2: Update handleNext and handleBack to set direction**

Replace the existing `handleNext` callback (line 87-89):
```tsx
const handleNext = useCallback(() => {
  setSlideDirection('right');
  setWizardStep(Math.min(wizardStep + 1, 5));
}, [wizardStep, setWizardStep]);
```

Replace the existing `handleBack` callback (line 91-93):
```tsx
const handleBack = useCallback(() => {
  setSlideDirection('left');
  setWizardStep(Math.max(wizardStep - 1, 1));
}, [wizardStep, setWizardStep]);
```

**Step 3: Apply directional animation to step container**

Replace the step container div (line 201):
```tsx
<div className="animate-fade-in-up transition-all duration-300 ease-out">
```
With:
```tsx
<div key={wizardStep} className={slideDirection === 'right' ? 'animate-slide-right' : 'animate-slide-left'}>
```

The `key={wizardStep}` forces React to remount when step changes, triggering the animation.

**Step 4: Build and commit**

```bash
cd frontend && npm run build
```

Commit: `feat(wizard): directional slide transitions between steps`

---

### Task 7: Budget Visualization + Enhanced Celebration (#6, #9)

Add a visual bar chart to BudgetSummary and confetti particles to the celebration banner.

**Files:**
- Modify: `frontend/src/components/trip/BudgetSummary.tsx`
- Modify: `frontend/src/components/trip/JourneyDashboard.tsx`

**Step 1: Add visual spending bars to BudgetSummary**

After the grid section (after line 95, before the budget comparison section), add a horizontal bar chart:

```tsx
{/* Visual spending breakdown */}
{(() => {
  const segments = [
    { label: 'Accommodation', amount: costBreakdown.accommodation_usd, color: 'bg-primary-500' },
    { label: 'Transport', amount: costBreakdown.transport_usd, color: 'bg-accent-500' },
    { label: 'Dining', amount: costBreakdown.dining_usd, color: 'bg-green-500' },
    { label: 'Activities', amount: costBreakdown.activities_usd, color: 'bg-purple-500' },
  ].filter(s => s.amount > 0);
  const total = costBreakdown.total_usd;

  return segments.length > 1 ? (
    <div className="space-y-2">
      <p className="text-xs text-text-muted font-medium">Spending Breakdown</p>
      <div className="flex h-4 rounded-full overflow-hidden bg-surface-muted">
        {segments.map((seg) => (
          <div
            key={seg.label}
            className={`${seg.color} transition-all duration-500`}
            style={{ width: `${(seg.amount / total) * 100}%` }}
            title={`${seg.label}: $${seg.amount.toFixed(0)} (${((seg.amount / total) * 100).toFixed(0)}%)`}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {segments.map((seg) => (
          <span key={seg.label} className="flex items-center gap-1.5 text-xs text-text-muted">
            <span className={`h-2.5 w-2.5 rounded-full ${seg.color}`} />
            {seg.label} ({((seg.amount / total) * 100).toFixed(0)}%)
          </span>
        ))}
      </div>
    </div>
  ) : null;
})()}
```

**Step 2: Add confetti particles to celebration banner in JourneyDashboard**

Replace the celebration banner (around lines 245-266) with an enhanced version that includes confetti:

```tsx
{showCelebration && journey && (
  <div className="animate-fade-in-up mb-4 rounded-xl bg-gradient-to-r from-primary-600 to-accent-500 p-5 text-white text-center shadow-lg relative overflow-hidden">
    {/* Confetti particles */}
    <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
      {Array.from({ length: 20 }).map((_, i) => (
        <div
          key={i}
          className="absolute w-2 h-2 rounded-full"
          style={{
            left: `${Math.random() * 100}%`,
            backgroundColor: ['#FFD700', '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8'][i % 6],
            animation: `confetti-fall ${2 + Math.random() * 2}s ease-out ${Math.random() * 0.5}s forwards`,
            opacity: 0.8,
          }}
        />
      ))}
    </div>
    <p className="text-xl font-display font-bold relative">Your adventure awaits!</p>
    <p className="text-sm opacity-90 mt-1 relative">
      {journey.cities.length} cities · {journey.total_days} days{journey.review_score ? ` · Quality score ${journey.review_score}/100` : ''}
    </p>
    <div className="flex items-center justify-center gap-3 mt-3 relative">
      <button
        onClick={() => { handleShare(); setShowCelebration(false); }}
        className="text-xs bg-white/20 hover:bg-white/30 rounded-full px-4 py-1.5 transition-colors"
      >
        Share with friends
      </button>
      <button
        onClick={() => { handleExportPdf(); setShowCelebration(false); }}
        className="text-xs bg-white/20 hover:bg-white/30 rounded-full px-4 py-1.5 transition-colors"
      >
        Download PDF
      </button>
    </div>
  </div>
)}
```

**Step 3: Build and commit**

```bash
cd frontend && npm run build
```

Commit: `feat(budget+celebration): visual spending bars and confetti celebration`

---

### Task 8: Mobile Swipe + Scroll Reveal + Stagger Polish (#10, #11, #4)

Add touch swipe gestures to FullDayView, scroll-triggered reveal to city cards, and stagger animations to overview city grid.

**Files:**
- Modify: `frontend/src/components/trip/FullDayView.tsx`
- Modify: `frontend/src/components/trip/JourneyDashboard.tsx`

**Step 1: Add touch swipe to FullDayView**

In FullDayView.tsx, after the existing state declarations, add touch tracking:

```tsx
const [touchStart, setTouchStart] = useState<number | null>(null);
const [touchEnd, setTouchEnd] = useState<number | null>(null);
const minSwipeDistance = 50;

const onTouchStart = (e: React.TouchEvent) => {
  setTouchEnd(null);
  setTouchStart(e.targetTouches[0].clientX);
};

const onTouchMove = (e: React.TouchEvent) => {
  setTouchEnd(e.targetTouches[0].clientX);
};

const onTouchEnd = () => {
  if (!touchStart || !touchEnd) return;
  const distance = touchStart - touchEnd;
  const isSwipe = Math.abs(distance) > minSwipeDistance;
  if (isSwipe) {
    if (distance > 0 && hasNext) {
      // Swipe left → next day
      setCurrentIndex(currentIndex + 1);
    } else if (distance < 0 && hasPrev) {
      // Swipe right → prev day
      setCurrentIndex(currentIndex - 1);
    }
  }
};
```

Apply the touch handlers to the main content container div. Add `onTouchStart`, `onTouchMove`, `onTouchEnd` to the scrollable content area.

Also add a swipe hint on mobile (show once):
```tsx
{currentIndex === 0 && (
  <p className="text-xs text-text-muted text-center mt-2 sm:hidden animate-swipe-hint">
    ← Swipe to navigate between days →
  </p>
)}
```

**Step 2: Add stagger animation to overview city grid in JourneyDashboard**

In the overview tab city highlights grid (around line 462), add stagger classes to each city card:

Replace:
```tsx
{journey.cities.map((city, i) => (
  <Card key={i} className="cursor-pointer hover:border-primary-300 transition-colors" onClick={() => setActiveTab('cities')}>
```
With:
```tsx
{journey.cities.map((city, i) => (
  <Card key={i} className={`cursor-pointer hover:border-primary-300 transition-colors animate-stagger-in stagger-${Math.min(i + 1, 8)}`} onClick={() => setActiveTab('cities')}>
```

**Step 3: Add scroll-reveal to CompactCityCard containers in Cities tab**

In the Cities tab (around line 582), add a scroll-reveal effect using IntersectionObserver. Add a simple hook:

In JourneyDashboard, before the return statement, add:

```tsx
// Scroll-reveal for city cards
useEffect(() => {
  if (activeTab !== 'cities') return;
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.1 }
  );
  const elements = document.querySelectorAll('.scroll-reveal');
  elements.forEach((el) => observer.observe(el));
  return () => observer.disconnect();
}, [activeTab, dayPlans]);
```

Then wrap each CompactCityCard (around line 583-601) in a scroll-reveal div:

```tsx
<div key={`city-${i}-${allExpanded}`} className="scroll-reveal">
  <CompactCityCard ... />
</div>
```

Move the `key` to the wrapper div and remove it from CompactCityCard.

**Step 4: Build and commit**

```bash
cd frontend && npm run build
```

Commit: `feat(mobile+polish): swipe navigation, scroll-reveal, stagger animations`

---

## Summary

| Task | Improvements | Key Change |
|------|-------------|------------|
| 1 | #4, #11, #12 | CSS animation foundation + dark mode enhancement |
| 2 | #2, #8 | Photo-first activity cards + shimmer loaders |
| 3 | #5 | Weather-driven day atmosphere gradients |
| 4 | #1 | Destination hero imagery banner |
| 5 | #3 | Immersive planning route animation |
| 6 | #7 | Wizard directional slide transitions |
| 7 | #6, #9 | Budget spending bars + confetti celebration |
| 8 | #10, #11, #4 | Swipe nav + scroll reveal + stagger polish |

**Execution order is 1→8 sequentially. Task 1 must be first (CSS foundation). All others can follow in order.**

## Verification

After all 8 tasks:
1. `cd frontend && npm run build` — TypeScript check + production build must pass
2. Visual check: Run `npm run dev` and test on mobile viewport (375px)
3. Check dark mode: all new gradients/colors should look intentional, not mechanical
4. Check animations: stagger should cascade, scroll-reveal should trigger on scroll, wizard should slide
5. Check celebration: confetti particles should fall on plan completion
6. Check weather atmosphere: sunny/rainy/cloudy days should have visually distinct backgrounds
