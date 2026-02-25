/**
 * DayCard - Expandable card showing a single day's activities
 * Uses the same color palette as city cards for visual consistency
 */
import { memo, useState } from 'react';
import { Calendar, ChevronDown, ChevronUp, Clock, Sparkles } from 'lucide-react';
import type { V6DayPlan } from '@/types';
import { categoryStyles, getCategoryIcon, cityColorPalettes } from './styles';
import { ActivityCard } from './ActivityCard';

interface DayCardProps {
  dayPlan: V6DayPlan;
  dayNumberInCity: number;
  paletteIndex: number;
  defaultExpanded?: boolean;
}

export const DayCard = memo(function DayCard({ 
  dayPlan, 
  dayNumberInCity, 
  paletteIndex,
  defaultExpanded = false,
}: DayCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const palette = cityColorPalettes[paletteIndex % cityColorPalettes.length];
  
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
    <div 
      className="rounded-xl overflow-hidden bg-white shadow-sm hover:shadow-md transition-all duration-200"
      style={{ border: `1px solid ${palette.borderColor}` }}
    >
      {/* Day Header with Light Gradient */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left"
        aria-expanded={expanded}
        aria-label={`Day ${dayNumberInCity}: ${dayPlan.theme}`}
      >
        <div 
          className="p-4"
          style={{ 
            background: `linear-gradient(to right, ${palette.bgColor}, white)`,
            borderBottom: expanded ? `1px solid ${palette.borderColor}` : 'none',
          }}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {/* Day number badge with accent gradient */}
              <div 
                className="w-11 h-11 rounded-xl flex items-center justify-center font-black text-lg shadow-md flex-shrink-0 text-white"
                style={{ background: `linear-gradient(135deg, ${palette.gradientFrom}, ${palette.gradientTo})` }}
              >
                {dayNumberInCity}
              </div>
              
              <div className="flex-1 min-w-0">
                {/* Theme */}
                <div className="flex items-center gap-2 mb-1">
                  <Sparkles className="h-4 w-4" style={{ color: palette.accentColor }} />
                  <h4 
                    className="text-lg font-bold tracking-tight line-clamp-1"
                    style={{ color: palette.textColor }}
                  >
                    {dayPlan.theme}
                  </h4>
                </div>
                
                {/* Date and time info */}
                <div className="flex items-center gap-2 text-sm font-medium">
                  <span 
                    className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs"
                    style={{ 
                      backgroundColor: `${palette.accentColor}15`,
                      color: palette.textColor,
                    }}
                  >
                    <Calendar className="h-3 w-3" />
                    {formattedDate}
                  </span>
                  {timeRange && (
                    <span 
                      className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs"
                      style={{ 
                        backgroundColor: `${palette.accentColor}15`,
                        color: palette.textColor,
                      }}
                    >
                      <Clock className="h-3 w-3" />
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
                <p className="text-xl font-bold" style={{ color: palette.textColor }}>
                  {dayPlan.activities.length}
                </p>
                <p className="text-xs uppercase tracking-wide text-gray-500">activities</p>
              </div>
              
              <div 
                className="p-2 rounded-xl transition-colors"
                style={{ 
                  backgroundColor: `${palette.accentColor}15`,
                  color: palette.textColor,
                }}
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
            <div 
              className="flex items-center gap-1.5 mt-3 pt-3"
              style={{ borderTop: `1px solid ${palette.borderColor}` }}
            >
              {uniqueCategories.map((cat, i) => {
                const catStyle = categoryStyles[cat] || categoryStyles.default;
                return (
                  <div 
                    key={i}
                    className="w-6 h-6 rounded-md flex items-center justify-center text-white shadow-sm"
                    style={{ background: catStyle.gradient }}
                    title={cat.charAt(0).toUpperCase() + cat.slice(1)}
                  >
                    {getCategoryIcon(cat)}
                  </div>
                );
              })}
              <span className="text-xs ml-2 font-medium text-gray-500">
                {dayPlan.activities.length} activities planned
              </span>
            </div>
          )}
        </div>
      </button>

      {/* Activities */}
      {expanded && (
        <div className="p-4 bg-gray-50/50">
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
