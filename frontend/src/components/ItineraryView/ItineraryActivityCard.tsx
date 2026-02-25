/**
 * ItineraryActivityCard - Single activity display within a day plan
 * Matches V6JourneyPlanView design language
 */
import { memo } from 'react';
import { Clock, MapPin, Star, Navigation, ExternalLink } from 'lucide-react';
import type { Activity } from '@/types/itinerary';
import { categoryStyles, getCategoryIcon, isMealActivity, formatDuration } from './styles';

interface ItineraryActivityCardProps {
  activity: Activity;
  isLast: boolean;
  index: number;
}

export const ItineraryActivityCard = memo(function ItineraryActivityCard({ 
  activity, 
  isLast, 
  index 
}: ItineraryActivityCardProps) {
  const category = activity.place.category?.toLowerCase() || 'default';
  const style = categoryStyles[category] || categoryStyles.default;
  const isMeal = isMealActivity(category);

  return (
    <div 
      className="flex gap-3 group animate-fadeIn" 
      style={{ animationDelay: `${index * 50}ms` }}
    >
      {/* Timeline with colored accent */}
      <div className="flex flex-col items-center w-16 flex-shrink-0">
        <div 
          className="text-xs font-bold px-2.5 py-1.5 rounded-lg shadow-sm whitespace-nowrap"
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
            className="flex-1 w-0.5 my-2 rounded-full min-h-[2rem]"
            style={{ background: `linear-gradient(to bottom, ${style.accent}40, ${style.accent}10)` }}
          />
        )}
      </div>

      {/* Activity content */}
      <div className={`flex-1 min-w-0 ${isLast ? '' : 'pb-4'}`}>
        <div 
          className="rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-all duration-200 group-hover:translate-x-0.5"
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
          
          <div className="p-4">
            {/* Header row */}
            <div className="flex items-start gap-3">
              {/* Category icon badge */}
              <div 
                className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm"
                style={{ 
                  background: style.gradient,
                  color: 'white'
                }}
              >
                {getCategoryIcon(category)}
              </div>
              
              <div className="flex-1 min-w-0">
                <h5 className="font-semibold text-gray-900 text-base leading-tight line-clamp-2">
                  {activity.place.name}
                </h5>
                
                {/* Meta row */}
                <div className="flex items-center gap-2 mt-2 flex-wrap">
                  <span
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold capitalize"
                    style={{ 
                      backgroundColor: style.bg,
                      color: style.text,
                      border: `1px solid ${style.border}`
                    }}
                  >
                    {isMeal && '🍽️'} {category.replace(/_/g, ' ')}
                  </span>
                  <span className="text-xs text-gray-500 flex items-center gap-1.5 font-medium bg-gray-50 px-2 py-1 rounded-full">
                    <Clock className="h-3 w-3" />
                    {formatDuration(activity.duration_minutes)}
                  </span>
                  {activity.place.rating && (
                    <span className="text-xs text-gray-600 flex items-center gap-1 font-medium bg-amber-50 px-2 py-1 rounded-full">
                      <Star className="h-3 w-3 text-amber-400 fill-amber-400" />
                      {activity.place.rating.toFixed(1)}
                    </span>
                  )}
                </div>
              </div>
            </div>
            
            {/* Notes */}
            {activity.notes && (
              <p className="mt-3 text-sm text-gray-600 leading-relaxed pl-14">
                {activity.notes}
              </p>
            )}
            
            {/* Address & Links */}
            <div className="mt-3 flex items-center gap-3 pl-14 flex-wrap">
              {activity.place.address && (
                <p className="text-xs text-gray-500 flex items-center gap-1.5">
                  <MapPin className="h-3.5 w-3.5 flex-shrink-0" style={{ color: style.accent }} />
                  <span className="truncate max-w-xs">{activity.place.address}</span>
                </p>
              )}
              {activity.place.website && (
                <a 
                  href={activity.place.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-primary-600 hover:text-primary-700 flex items-center gap-1 font-medium"
                >
                  <ExternalLink className="h-3 w-3" />
                  Website
                </a>
              )}
            </div>
            
            {/* Route to next */}
            {activity.route_to_next && (
              <div 
                className="mt-3 pt-3 border-t flex items-center gap-2 text-xs text-gray-500"
                style={{ borderColor: style.border }}
              >
                <Navigation className="h-3.5 w-3.5" style={{ color: style.accent }} />
                <span className="font-medium">{activity.route_to_next.duration_text}</span>
                <span className="text-gray-400">•</span>
                <span>{(activity.route_to_next.distance_meters / 1000).toFixed(1)} km</span>
                <span className="text-gray-400">•</span>
                <span className="capitalize">{activity.route_to_next.travel_mode.toLowerCase()}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
});
