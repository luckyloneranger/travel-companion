# CSS Revamp Design: Warm & Organic Earth Tones

**Date:** 2026-02-28
**Status:** Approved
**Approach:** Foundation First (design tokens -> cascade -> transitions -> component polish)

## Summary

Complete visual overhaul of the Travel Companion frontend. Replace the current violet/purple glass morphism design with a warm, organic, earth-tone aesthetic. Add step-by-step phase transitions with a stepper indicator and back navigation.

## 1. Color & Visual System

### Brand Palette

| Token | Old Value | New Value | Hex |
|-------|-----------|-----------|-----|
| Primary | Violet 600 | Terracotta | `#C97B5A` |
| Primary Dark | Violet 700 | Deep Terracotta | `#A66244` |
| Primary Light | Violet 500 | Soft Terracotta | `#D4956F` |
| Secondary | Emerald 600 | Sage Green | `#8B9E6B` |
| Secondary Dark | Emerald 700 | Deep Sage | `#728556` |
| Accent | Orange 500 | Warm Sand | `#D4A574` |
| Background | `#faf9fe` | `#FBF8F4` (warm cream) |
| Surface | white | `#F5F0E8` (parchment) |
| Text Primary | `#1e1b4b` | `#3D3229` (warm charcoal) |
| Text Muted | gray-500 | `#9C8E82` (stone) |
| Border | gray-100 | `#E8E0D4` (warm sand border) |

### Tailwind Primary Scale

```
50:  #FCF8F5
100: #F7EDE5
200: #EDCDB8
300: #E3AD8B
400: #D4956F
500: #C97B5A
600: #C97B5A (primary)
700: #A66244
800: #834D35
900: #603828
```

### Removals

- Glass morphism (`.glass`, `.glass-strong` from index.css)
- Mesh gradient background (`.bg-mesh`)
- Violet-tinted shadows (`rgba(124, 58, 237, ...)`)
- Focus ring with violet (`rgba(139, 92, 246, ...)`)
- Scrollbar violet tints

### Replacements

- Shadows: warm neutral (`rgba(61, 50, 41, 0.06)` base)
- Focus rings: terracotta-tinted (`rgba(201, 123, 90, 0.15)`)
- Scrollbar: warm stone tint
- Background: plain `#FBF8F4`

### Rotating Palettes (5 earth-tone palettes for cities/days)

1. **Terracotta** — `#C97B5A`, bg `#FCF8F5`, border `#EDCDB8`
2. **Sage** — `#8B9E6B`, bg `#F5F7F0`, border `#C5D4AB`
3. **Sand** — `#D4A574`, bg `#FDF8F3`, border `#E8D4BC`
4. **Clay** — `#B07878`, bg `#FBF5F5`, border `#DAC0C0`
5. **Stone** — `#8E8478`, bg `#F7F5F2`, border `#D4CEC7`

### Category Styles

Simplify from 20+ entries to earth-tone warmth. Keep the same category -> color mapping logic but use muted warm tones.

### Typography

Keep Inter + Plus Jakarta Sans. Change text color references from gray/indigo to warm charcoal family.

## 2. Phase Transition UX

### Phase Stepper

New `PhaseIndicator.tsx` component:
- Horizontal breadcrumb bar at top of `<main>`
- Shows phases: Plan -> Generating -> Preview -> Day Plans
- Current = terracotta dot, completed = sage checkmark, future = stone circle
- Hidden during input phase, appears once planning starts
- Back arrow + "Back to [phase]" label

### Transitions

| Transition | Animation | Duration |
|-----------|-----------|----------|
| Input -> Planning | Fade out/in | 300ms ease-out |
| Planning -> Preview | Slide-in from right + scale-up | 400ms cubic-bezier(0.16, 1, 0.3, 1) |
| Preview -> Day Plans | Smooth expand below | 300ms ease-out |
| Any -> Input (reset) | Quick crossfade | 200ms |

### Implementation

Wrap phase content in `<PhaseTransition>` wrapper component. Pure CSS `@keyframes` + className toggling. No animation library.

### Back Navigation

- Preview -> Input: clears plan, re-shows form
- Day Plans -> Preview: keeps plan, collapses day details

## 3. Component-Level Polish

### Form Inputs

- Focus rings: terracotta (`0 0 0 3px rgba(201, 123, 90, 0.15)`)
- Input backgrounds: `#FBF8F4`
- Chip selectors: warm surfaces with terracotta active state
- Date picker: terracotta focus color
- Keep `rounded-xl`

### Cards

- Headers: solid warm-tone (per palette), no gradients
- Shadows: warm neutral
- Borders: `#E8E0D4`
- Hover: slight lift + border darken

### Header

- Clean warm cream background + subtle bottom border
- No glass, no gradient
- Logo/title in warm charcoal

### Mode Toggle

- Active: solid terracotta fill + white text
- Inactive: transparent + warm charcoal text, hover = parchment background

### Journey Preview

- Header card: solid terracotta background, cream text
- Stats grid: warm surface cards with sage/sand/terracotta accents
- Route pills: earth-tone palette cycling
- Timeline connector: warm sand dotted line

### Chat Panel

- Header: sage green (solid)
- User messages: terracotta tint
- AI messages: parchment surface
- Input field matches new form styling

### Footer

- Simple warm cream background + subtle top border (no glass)

## 4. Generation Progress Redesign

### Journey Planning Mode

- Horizontal "journey storyline" path: Scout -> Enrich -> Review -> Planner
- Active phase: pulsing terracotta dot
- Completed: sage green checkmark
- Current message below path in warm charcoal
- Single thin progress bar at top in terracotta
- Remove emojis from messages
- Iteration counter: subtle "Refining... (iteration 2)" in stone text

### Itinerary Mode

- Same thin top progress bar
- Vertical checklist: geocoding -> discovering -> planning -> optimizing -> scheduling -> validating
- Checkmarks for completed, terracotta dot for active, stone circle for pending

### Day Plans Side Panel

- Header: sage green (solid, no gradient)
- City cards: parchment surface with earth-tone badges
- Replace spinner with calm terracotta pulsing dot
- More whitespace

### Cancel Button

- Secondary warm style (white bg, warm border, warm charcoal text)

## Files to Modify

### Foundation (do first)
1. `frontend/src/styles/design-system.ts` — all tokens, palettes, shadows, glass removal
2. `frontend/tailwind.config.js` — primary color scale, animations
3. `frontend/src/index.css` — background, scrollbar, glass classes, animations, mesh gradient, date picker

### Structural (new components)
4. `frontend/src/components/PhaseIndicator.tsx` — new stepper component
5. `frontend/src/components/PhaseTransition.tsx` — new transition wrapper

### Component Updates
6. `frontend/src/App.tsx` — stepper integration, transition wrappers, back navigation, remove emojis, restyle mode toggle + hero + footer
7. `frontend/src/components/Header.tsx` — remove gradient, warm styling
8. `frontend/src/components/GenerationProgress.tsx` — full redesign per section 4
9. `frontend/src/components/JourneyInputForm.tsx` — form styling updates
10. `frontend/src/components/ItineraryInputForm.tsx` — form styling updates
11. `frontend/src/components/V6JourneyPlanView/index.tsx` — header, stats, timeline
12. `frontend/src/components/V6JourneyPlanView/CityCard.tsx` — earth-tone cards
13. `frontend/src/components/V6JourneyPlanView/TravelLegCard.tsx` — warm styling
14. `frontend/src/components/shared/ActivityCard.tsx` — warm cards
15. `frontend/src/components/JourneyChat.tsx` — warm chat panel
16. `frontend/src/components/ItineraryView.tsx` — warm styling
