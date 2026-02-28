# CSS Revamp Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the violet/purple glass morphism design with a warm, organic earth-tone aesthetic and add step-by-step phase transitions.

**Architecture:** Foundation-first approach. Update design tokens and CSS foundation first (Tasks 1-3), then add new structural components (Tasks 4-5), then cascade through every component (Tasks 6-14). Each task is one coherent unit of work.

**Tech Stack:** React, TypeScript, Tailwind CSS, CSS keyframes (no animation library)

---

### Task 1: Update Tailwind Config — Earth Tone Primary Scale

**Files:**
- Modify: `frontend/tailwind.config.js`

**Step 1: Replace primary color scale with earth tones**

Replace the entire `colors.primary` object in `tailwind.config.js`:

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#FCF8F5',
          100: '#F7EDE5',
          200: '#EDCDB8',
          300: '#E3AD8B',
          400: '#D4956F',
          500: '#C97B5A',
          600: '#C97B5A',
          700: '#A66244',
          800: '#834D35',
          900: '#603828',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'shimmer': 'shimmer 2s linear infinite',
        'scale-in': 'scaleIn 0.2s ease-out',
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-in-right': 'slideInRight 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
        'fade-out': 'fadeOut 0.2s ease-out',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-6px)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideInRight: {
          '0%': { opacity: '0', transform: 'translateX(24px) scale(0.98)' },
          '100%': { opacity: '1', transform: 'translateX(0) scale(1)' },
        },
        fadeOut: {
          '0%': { opacity: '1' },
          '100%': { opacity: '0' },
        },
      },
    },
  },
  plugins: [],
};
```

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds (Tailwind config is valid)

**Step 3: Commit**

```bash
git add frontend/tailwind.config.js
git commit -m "feat(ui): update Tailwind config with earth-tone primary scale and transition animations"
```

---

### Task 2: Overhaul Design System Tokens

**Files:**
- Modify: `frontend/src/styles/design-system.ts` (full rewrite of color sections)

**Step 1: Replace brand colors, palettes, header gradients, category styles, shadows, and remove glass**

Replace the full content of `design-system.ts` with earth-tone tokens. Key changes:

**Brand colors** (lines 15-22):
```ts
export const brand = {
  primary: '#C97B5A',       // terracotta
  primaryDark: '#A66244',   // deep terracotta
  primaryLight: '#D4956F',  // soft terracotta
  secondary: '#8B9E6B',     // sage green
  secondaryDark: '#728556', // deep sage
  accent: '#D4A574',        // warm sand
} as const;
```

**Rotating palettes** — replace 7 saturated palettes with 5 earth-tone:
```ts
export const colorPalettes = [
  {
    name: 'terracotta',
    gradientFrom: '#C97B5A',
    gradientTo: '#D4956F',
    bgColor: '#FCF8F5',
    borderColor: '#EDCDB8',
    textColor: '#A66244',
    accentColor: '#C97B5A',
  },
  {
    name: 'sage',
    gradientFrom: '#8B9E6B',
    gradientTo: '#A3B584',
    bgColor: '#F5F7F0',
    borderColor: '#C5D4AB',
    textColor: '#728556',
    accentColor: '#8B9E6B',
  },
  {
    name: 'sand',
    gradientFrom: '#D4A574',
    gradientTo: '#E0BB91',
    bgColor: '#FDF8F3',
    borderColor: '#E8D4BC',
    textColor: '#B8884F',
    accentColor: '#D4A574',
  },
  {
    name: 'clay',
    gradientFrom: '#B07878',
    gradientTo: '#C4918F',
    bgColor: '#FBF5F5',
    borderColor: '#DAC0C0',
    textColor: '#96615F',
    accentColor: '#B07878',
  },
  {
    name: 'stone',
    gradientFrom: '#8E8478',
    gradientTo: '#A39A8F',
    bgColor: '#F7F5F2',
    borderColor: '#D4CEC7',
    textColor: '#6E655B',
    accentColor: '#8E8478',
  },
] as const;
```

**Light palettes** — replace 7 with 5 earth-tone soft variants:
```ts
export const lightPalettes = [
  {
    name: 'soft-terracotta',
    gradientFrom: '#EDCDB8',
    gradientTo: '#F7EDE5',
    headerBg: 'linear-gradient(135deg, #FCF8F5 0%, #FDF6F0 100%)',
    textColor: '#A66244',
    accentColor: '#C97B5A',
    borderColor: '#E3AD8B',
    iconBg: 'linear-gradient(135deg, #D4956F, #C97B5A)',
  },
  {
    name: 'soft-sage',
    gradientFrom: '#C5D4AB',
    gradientTo: '#D9E4C4',
    headerBg: 'linear-gradient(135deg, #F5F7F0 0%, #F0F4E8 100%)',
    textColor: '#728556',
    accentColor: '#8B9E6B',
    borderColor: '#A8BD88',
    iconBg: 'linear-gradient(135deg, #A3B584, #8B9E6B)',
  },
  {
    name: 'soft-sand',
    gradientFrom: '#E8D4BC',
    gradientTo: '#F0E2D0',
    headerBg: 'linear-gradient(135deg, #FDF8F3 0%, #FCF4EB 100%)',
    textColor: '#B8884F',
    accentColor: '#D4A574',
    borderColor: '#D4B896',
    iconBg: 'linear-gradient(135deg, #E0BB91, #D4A574)',
  },
  {
    name: 'soft-clay',
    gradientFrom: '#DAC0C0',
    gradientTo: '#E5D2D2',
    headerBg: 'linear-gradient(135deg, #FBF5F5 0%, #F9F0F0 100%)',
    textColor: '#96615F',
    accentColor: '#B07878',
    borderColor: '#CCA8A6',
    iconBg: 'linear-gradient(135deg, #C4918F, #B07878)',
  },
  {
    name: 'soft-stone',
    gradientFrom: '#D4CEC7',
    gradientTo: '#E0DBD5',
    headerBg: 'linear-gradient(135deg, #F7F5F2 0%, #F3F0EC 100%)',
    textColor: '#6E655B',
    accentColor: '#8E8478',
    borderColor: '#BEB7AE',
    iconBg: 'linear-gradient(135deg, #A39A8F, #8E8478)',
  },
] as const;
```

**Header gradients** — replace with earth tones:
```ts
export const headerGradients = {
  journey: {
    from: '#C97B5A',
    to: '#D4956F',
    css: 'linear-gradient(135deg, #C97B5A, #D4956F)',
  },
  dayPlan: {
    from: '#8B9E6B',
    to: '#A3B584',
    css: 'linear-gradient(135deg, #8B9E6B, #A3B584)',
  },
  stats: {
    from: '#8E8478',
    to: '#A39A8F',
    css: 'linear-gradient(135deg, #8E8478, #A39A8F)',
  },
  transport: {
    from: '#D4A574',
    to: '#B8884F',
    css: 'linear-gradient(135deg, #D4A574, #B8884F)',
  },
  accent: {
    from: '#D4A574',
    to: '#E0BB91',
    css: 'linear-gradient(135deg, #D4A574, #E0BB91)',
  },
  rose: {
    from: '#B07878',
    to: '#C4918F',
    css: 'linear-gradient(135deg, #B07878, #C4918F)',
  },
} as const;
```

**Category styles** — replace with earth-tone warm palette:
```ts
export const categoryStyles: Record<string, {
  bg: string;
  text: string;
  border: string;
  accent: string;
  gradient: string;
}> = {
  // Culture & Arts — terracotta family
  culture: { bg: '#FCF8F5', text: '#A66244', border: '#EDCDB8', accent: '#C97B5A', gradient: 'linear-gradient(135deg, #C97B5A, #A66244)' },
  museum: { bg: '#FCF8F5', text: '#A66244', border: '#EDCDB8', accent: '#D4956F', gradient: 'linear-gradient(135deg, #D4956F, #C97B5A)' },
  art: { bg: '#FBF5F5', text: '#96615F', border: '#DAC0C0', accent: '#B07878', gradient: 'linear-gradient(135deg, #B07878, #96615F)' },

  // Food & Dining — sand/warm family
  food: { bg: '#FDF8F3', text: '#B8884F', border: '#E8D4BC', accent: '#D4A574', gradient: 'linear-gradient(135deg, #D4A574, #B8884F)' },
  breakfast: { bg: '#FDF8F3', text: '#B8884F', border: '#E8D4BC', accent: '#E0BB91', gradient: 'linear-gradient(135deg, #E0BB91, #D4A574)' },
  lunch: { bg: '#FDF8F3', text: '#A66244', border: '#EDCDB8', accent: '#C97B5A', gradient: 'linear-gradient(135deg, #C97B5A, #A66244)' },
  dinner: { bg: '#FBF5F5', text: '#96615F', border: '#DAC0C0', accent: '#B07878', gradient: 'linear-gradient(135deg, #B07878, #96615F)' },
  restaurant: { bg: '#FDF8F3', text: '#B8884F', border: '#E8D4BC', accent: '#D4A574', gradient: 'linear-gradient(135deg, #D4A574, #B8884F)' },
  cafe: { bg: '#FDF8F3', text: '#8E7656', border: '#E0D4C2', accent: '#B8975E', gradient: 'linear-gradient(135deg, #B8975E, #8E7656)' },

  // Nature & Outdoors — sage family
  nature: { bg: '#F5F7F0', text: '#728556', border: '#C5D4AB', accent: '#8B9E6B', gradient: 'linear-gradient(135deg, #8B9E6B, #728556)' },
  park: { bg: '#F5F7F0', text: '#728556', border: '#C5D4AB', accent: '#A3B584', gradient: 'linear-gradient(135deg, #A3B584, #8B9E6B)' },
  beach: { bg: '#F5F7F2', text: '#6B8A6B', border: '#B8D4B8', accent: '#7BA37B', gradient: 'linear-gradient(135deg, #7BA37B, #6B8A6B)' },

  // History & Architecture — stone/warm amber family
  history: { bg: '#F7F5F2', text: '#6E655B', border: '#D4CEC7', accent: '#8E8478', gradient: 'linear-gradient(135deg, #8E8478, #6E655B)' },
  landmark: { bg: '#FCF8F5', text: '#A66244', border: '#EDCDB8', accent: '#C97B5A', gradient: 'linear-gradient(135deg, #C97B5A, #A66244)' },
  architecture: { bg: '#F7F5F2', text: '#6E655B', border: '#D4CEC7', accent: '#8E8478', gradient: 'linear-gradient(135deg, #8E8478, #6E655B)' },
  religious: { bg: '#FDF8F3', text: '#B8884F', border: '#E8D4BC', accent: '#D4A574', gradient: 'linear-gradient(135deg, #D4A574, #B8884F)' },

  // Entertainment & Lifestyle — clay/terracotta family
  shopping: { bg: '#FBF5F5', text: '#96615F', border: '#DAC0C0', accent: '#B07878', gradient: 'linear-gradient(135deg, #B07878, #96615F)' },
  nightlife: { bg: '#F7F5F2', text: '#6E655B', border: '#D4CEC7', accent: '#8E8478', gradient: 'linear-gradient(135deg, #8E8478, #6E655B)' },
  adventure: { bg: '#FCF8F5', text: '#A66244', border: '#EDCDB8', accent: '#C97B5A', gradient: 'linear-gradient(135deg, #C97B5A, #A66244)' },
  relaxation: { bg: '#F5F7F0', text: '#728556', border: '#C5D4AB', accent: '#8B9E6B', gradient: 'linear-gradient(135deg, #8B9E6B, #728556)' },
  entertainment: { bg: '#FBF5F5', text: '#96615F', border: '#DAC0C0', accent: '#B07878', gradient: 'linear-gradient(135deg, #B07878, #96615F)' },

  // Default fallback — stone
  default: { bg: '#F7F5F2', text: '#6E655B', border: '#D4CEC7', accent: '#8E8478', gradient: 'linear-gradient(135deg, #8E8478, #6E655B)' },
};
```

**Shadows** — replace violet tint with warm neutral:
```ts
export const shadows = {
  none: 'none',
  xs: '0 1px 2px rgba(61, 50, 41, 0.04)',
  sm: '0 1px 3px rgba(61, 50, 41, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04)',
  md: '0 4px 12px rgba(61, 50, 41, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04)',
  lg: '0 8px 24px rgba(61, 50, 41, 0.1), 0 4px 8px rgba(0, 0, 0, 0.04)',
  xl: '0 16px 40px rgba(61, 50, 41, 0.12), 0 8px 16px rgba(0, 0, 0, 0.04)',
  ring: '0 0 0 3px rgba(201, 123, 90, 0.15)',
  glow: '0 8px 32px rgba(201, 123, 90, 0.2)',
} as const;
```

**Remove** the `glass` export entirely. Delete the glass object and `glassStyle` function. Update `cardStyles` button colors:

```ts
export const buttonStyles = {
  primary: {
    base: 'bg-primary-600 text-white font-semibold',
    hover: 'hover:bg-primary-700 hover:-translate-y-0.5',
    disabled: 'disabled:bg-gray-300 disabled:cursor-not-allowed disabled:translate-y-0',
    shadow: 'shadow-md hover:shadow-lg',
  },
  secondary: {
    base: 'bg-white text-gray-700 font-semibold border border-[#E8E0D4]',
    hover: 'hover:bg-[#F5F0E8] hover:border-[#D4CEC7] hover:-translate-y-0.5',
    disabled: 'disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed',
    shadow: 'shadow-sm hover:shadow',
  },
  ghost: {
    base: 'bg-transparent text-[#3D3229] font-medium',
    hover: 'hover:bg-[#F5F0E8] hover:text-[#3D3229]',
    disabled: 'disabled:text-gray-300 disabled:cursor-not-allowed',
    shadow: '',
  },
  accent: {
    base: 'bg-[#8B9E6B] text-white font-semibold',
    hover: 'hover:bg-[#728556] hover:-translate-y-0.5',
    disabled: 'disabled:bg-gray-300 disabled:cursor-not-allowed',
    shadow: 'shadow-md hover:shadow-lg',
  },
} as const;
```

**Step 2: Update re-export modules to remove glass references**

In `frontend/src/components/V6JourneyPlanView/styles.tsx`, remove the `glass`, `glassStyle` exports.

In `frontend/src/components/ItineraryView/styles.tsx`, remove the `glass`, `glassStyle` exports.

**Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds. There may be errors from components still referencing `glass`/`glassStyle` — that's expected and will be fixed in subsequent tasks.

**Step 4: Commit**

```bash
git add frontend/src/styles/design-system.ts frontend/src/components/V6JourneyPlanView/styles.tsx frontend/src/components/ItineraryView/styles.tsx
git commit -m "feat(ui): replace design tokens with earth-tone palette, remove glass morphism"
```

---

### Task 3: Overhaul index.css — Background, Scrollbar, Animations, Glass Removal

**Files:**
- Modify: `frontend/src/index.css`

**Step 1: Replace entire index.css**

Replace all 213 lines with updated earth-tone styles:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  font-family: 'Inter', system-ui, sans-serif;
  line-height: 1.5;
  font-weight: 400;
  color-scheme: light;
  color: #3D3229;
  background-color: #FBF8F4;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  margin: 0;
  min-height: 100vh;
}

#root {
  min-height: 100vh;
}

/* Display font utility */
.font-display {
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
}

/* Custom scrollbar — minimal & warm */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(201, 123, 90, 0.15);
  border-radius: 99px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(201, 123, 90, 0.3);
}

/* Thin scrollbar for horizontal scroll areas */
.scrollbar-thin::-webkit-scrollbar {
  height: 3px;
}

.scrollbar-thin::-webkit-scrollbar-track {
  background: transparent;
}

.scrollbar-thin::-webkit-scrollbar-thumb {
  background: rgba(201, 123, 90, 0.12);
  border-radius: 99px;
}

.scrollbar-thin::-webkit-scrollbar-thumb:hover {
  background: rgba(201, 123, 90, 0.25);
}

/* Hide scrollbar but allow scroll */
.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.scrollbar-hide::-webkit-scrollbar {
  display: none;
}

/* Date picker overrides — warm */
.react-datepicker-wrapper {
  width: 100%;
}

.react-datepicker__input-container input {
  width: 100%;
  padding: 0.625rem 0.875rem;
  border: 1px solid #E8E0D4;
  border-radius: 0.75rem;
  font-size: 0.875rem;
  outline: none;
  background: #FBF8F4;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.react-datepicker__input-container input:focus {
  border-color: #C97B5A;
  box-shadow: 0 0 0 3px rgba(201, 123, 90, 0.1);
  background: white;
}

/* =========================================================
   Animation utilities
   ========================================================= */

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-8px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes scaleIn {
  from {
    opacity: 0;
    transform: scale(0.96);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

@keyframes slideInRight {
  from {
    opacity: 0;
    transform: translateX(24px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateX(0) scale(1);
  }
}

.animate-slide-in {
  animation: slideIn 0.3s ease-out forwards;
}

.animate-fade-in,
.animate-fadeIn {
  animation: fadeIn 0.3s ease-out forwards;
}

.animate-scale-in {
  animation: scaleIn 0.2s ease-out forwards;
}

.animate-pulse-slow {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.animate-slide-in-right {
  animation: slideInRight 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

/* =========================================================
   Focus ring utility — warm terracotta
   ========================================================= */

.focus-ring {
  outline: none;
}

.focus-ring:focus-visible {
  box-shadow: 0 0 0 2px white, 0 0 0 4px rgba(201, 123, 90, 0.4);
}
```

