import { MapPin, Clock, Star, Hotel, Navigation } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import type { Activity } from '@/types';

interface ActivityCardProps {
  activity: Activity;
  index: number;
}

function TravelModeIcon({ mode }: { mode: string }) {
  switch (mode) {
    case 'WALK':
      return <Navigation className="h-3 w-3" />;
    case 'DRIVE':
      return <Navigation className="h-3 w-3 rotate-45" />;
    case 'TRANSIT':
      return <Navigation className="h-3 w-3 -rotate-45" />;
    default:
      return <Navigation className="h-3 w-3" />;
  }
}

function formatDistance(meters: number): string {
  if (meters < 1000) {
    return `${Math.round(meters)} m`;
  }
  return `${(meters / 1000).toFixed(1)} km`;
}

function formatDuration(seconds: number): string {
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) {
    return `${minutes} min`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
}

const isAccommodation = (category: string): boolean =>
  ['hotel', 'lodging', 'accommodation', 'hostel', 'resort'].some((key) =>
    category.toLowerCase().includes(key),
  );

export function ActivityCard({ activity, index }: ActivityCardProps) {
  const accommodation = isAccommodation(activity.place.category);

  return (
    <div className="flex gap-3">
      {/* Timeline marker */}
      <div className="flex flex-col items-center pt-1">
        <div
          className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
            accommodation
              ? 'bg-accent-100 text-accent-500'
              : 'bg-primary-100 text-primary-700'
          }`}
        >
          {accommodation ? (
            <Hotel className="h-3.5 w-3.5" />
          ) : (
            <span>{index + 1}</span>
          )}
        </div>
        {/* Vertical connector line */}
        <div className="w-px flex-1 bg-border-default mt-1" />
      </div>

      {/* Content */}
      <div
        className={`flex-1 pb-4 ${
          accommodation ? '' : ''
        }`}
      >
        <div
          className={`rounded-lg border p-3 ${
            accommodation
              ? 'bg-accent-50/50 border-accent-200'
              : 'bg-surface border-border-default'
          }`}
        >
          {/* Time range */}
          <div className="flex items-center gap-1.5 text-xs text-text-muted mb-1">
            <Clock className="h-3 w-3" />
            <span>
              {activity.time_start} - {activity.time_end}
            </span>
            <span className="text-border-default">|</span>
            <span>{activity.duration_minutes} min</span>
          </div>

          {/* Place name + category */}
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h4 className="text-sm font-semibold text-text-primary truncate">
                {activity.place.name}
              </h4>
              {activity.place.address && (
                <p className="text-xs text-text-muted flex items-center gap-1 mt-0.5 truncate">
                  <MapPin className="h-3 w-3 shrink-0" />
                  {activity.place.address}
                </p>
              )}
            </div>
            <div className="flex items-center gap-1.5 shrink-0">
              {activity.place.rating && (
                <span className="flex items-center gap-0.5 text-xs text-text-secondary">
                  <Star className="h-3 w-3 fill-accent-400 text-accent-400" />
                  {activity.place.rating.toFixed(1)}
                </span>
              )}
              <Badge variant="outline" className="text-[10px] capitalize">
                {activity.place.category}
              </Badge>
            </div>
          </div>

          {/* Notes */}
          {activity.notes && (
            <p className="text-xs text-text-secondary mt-1.5 leading-relaxed">
              {activity.notes}
            </p>
          )}
        </div>

        {/* Route to next */}
        {activity.route_to_next && (
          <div className="mt-1.5 ml-2 flex items-center gap-2 text-[11px] text-text-muted">
            <TravelModeIcon mode={activity.route_to_next.travel_mode} />
            <span>{formatDistance(activity.route_to_next.distance_meters)}</span>
            <span className="text-border-default">&middot;</span>
            <span>{formatDuration(activity.route_to_next.duration_seconds)}</span>
            <span className="text-border-default">&middot;</span>
            <span className="capitalize">
              {activity.route_to_next.travel_mode.toLowerCase()}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
