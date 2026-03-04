import { useCallback, useEffect, useState } from 'react';
import { Compass, Moon, Sun, Check, PlusCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AuthButton } from '@/components/auth/AuthButton';
import { useTripStore } from '@/stores/tripStore';
import { useUIStore } from '@/stores/uiStore';

export function Header() {
  const [dark, setDark] = useState(() => {
    if (typeof window === 'undefined') return false;
    return document.documentElement.classList.contains('dark') ||
      (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches);
  });

  const journey = useTripStore((s) => s.journey);
  const tripId = useTripStore((s) => s.tripId);
  const phase = useUIStore((s) => s.phase);

  useEffect(() => {
    if (dark) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [dark]);

  const toggleDark = useCallback(() => setDark((d) => !d), []);

  const handleNewTrip = useCallback(() => {
    useTripStore.getState().reset();
    useUIStore.getState().resetUI();
  }, []);

  const handleGoHome = useCallback(() => {
    if (phase !== 'input') {
      // If viewing a trip, just navigate back to input — don't reset
      useUIStore.getState().setPhase('input');
    }
  }, [phase]);

  const showTripContext = phase === 'preview' && journey;
  const showNewTrip = phase === 'preview';

  return (
    <header className="border-b border-border-default bg-surface px-4 sm:px-6 py-3 sm:py-4">
      <div className="max-w-6xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          <button
            type="button"
            onClick={handleGoHome}
            className="flex items-center gap-2 sm:gap-3 min-w-0 hover:opacity-80 transition-opacity"
            title="Back to home"
          >
            <Compass className="h-5 w-5 sm:h-6 sm:w-6 text-primary-600 shrink-0" />
            <h1 className="text-lg sm:text-xl font-display font-bold text-text-primary truncate">
              Travel Companion
              {showTripContext && (
                <span className="text-text-muted font-normal text-sm sm:text-base">
                  {' · '}{journey.theme}
                </span>
              )}
            </h1>
          </button>
          {tripId && (
            <span className="hidden sm:flex items-center gap-0.5 text-xs text-green-600 dark:text-green-400 shrink-0">
              <Check className="h-3 w-3" /> Saved
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {showNewTrip && (
            <Button variant="ghost" size="sm" onClick={handleNewTrip} title="Start a new trip">
              <PlusCircle className="h-4 w-4" />
              <span className="hidden sm:inline">New Trip</span>
            </Button>
          )}
          <AuthButton />
          <Button variant="ghost" size="icon-sm" onClick={toggleDark} aria-label="Toggle dark mode">
            {dark ? <Sun className="h-4 w-4 text-text-muted" /> : <Moon className="h-4 w-4 text-text-muted" />}
          </Button>
        </div>
      </div>
    </header>
  );
}
