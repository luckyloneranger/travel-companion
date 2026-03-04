import type { DayPlan } from '@/types';

interface DayNavProps {
  dayPlans: DayPlan[];
  activeDay: number;
  onDayClick: (dayNumber: number) => void;
}

export function DayNav({ dayPlans, activeDay, onDayClick }: DayNavProps) {
  return (
    <nav
      className="sticky top-0 z-10 bg-surface border-b border-border-default -mx-4 sm:-mx-6 px-4 sm:px-6 py-2 overflow-x-auto"
      aria-label="Day navigation"
    >
      <div className="flex gap-2 min-w-max">
        {dayPlans.map((dp) => {
          const isActive = dp.day_number === activeDay;
          return (
            <button
              key={dp.day_number}
              type="button"
              onClick={() => onDayClick(dp.day_number)}
              className={`flex flex-col items-center rounded-lg px-3 py-2 min-w-[72px] transition-colors ${
                isActive
                  ? 'bg-primary-600 text-white shadow-sm'
                  : 'bg-surface-muted text-text-secondary hover:bg-surface-dim'
              }`}
              aria-current={isActive ? 'true' : undefined}
            >
              <span className={`text-xs font-semibold ${isActive ? 'text-white' : 'text-text-primary'}`}>
                Day {dp.day_number}
              </span>
              <span className={`text-xs mt-0.5 ${isActive ? 'text-white/80' : 'text-text-muted'}`}>
                {dp.city_name}
              </span>
              {dp.daily_cost_usd != null && dp.daily_cost_usd > 0 && (
                <span className={`text-xs mt-0.5 ${isActive ? 'text-white/70' : 'text-text-muted'}`}>
                  ~${dp.daily_cost_usd.toFixed(0)}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
