/**
 * ActivityCard - Single activity display within a day plan
 */
import { memo } from 'react';
import { Clock, MapPin, Star } from 'lucide-react';
import type { V6Activity } from '@/types';
import { categoryStyles, getCategoryIcon, isMealActivity } from './styles';

interface ActivityCardProps {
  activity: V6Activity;
  isLast: boolean;
  index: number;
}

export const ActivityCard = memo(function ActivityCard({ activity, isLast, index }: ActivityCardProps) {
  const category = activity.place.category?.toLowerCase() || 'default';
  const style = categoryStyles[category] || categoryStyles.default;
  const isMeal = isMealActivity(category);
  
  return (
    <div className="flex gap-3 group" style={{ animationDelay: `${index * 50}ms` }}>
      {/* Timeline with colored accent */}
      <div className="flex flex-col items-center w-14 flex-shrink-0">
        <div 
          className="text-xs font-bold px-2.5 py-1.5 rounded-lg shadow-sm"
          style={{ 
            background: style.gradient,
            color: 'white',
            textShadow: '0 1px 2px rgba(0,0,0,0.1)'
          }}
        >
          {activity.time_start}
        </div>
        {!isLast && (
          <div 
            className="flex-1 w-0.5 my-2 rounded-full"
            style={{ background: `linear-gradient(to bottom, ${style.accent}40, ${style.accent}10)` }}
          />
        )}
      </div>

      {/* Activity content */}
      <div className={`flex-1 min-w-0 ${isLast ? '' : 'pb-3'}`}>
        <div 
          className="rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-all group-hover:translate-x-0.5"
          style={{ 
            background: 'white',
            border: `1px solid ${style.border}`,
          }}
        >
          {/* Colored top accent bar */}
          <div 
            className="h-1"
            style={{ background: style.gradient }}
          />
          
          <div className="p-3.5">
            {/* Header row */}
            <div className="flex items-start gap-3">
              {/* Category icon badge */}
              <div 
                className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm"
                style={{ 
                  background: style.gradient,
                  color: 'white'
                }}
              >
                {getCategoryIcon(category)}
              </div>
              
              <div className="flex-1 min-w-0">
                <h5 className="font-semibold text-gray-900 text-sm leading-tight">
                  {activity.place.name}
                </h5>
                
                {/* Meta row */}
                <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                  <span
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold capitalize"
                    style={{ 
                      backgroundColor: style.bg,
                      color: style.text,
                      border: `1px solid ${style.border}`
                    }}
                  >
                    {isMeal ? '🍽️' : ''} {category.replace('_', ' ')}
                  </span>
                  <span className="text-xs text-gray-500 flex items-center gap-1 font-medium">
                    <Clock className="h-3 w-3" />
                    {activity.duration_minutes} min
                  </span>
                  {activity.place.rating && (
                    <span className="text-xs text-gray-600 flex items-center gap-1 font-medium">
                      <Star className="h-3 w-3 text-amber-400 fill-amber-400" />
                      {activity.place.rating}
                    </span>
                  )}
                </div>
              </div>
            </div>
            
            {/* Address */}
            {activity.place.address && (
              <p className="mt-2.5 text-xs text-gray-500 flex items-center gap-1.5 pl-13">
                <MapPin className="h-3 w-3 flex-shrink-0" style={{ color: style.accent }} />
                <span className="truncate">{activity.place.address}</span>
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
});