**Key removals:** `.glass`, `.glass-strong`, `.bg-mesh` classes. All violet rgba references replaced with terracotta.

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/index.css
git commit -m "feat(ui): update index.css with earth-tone colors, remove glass/mesh classes"
```

---

### Task 4: Create PhaseIndicator Component

**Files:**
- Create: `frontend/src/components/PhaseIndicator.tsx`

**Step 1: Create the stepper component**

```tsx
import { ChevronLeft, Check } from 'lucide-react';

type Phase = 'input' | 'planning' | 'preview' | 'day-plans';

const PHASES: { key: Phase; label: string }[] = [
  { key: 'input', label: 'Plan' },
  { key: 'planning', label: 'Generating' },
  { key: 'preview', label: 'Preview' },
  { key: 'day-plans', label: 'Day Plans' },
];

const PHASE_ORDER: Record<Phase, number> = {
  input: 0,
  planning: 1,
  preview: 2,
  'day-plans': 3,
};

interface PhaseIndicatorProps {
  currentPhase: Phase;
  onBack?: () => void;
  backLabel?: string;
}

export function PhaseIndicator({ currentPhase, onBack, backLabel }: PhaseIndicatorProps) {
  if (currentPhase === 'input') return null;

  const currentIndex = PHASE_ORDER[currentPhase];

  return (
    <div className="flex items-center gap-3 mb-6">
      {onBack && (
        <button
          onClick={onBack}
          className="flex items-center gap-1 text-sm text-[#9C8E82] hover:text-[#3D3229] transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
          <span>{backLabel || 'Back'}</span>
        </button>
      )}
      <div className="flex items-center gap-2 flex-1">
        {PHASES.map((phase, index) => {
          const isCompleted = index < currentIndex;
          const isCurrent = index === currentIndex;
          const isFuture = index > currentIndex;

          return (
            <div key={phase.key} className="flex items-center gap-2">
              {index > 0 && (
                <div
                  className={`h-px w-6 sm:w-10 ${
                    isCompleted ? 'bg-[#8B9E6B]' : 'bg-[#E8E0D4]'
                  }`}
                />
              )}
              <div className="flex items-center gap-1.5">
                {isCompleted ? (
                  <div className="w-5 h-5 rounded-full bg-[#8B9E6B] flex items-center justify-center">
                    <Check className="h-3 w-3 text-white" />
                  </div>
                ) : isCurrent ? (
                  <div className="w-5 h-5 rounded-full bg-[#C97B5A] animate-pulse" />
                ) : (
                  <div className="w-5 h-5 rounded-full bg-[#E8E0D4]" />
                )}
                <span
                  className={`text-xs font-medium hidden sm:inline ${
                    isCurrent
                      ? 'text-[#C97B5A]'
                      : isCompleted
                      ? 'text-[#8B9E6B]'
                      : 'text-[#9C8E82]'
                  }`}
                >
                  {phase.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds (component is not yet imported)

**Step 3: Commit**

```bash
git add frontend/src/components/PhaseIndicator.tsx
git commit -m "feat(ui): add PhaseIndicator stepper component"
```

---

### Task 5: Create PhaseTransition Wrapper Component

**Files:**
- Create: `frontend/src/components/PhaseTransition.tsx`

**Step 1: Create the transition wrapper**

```tsx
import { useEffect, useState, type ReactNode } from 'react';

interface PhaseTransitionProps {
  children: ReactNode;
  phase: string;
  animation?: 'fade' | 'slide-right' | 'scale';
}

export function PhaseTransition({ children, phase, animation = 'fade' }: PhaseTransitionProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Reset visibility on phase change to trigger re-animation
    setVisible(false);
    const timer = requestAnimationFrame(() => setVisible(true));
    return () => cancelAnimationFrame(timer);
  }, [phase]);

  const animationClass = visible
    ? animation === 'slide-right'
      ? 'animate-slide-in-right'
      : animation === 'scale'
      ? 'animate-scale-in'
      : 'animate-fade-in'
    : 'opacity-0';

  return (
    <div key={phase} className={animationClass}>
      {children}
    </div>
  );
}
```

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/components/PhaseTransition.tsx
git commit -m "feat(ui): add PhaseTransition wrapper component for phase animations"
```

---

### Task 6: Overhaul App.tsx — Integrate Stepper, Transitions, Warm Styling

**Files:**
- Modify: `frontend/src/App.tsx`

**Step 1: Update imports and integrate new components**

Add imports for `PhaseIndicator` and `PhaseTransition`. Remove emoji constants (`V6_PHASE_EMOJIS`, `DAY_PLAN_PHASE_EMOJIS`, `ITINERARY_PHASE_EMOJIS`).

**Step 2: Replace the return JSX**

Key changes:
- Remove `bg-mesh` class from root div → use `bg-[#FBF8F4]`
- Add `<PhaseIndicator>` below `<Header />`
- Wrap each phase in `<PhaseTransition>`
- Replace mode toggle gradient styling with solid terracotta
- Replace hero text colors with warm charcoal
- Replace footer `glass` with simple warm border
- Remove all gradient references from the side panel → use solid sage green
- Remove emojis from progress mapper functions
- Add back navigation handler

Specific class replacements in App.tsx:
- `bg-mesh` → `bg-[#FBF8F4]` (line 296)
- `glass-strong rounded-2xl p-1.5 shadow-lg border border-white/60` → `bg-[#F5F0E8] rounded-2xl p-1.5 shadow-sm border border-[#E8E0D4]` (mode toggle wrapper, line 367)
- Mode toggle active button: remove inline gradient `style` → use `bg-[#C97B5A] text-white shadow-sm` class
- `glass border-t border-white/40` → `bg-[#FBF8F4] border-t border-[#E8E0D4]` (footer, line 447)
- Side panel: `bg-white/95 backdrop-blur-xl shadow-2xl border-l border-white/60` → `bg-white shadow-xl border-l border-[#E8E0D4]`
- Side panel header: `bg-gradient-to-r from-emerald-600 to-teal-600` → `bg-[#8B9E6B]`
- `text-gray-900` in hero → `text-[#3D3229]`
- `text-gray-600` in hero → `text-[#9C8E82]`
- `bg-black/20` backdrop → `bg-[#3D3229]/15`
- Side panel `bg-white/20` spinner box → `bg-white/25`
- Side panel `text-white/80` → `text-white/85`

**Step 3: Remove emojis from mapper functions**

In `mapV6EventToProgress`: remove emoji prepend, just pass `message` straight through.
In `mapDayPlanEventToProgress`: same.
In `mapItineraryEventToProgress`: same.

Delete the module-level `*_EMOJIS` constants.

**Step 4: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 5: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat(ui): integrate phase stepper, transitions, and warm styling in App.tsx"
```

---

### Task 7: Restyle Header Component

**Files:**
- Modify: `frontend/src/components/Header.tsx`

**Step 1: Replace gradient header with warm flat design**

Remove the gradient background and glass-strong class. Replace with:
- Background: `bg-[#FBF8F4]` with `border-b border-[#E8E0D4]`
- Logo icon: solid `bg-[#C97B5A]` circle with white icon
- Title text: `text-[#3D3229]` (warm charcoal)
- Remove gradient text styling and `headerGradients` import

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/components/Header.tsx
git commit -m "feat(ui): restyle Header with warm earth-tone flat design"
```

---

### Task 8: Redesign GenerationProgress Component

**Files:**
- Modify: `frontend/src/components/GenerationProgress.tsx`

This is the largest component (415 lines). Key changes:

**Step 1: Replace MODE_COLORS**

Replace the 3-mode color objects with earth-tone equivalents:
- Journey: terracotta (`bg-primary-100`, `text-primary-600`, etc.)
- Day-plans: sage (`bg-[#F5F7F0]`, `text-[#728556]`, etc.)
- Itinerary: stone (`bg-[#F7F5F2]`, `text-[#6E655B]`, etc.)

All gradient references → solid colors.

**Step 2: Restructure journey progress layout**

Replace vertical phase list with horizontal connected path. Replace emojis with simple dot indicators (terracotta active, sage completed, stone pending).

**Step 3: Replace progress bar**

Thick violet gradient bar → thin terracotta bar at top (`h-1 bg-[#C97B5A]`).

**Step 4: Restyle city progress cards**

- Remove gradient card backgrounds → parchment surface (`bg-[#F5F0E8]`)
- Replace violet/emerald badges → earth-tone palette cycling
- Replace spinner animation colors

**Step 5: Restyle cancel button**

Remove red/danger styling → warm secondary: `bg-white border border-[#E8E0D4] text-[#3D3229] hover:bg-[#F5F0E8]`

**Step 6: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 7: Commit**

```bash
git add frontend/src/components/GenerationProgress.tsx
git commit -m "feat(ui): redesign GenerationProgress with earth-tone horizontal journey path"
```

---

### Task 9: Restyle JourneyInputForm

**Files:**
- Modify: `frontend/src/components/JourneyInputForm.tsx`

**Step 1: Replace all violet/primary color references**

- `text-primary-400` icon colors → `text-[#C97B5A]`
- `focus:ring-primary-400/30 focus:border-primary-400` → `focus:ring-[#C97B5A]/20 focus:border-[#C97B5A]`
- `hover:bg-primary-50/50` → `hover:bg-primary-50`
- Selected interest: `bg-primary-100 text-primary-700 ring-primary-400/50` → `bg-primary-100 text-primary-700 ring-primary-400/40`
- Selected pace: same pattern
- Submit button: replace `headerGradients.journey.css` inline style → `className="bg-[#C97B5A] hover:bg-[#A66244]"`
- `backdrop-blur-xl` references → remove

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/components/JourneyInputForm.tsx
git commit -m "feat(ui): restyle JourneyInputForm with earth-tone warm inputs"
```

---

### Task 10: Restyle ItineraryInputForm

**Files:**
- Modify: `frontend/src/components/ItineraryInputForm.tsx`

**Step 1: Replace headerGradient inline styles**

All section card headers currently use inline `style={{ background: headerGradients.*.css }}`. Replace these with solid earth-tone backgrounds:
- Destination card header: `bg-[#8E8478]` (stone) with white text
- Dates card header: `bg-[#8B9E6B]` (sage) with white text
- Interests card header: `bg-[#D4A574]` (sand) with white text
- Pace card header: `bg-[#B07878]` (clay) with white text
- Submit button: `bg-[#C97B5A] hover:bg-[#A66244]` (solid terracotta)

Replace selected interest/pace chip styles with earth-tone active states.

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/components/ItineraryInputForm.tsx
git commit -m "feat(ui): restyle ItineraryInputForm with earth-tone card headers"
```

---

### Task 11: Restyle V6JourneyPlanView + CityCard

**Files:**
- Modify: `frontend/src/components/V6JourneyPlanView/index.tsx`
- Modify: `frontend/src/components/V6JourneyPlanView/CityCard.tsx`

**Step 1: V6JourneyPlanView/index.tsx**

- Header card: replace `headerGradients.journey.css` with `bg-[#C97B5A]` solid
- Stats: replace `color: headerGradients.journey.from` with `color: '#C97B5A'`
- Route pills: already palette-driven, will pick up new palettes from design-system.ts automatically
- Day section header: replace `headerGradients.dayPlan.css` with `bg-[#8B9E6B]` solid
- Action bar: replace `glass-strong` with `bg-[#F5F0E8] border border-[#E8E0D4]`
- Button: replace `bg-gradient-to-r from-primary-600 to-purple-600` with `bg-[#C97B5A] hover:bg-[#A66244]`

**Step 2: CityCard.tsx**

- Timeline marker: already palette-driven (auto-picks up new palettes)
- Header gradient: replace `linear-gradient(to right, ${palette.bgColor}, white)` → `backgroundColor: palette.bgColor` (flat, no gradient)
- Highlight badges: already style-driven (auto-picks up new categoryStyles)

**Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 4: Commit**

```bash
git add frontend/src/components/V6JourneyPlanView/index.tsx frontend/src/components/V6JourneyPlanView/CityCard.tsx
git commit -m "feat(ui): restyle V6JourneyPlanView and CityCard with earth tones"
```

---

### Task 12: Restyle TravelLegCard

**Files:**
- Modify: `frontend/src/components/V6JourneyPlanView/TravelLegCard.tsx`

**Step 1: Replace blue/indigo references with warm tones**

- Timeline vertical line: `bg-gradient-to-b from-gray-200 via-blue-300 to-gray-200` → `bg-[#E8E0D4]` (solid warm border)
- Card background: `from-blue-50/80 to-indigo-50/80 border border-blue-100/60` → `bg-[#FDF8F3] border border-[#E8E0D4]`
- Transport icon badge: replace `headerGradients.transport.css` → `bg-[#D4A574]` solid
- Date badge: `text-indigo-600 bg-indigo-50` → `text-[#A66244] bg-primary-50`
- Mode badge: `text-blue-600 bg-blue-100` → `text-[#8B9E6B] bg-[#F5F7F0]`
- Time badge: `bg-blue-50 text-blue-700` → `bg-[#F7F5F2] text-[#6E655B]`
- Arrow: `text-blue-400` → `text-[#9C8E82]`
- Compact card: replace gradient background with solid palette bgColor
- Fallback color: `#dbeafe` → `#FDF8F3`

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/components/V6JourneyPlanView/TravelLegCard.tsx
git commit -m "feat(ui): restyle TravelLegCard with warm earth-tone colors"
```

---

### Task 13: Restyle JourneyChat

**Files:**
- Modify: `frontend/src/components/JourneyChat.tsx`

**Step 1: Replace gradient-based chat styling**

- Chat button: replace gradient with solid `bg-[#C97B5A]` (journey) / `bg-[#8B9E6B]` (dayplan)
- Panel header: solid color instead of gradient — `bg-[#C97B5A]` or `bg-[#8B9E6B]`
- Remove `shadows.lg` / `shadows.xl` inline styles → use Tailwind `shadow-lg` / `shadow-xl`
- Messages area: `bg-gray-50/50` → `bg-[#FBF8F4]`
- User message bubble: terracotta tint `bg-primary-50 border border-[#EDCDB8]`
- AI message bubble: parchment `bg-[#F5F0E8] border border-[#E8E0D4]`
- Quick action buttons: remove gradient hover → `hover:bg-primary-50 hover:text-[#C97B5A]`
- Send button: solid `bg-[#C97B5A] hover:bg-[#A66244]`
- Input focus: `focus:ring-primary-400/30` → `focus:ring-[#C97B5A]/20 focus:border-[#C97B5A]`

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/components/JourneyChat.tsx
git commit -m "feat(ui): restyle JourneyChat with warm earth-tone messaging"
```

---

### Task 14: Restyle ItineraryView

**Files:**
- Modify: `frontend/src/components/ItineraryView/index.tsx`

**Step 1: Replace violet/gradient references**

- Header: `bg-gradient-to-r from-primary-600 via-purple-600 to-pink-500` → `bg-[#C97B5A]` solid
- Stats values: `text-primary-600` → `text-[#C97B5A]`
- Interest badges: already palette-driven (auto-picks up new `dayColorPalettes`)
- Day section header: `bg-gradient-to-r from-emerald-600 to-teal-600` → `bg-[#8B9E6B]` solid
- Glass effects in day header: remove `backdropFilter: 'blur(10px)'` and `rgba(255,255,255,0.2)` → simple `bg-white/30`
- Quality progress colors: keep the green/amber/red semantic colors (these are informational, not brand)
- Action bar: replace `glass-strong` → `bg-[#F5F0E8] border border-[#E8E0D4]`
- Button: replace gradient → `bg-[#C97B5A] hover:bg-[#A66244]`

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/components/ItineraryView/index.tsx
git commit -m "feat(ui): restyle ItineraryView with earth-tone warm design"
```

---

### Task 15: Final Verification + Cleanup

**Files:**
- All modified files

**Step 1: Full build check**

Run: `cd frontend && npm run build`
Expected: Zero errors, zero warnings related to missing imports

**Step 2: Grep for remaining violet/glass/mesh references**

```bash
cd frontend/src && grep -rn "glass\|bg-mesh\|purple-600\|violet-\|#7c3aed\|#6d28d9\|#8b5cf6\|#9333ea\|from-primary-600 to-purple" --include="*.tsx" --include="*.ts" --include="*.css"
```

Expected: No matches (all references replaced)

**Step 3: Visual spot-check**

Run: `cd frontend && npm run dev`
Open browser, navigate through all 4 phases to confirm:
- Earth-tone colors throughout
- No violet/purple remnants
- Stepper appears after leaving input phase
- Transitions animate between phases
- Back navigation works

**Step 4: Commit any missed fixes**

```bash
git add -A
git commit -m "fix(ui): clean up remaining old color references"
```

---

## Execution Order Summary

| Task | Description | Est. Scope | Dependencies |
|------|-------------|------------|--------------|
| 1 | Tailwind config | Small | None |
| 2 | Design system tokens | Large | Task 1 |
| 3 | index.css overhaul | Medium | Task 1 |
| 4 | PhaseIndicator component | Small | Task 3 |
| 5 | PhaseTransition component | Small | Task 3 |
| 6 | App.tsx integration | Large | Tasks 4, 5 |
| 7 | Header restyle | Small | Task 2 |
| 8 | GenerationProgress redesign | Large | Task 2 |
| 9 | JourneyInputForm restyle | Medium | Task 2 |
| 10 | ItineraryInputForm restyle | Medium | Task 2 |
| 11 | V6JourneyPlanView + CityCard | Medium | Task 2 |
| 12 | TravelLegCard restyle | Medium | Task 2 |
| 13 | JourneyChat restyle | Medium | Task 2 |
| 14 | ItineraryView restyle | Medium | Task 2 |
| 15 | Final verification | Small | All |

Tasks 7-14 are independent of each other (only depend on Task 2). They can be parallelized.
