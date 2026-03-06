import { useState } from 'react';
import { MapPin, ChevronRight, X, Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { JourneyPlan, DayPlan } from '@/types';

interface NavigationSidebarProps {
  journey: JourneyPlan;
  dayPlans?: DayPlan[] | null;
  onSelectDay?: (dayNumber: number) => void;
}

export function NavigationSidebar({ journey, dayPlans, onSelectDay }: NavigationSidebarProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleDayClick = (dayNumber: number) => {
    if (onSelectDay) {
      onSelectDay(dayNumber);
    } else {
      document.getElementById(`day-${dayNumber}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    setIsOpen(false);
  };

  return (
    <>
      {/* Floating toggle button */}
      <Button
        variant="default"
        size="icon"
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 z-40 h-12 w-12 rounded-full shadow-lg lg:hidden"
        aria-label="Navigate trip"
      >
        {isOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </Button>

      {/* Navigation panel */}
      {isOpen && (
        <div className="fixed inset-0 z-30 lg:relative lg:inset-auto" onClick={() => setIsOpen(false)}>
          <div
            className="absolute right-4 bottom-20 w-72 max-h-[60vh] overflow-y-auto rounded-xl border border-border-default bg-surface shadow-2xl p-3 space-y-2 lg:sticky lg:top-20 lg:bottom-auto lg:right-auto lg:w-56 lg:shadow-sm"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider px-2">Trip Overview</h3>
            {journey.cities.map((city, ci) => {
              const cityDays = dayPlans?.filter(dp => dp.city_name.toLowerCase() === city.name.toLowerCase()) ?? [];
              return (
                <div key={ci} className="space-y-0.5">
                  <div className="flex items-center gap-2 px-2 py-1.5 rounded-md bg-surface-muted/50">
                    <MapPin className="h-3.5 w-3.5 text-primary-500 shrink-0" />
                    <span className="text-sm font-medium text-text-primary truncate">{city.name}</span>
                    <span className="text-xs text-text-muted ml-auto shrink-0">{city.days}d</span>
                  </div>
                  {cityDays.map(dp => (
                    <button
                      key={dp.day_number}
                      type="button"
                      onClick={() => handleDayClick(dp.day_number)}
                      className="w-full flex items-center gap-2 px-2 py-1 ml-4 rounded text-left hover:bg-primary-50 dark:hover:bg-primary-950/20 transition-colors group"
                    >
                      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/40 text-[10px] font-bold text-primary-700 dark:text-primary-300 shrink-0 group-hover:bg-primary-200">
                        {dp.day_number}
                      </span>
                      <span className="text-xs text-text-secondary truncate">{dp.theme}</span>
                      <ChevronRight className="h-3 w-3 text-text-muted/50 ml-auto shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </button>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </>
  );
}
