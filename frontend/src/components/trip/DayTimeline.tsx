import {
  Clock, Star, MapPin, Navigation, ExternalLink, DollarSign,
  CloudRain, Lightbulb,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import type { DayPlan, Activity } from '@/types';

interface DayTimelineProps {
  dayPlan: DayPlan;
  tips: Record<string, string>;
}

function TravelModeLabel({ mode }: { mode: string }) {
  const labels: Record<string, string> = { WALK: 'Walk', DRIVE: 'Drive', TRANSIT: 'Transit' };
  return <span>{labels[mode] || mode.toLowerCase()}</span>;
}

function formatDistance(meters: number): string {
  return meters < 1000 ? `${Math.round(meters)}m` : `${(meters / 1000).toFixed(1)}km`;
}

function formatDuration(seconds: number): string {
  const min = Math.round(seconds / 60);
  if (min < 60) return `${min} min`;
  const h = Math.floor(min / 60);
  const m = min % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function TimelineActivity({ activity, tip, isLast }: { activity: Activity; tip?: string; isLast: boolean }) {
  if (activity.duration_minutes === 0) return null;

  return (
    <div className="flex gap-3">
      {/* Time column */}
      <div className="flex flex-col items-center w-16 shrink-0">
        <span className="text-sm font-semibold text-primary-600 dark:text-primary-400">
          {activity.time_start}
        </span>
        {!isLast && <div className="w-px flex-1 bg-border-default mt-1" />}
      </div>

      {/* Content */}
      <div className="flex-1 pb-4 min-w-0">
        <div className="rounded-lg border border-border-default bg-surface p-3 space-y-2">
          {/* Name + meta */}
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <h4 className="text-sm font-semibold text-text-primary break-words">
                {activity.place.name}
              </h4>
              <div className="flex flex-wrap items-center gap-2 mt-1 text-sm text-text-muted">
                <span className="flex items-center gap-0.5">
                  <Clock className="h-3.5 w-3.5" />
                  {activity.time_start} – {activity.time_end} · {activity.duration_minutes} min
                </span>
                <Badge variant="outline" className="text-xs capitalize">{activity.place.category}</Badge>
                {activity.estimated_cost_usd != null && activity.estimated_cost_usd > 0 && (
                  <span className="flex items-center gap-0.5 font-medium">
                    <DollarSign className="h-3.5 w-3.5" />~${activity.estimated_cost_usd.toFixed(0)}
                  </span>
                )}
                {activity.place.rating && (
                  <span className="flex items-center gap-0.5">
                    <Star className="h-3.5 w-3.5 fill-accent-400 text-accent-400" />{activity.place.rating.toFixed(1)}
                  </span>
                )}
              </div>
            </div>
            {activity.place.website && (
              <a
                href={activity.place.website}
                target="_blank"
                rel="noopener noreferrer"
                className="text-text-muted hover:text-primary-600 transition-colors shrink-0"
                aria-label={`Visit ${activity.place.name} website`}
                onClick={(e) => e.stopPropagation()}
              >
                <ExternalLink className="h-4 w-4" />
              </a>
            )}
          </div>

          {/* Address */}
          {activity.place.address && (
            <p className="flex items-center gap-1.5 text-sm text-text-muted">
              <MapPin className="h-3.5 w-3.5 shrink-0" />
              <span className="break-words">{activity.place.address}</span>
            </p>
          )}

          {/* Notes */}
          {activity.notes && (
            <p className="text-sm text-text-secondary break-words leading-relaxed">{activity.notes}</p>
          )}

          {/* Photos */}
          {activity.place.photo_urls && activity.place.photo_urls.length > 0 && (
            <div className="flex gap-1.5 overflow-x-auto">
              {activity.place.photo_urls.map((url, i) => (
                <img key={i} src={url} alt={`${activity.place.name} photo ${i + 1}`} loading="lazy" className="h-20 w-24 rounded-md object-cover shrink-0" />
              ))}
            </div>
          )}

          {/* Weather warning */}
          {activity.weather_warning && (
            <div className="flex items-start gap-1.5 rounded-md bg-orange-50 dark:bg-orange-950/30 border border-orange-200 dark:border-orange-800 px-2.5 py-1.5">
              <CloudRain className="h-4 w-4 text-orange-500 mt-0.5 shrink-0" />
              <p className="text-sm text-orange-800 dark:text-orange-300 break-words">{activity.weather_warning}</p>
            </div>
          )}

          {/* Tip */}
          {tip && (
            <div className="flex items-start gap-1.5 rounded-md bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 px-2.5 py-1.5">
              <Lightbulb className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
              <p className="text-sm text-amber-800 dark:text-amber-300 break-words">{tip}</p>
            </div>
          )}
        </div>

        {/* Transport to next */}
        {activity.route_to_next && (
          <div className="mt-2 ml-1 flex items-center gap-2 text-sm text-text-muted">
            <Navigation className="h-3.5 w-3.5 shrink-0" />
            <TravelModeLabel mode={activity.route_to_next.travel_mode} />
            <span>&middot;</span>
            <span>{formatDistance(activity.route_to_next.distance_meters)}</span>
            <span>&middot;</span>
            <span>{formatDuration(activity.route_to_next.duration_seconds)}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export function DayTimeline({ dayPlan, tips }: DayTimelineProps) {
  const visibleActivities = dayPlan.activities.filter(a => a.duration_minutes > 0);

  if (visibleActivities.length === 0) {
    return (
      <p className="text-sm text-text-muted text-center py-8">No activities planned for this day.</p>
    );
  }

  return (
    <div className="space-y-0">
      {visibleActivities.map((activity, i) => (
        <TimelineActivity
          key={activity.id}
          activity={activity}
          tip={tips[activity.place.place_id]}
          isLast={i === visibleActivities.length - 1}
        />
      ))}
    </div>
  );
}
