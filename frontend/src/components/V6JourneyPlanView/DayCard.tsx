/**
 * DayCard - Expandable card showing a single day's activities
 */
import { memo, useState } from 'react';
import { Calendar, ChevronDown, ChevronUp, Clock } from 'lucide-react';
import type { V6DayPlan } from '@/types';
import { categoryStyles, getCategoryIcon, type CityColorPalette } from './styles';
import { ActivityCard } from './ActivityCard';

interface DayCardProps {
  dayPlan: V6DayPlan;
  dayNumberInCity: number;
  palette: CityColorPalette;
}

export const DayCard = memo(function DayCard({ dayPlan, dayNumberInCity, palette }: DayCardProps) {
  const [expanded, setExpanded] = useState(false);
  
  // Get unique categories for preview icons
  const uniqueCategories = [...new Set(dayPlan.activities.map(a => a.place.category?.toLowerCase() || 'default'))].slice(0, 4);
  
  // Calculate time range
  const firstActivity = dayPlan.activities[0];
  const lastActivity = dayPlan.activities[dayPlan.activities.length - 1];
  const timeRange = firstActivity && lastActivity 
    ? `${firstActivity.time_start} - ${lastActivity.time_end || lastActivity.time_start}`
    : null;

  return (
    <div 
      className="rounded-xl overflow-hidden bg-white shadow-sm hover:shadow-md transition-all"
      style={{ border: `1px solid ${palette.borderColor}` }}
    >
      {/* Day Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 flex items-center justify-between hover:bg-gray-50/50 transition-colors"
        aria-expanded={expanded}
        aria-label={`Day ${dayNumberInCity}: ${dayPlan.theme}`}
      >
        <div className="flex items-center gap-4">
          <div 
            className="w-12 h-12 rounded-xl text-white flex items-center justify-center font-bold text-xl shadow-md"
            style={{ background: `linear-gradient(135deg, ${palette.gradientFrom}, ${palette.gradientTo})` }}
          >
            {dayNumberInCity}
          </div>
          <div className="text-left flex-1 min-w-0">
            <h4 className="font-bold text-gray-900 text-base line-clamp-1">{dayPlan.theme}</h4>
            <div className="flex items-center gap-2 text-xs text-gray-500 mt-1.5">
              <span className="flex items-center gap-1 font-medium" style={{ color: palette.textColor }}>
                <Calendar className="h-3.5 w-3.5" />
                {new Date(dayPlan.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
              </span>
              {timeRange && (
                <>
                  <span className="text-gray-300">•</span>
                  <span className="flex items-center gap-1 font-medium text-gray-600">
                    <Clock className="h-3.5 w-3.5" />
                    {timeRange}
                  </span>
                </>
              )}
            </div>
            {/* Activity category preview */}
            <div className="flex items-center gap-1.5 mt-2">
              {uniqueCategories.map((cat, i) => {
                const catStyle = categoryStyles[cat] || categoryStyles.default;
                return (
                  <div 
                    key={i}
                    className="w-6 h-6 rounded-lg flex items-center justify-center text-white shadow-sm"
                    style={{ background: catStyle.gradient }}
                    title={cat}
                  >
                    {getCategoryIcon(cat)}
                  </div>
                );
              })}
              <span className="text-xs text-gray-400 ml-1 font-medium">{dayPlan.activities.length} activities</span>
            </div>
          </div>
        </div>
        <div 
          className="p-2.5 rounded-xl transition-colors ml-3"
          style={{ backgroundColor: expanded ? palette.bgColor : '#f9fafb' }}
          >
          {expanded ? (
            <ChevronUp className="h-5 w-5" style={{ color: palette.accentColor }} />
          ) : (
            <ChevronDown className="h-5 w-5 text-gray-400" />
          )}
        </div>
      </button>

      {/* Activities */}
      {expanded && (
        <div 
          className="p-4"
          style={{ backgroundColor: palette.bgColor, borderTop: `1px solid ${palette.borderColor}` }}
        >
          <div className="space-y-0">
            {dayPlan.activities.map((activity, idx) => (
              <ActivityCard 
                key={idx} 
                activity={activity}
                isLast={idx === dayPlan.activities.length - 1}
                index={idx}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
});
