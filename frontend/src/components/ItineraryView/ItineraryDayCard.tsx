/**
 * ItineraryDayCard - Expandable card showing a single day's activities
 */
import { memo, useState } from 'react';
import { Calendar, ChevronDown, ChevronUp, Clock, Sparkles } from 'lucide-react';
import type { DayPlan } from '@/types/itinerary';
import { dayColorPalettes, categoryStyles, getCategoryIcon, type DayColorPalette } from './styles';
import { ItineraryActivityCard } from './ItineraryActivityCard';

interface ItineraryDayCardProps {
  dayPlan: DayPlan;
  palette?: DayColorPalette;
}

export const ItineraryDayCard = memo(function ItineraryDayCard({
  dayPlan,
  palette = dayColorPalettes[0],
}: ItineraryDayCardProps) {
  const [expanded, setExpanded] = useState(true);

  // Get palette based on day number
  const dayPalette = dayColorPalettes[(dayPlan.day_number - 1) % dayColorPalettes.length];
  const activePalette = palette || dayPalette;

  // Get unique categories for preview icons
  const uniqueCategories = [...new Set(dayPlan.activities.map(a => a.place.category?.toLowerCase() || 'default'))].slice(0, 5);

  // Calculate time range
  const firstActivity = dayPlan.activities[0];
  const lastActivity = dayPlan.activities[dayPlan.activities.length - 1];
  const timeRange = firstActivity && lastActivity
    ? `${firstActivity.time_start} - ${lastActivity.time_end || lastActivity.time_start}`
    : null;

  // Format date
  const formattedDate = new Date(dayPlan.date).toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'short',
    day: 'numeric'
  });

  return (
    <div className="mb-5 last:mb-0">
      {/* Day Header */}
      <div
        className="rounded-2xl overflow-hidden shadow-md transition-all duration-300 hover:shadow-lg"
        style={{ border: `1px solid ${activePalette.borderColor}40` }}
      >
        {/* Gradient header */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full text-left"
          aria-expanded={expanded}
          aria-label={`Day ${dayPlan.day_number}: ${dayPlan.theme}`}
        >
          <div
            className="text-white p-5"
            style={{ background: `linear-gradient(135deg, ${activePalette.gradientFrom}, ${activePalette.gradientTo})` }}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                {/* Day number badge */}
                <div
                  className="w-14 h-14 rounded-2xl flex items-center justify-center font-display font-extrabold text-2xl shadow-lg bg-white/25"
                >
                  {dayPlan.day_number}
                </div>

                <div className="flex-1 min-w-0">
                  {/* Theme */}
                  <div className="flex items-center gap-2 mb-1">
                    <Sparkles className="h-4 w-4 opacity-80" />
                    <h3 className="text-xl font-display font-bold tracking-tight line-clamp-1" style={{ textShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
                      {dayPlan.theme}
                    </h3>
                  </div>

                  {/* Date and time info */}
                  <div className="flex items-center gap-2 text-sm font-medium" style={{ color: 'rgba(255,255,255,0.9)' }}>
                    <span className="flex items-center gap-1.5 bg-white/15 px-2.5 py-0.5 rounded-full text-xs">
                      <Calendar className="h-3.5 w-3.5" />
                      {formattedDate}
                    </span>
                    {timeRange && (
                      <span className="flex items-center gap-1.5 bg-white/15 px-2.5 py-0.5 rounded-full text-xs">
                        <Clock className="h-3.5 w-3.5" />
                        {timeRange}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Expand/collapse button and activity count */}
              <div className="flex items-center gap-3">
                {/* Activity count */}
                <div className="text-right hidden sm:block">
                  <p className="text-2xl font-display font-extrabold">{dayPlan.activities.length}</p>
                  <p className="text-xs opacity-80 uppercase tracking-wider font-medium">activities</p>
                </div>

                <div
                  className="p-2.5 rounded-xl transition-colors"
                  style={{ backgroundColor: 'rgba(255,255,255,0.12)' }}
                >
                  {expanded ? (
                    <ChevronUp className="h-5 w-5" />
                  ) : (
                    <ChevronDown className="h-5 w-5" />
                  )}
                </div>
              </div>
            </div>

            {/* Activity category preview when collapsed */}
            {!expanded && (
              <div className="flex items-center gap-2 mt-4 pt-4 border-t border-white/15">
                {uniqueCategories.map((cat, i) => {
                  const catStyle = categoryStyles[cat] || categoryStyles.default;
                  return (
                    <div
                      key={i}
                      className="w-8 h-8 rounded-lg flex items-center justify-center text-white shadow-sm"
                      style={{ background: catStyle.gradient }}
                      title={cat}
                    >
                      {getCategoryIcon(cat)}
                    </div>
                  );
                })}
                <span className="text-sm opacity-80 ml-2 font-medium">
                  {dayPlan.activities.length} activities planned
                </span>
              </div>
            )}
          </div>
        </button>

        {/* Activities */}
        {expanded && (
          <div
            className="p-5"
            style={{
              backgroundColor: activePalette.bgColor,
            }}
          >
            <div className="space-y-0">
              {dayPlan.activities.map((activity, idx) => (
                <ItineraryActivityCard
                  key={activity.id || idx}
                  activity={activity}
                  isLast={idx === dayPlan.activities.length - 1}
                  index={idx}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
});
