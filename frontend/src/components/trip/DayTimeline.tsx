import {
  Clock, Star, MapPin, Navigation, ExternalLink, DollarSign,
  CloudRain, Lightbulb, Cloud, CloudLightning, Snowflake,
  Droplets, Wind, Sun, Coffee, MessageSquare, Minus, Plus, Trash2, HelpCircle,
  GripVertical,
} from 'lucide-react';
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Badge } from '@/components/ui/badge';
import type { DayPlan, Activity } from '@/types';

interface DayTimelineProps {
  dayPlan: DayPlan;
  tips: Record<string, string>;
  onChatAbout?: (activityName: string, dayNumber: number) => void;
  onRemoveActivity?: (dayNumber: number, activityId: string) => void;
  onAdjustDuration?: (dayNumber: number, activityId: string, change: number) => void;
  onReorder?: (dayNumber: number, activityIds: string[]) => void;
  recentChanges?: {
    added: Set<string>;
    modified: Set<string>;
    removed: string[];
  } | null;
}

// ── Helper functions ───────────────────────────────────────

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

function getMinutesBetween(endTime: string, startTime: string): number {
  const [eh, em] = endTime.split(':').map(Number);
  const [sh, sm] = startTime.split(':').map(Number);
  return (sh * 60 + sm) - (eh * 60 + em);
}

// ── Feature 8: Weather Icon ────────────────────────────────

function WeatherIcon({ condition }: { condition: string }) {
  const c = condition.toLowerCase();
  if (c.includes('rain') || c.includes('shower')) return <CloudRain className="h-5 w-5 text-primary-500" />;
  if (c.includes('cloud') || c.includes('overcast')) return <Cloud className="h-5 w-5 text-text-muted" />;
  if (c.includes('snow')) return <Snowflake className="h-5 w-5 text-primary-300" />;
  if (c.includes('thunder') || c.includes('storm')) return <CloudLightning className="h-5 w-5 text-accent-500" />;
  return <Sun className="h-5 w-5 text-accent-400" />;
}

// ── Feature 10: Time Gap ───────────────────────────────────

function TimeGap({ minutes }: { minutes: number }) {
  if (minutes <= 60) return null;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  const label = h > 0 ? `${h}h ${m > 0 ? `${m}m` : ''}` : `${m}m`;
  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center w-16 shrink-0">
        <div className="w-px flex-1 bg-border-default border-dashed" />
      </div>
      <div className="flex-1 py-2">
        <div className="flex items-center gap-2 rounded-lg border border-dashed border-primary-200 dark:border-primary-800 bg-primary-50/50 dark:bg-primary-950/20 px-3 py-2">
          <Coffee className="h-4 w-4 text-primary-400" />
          <span className="text-xs text-primary-600 dark:text-primary-400">
            Free time: {label} — explore the area or rest
          </span>
        </div>
      </div>
    </div>
  );
}

// ── Feature 11: "Why this place?" tooltip ─────────────────

function getWhyThisPlace(activity: Activity, dayTheme?: string): string {
  const reasons: string[] = [];

  // Rating-based reasoning
  if (activity.place.rating) {
    if (activity.place.rating >= 4.5) reasons.push(`Highly rated (${activity.place.rating.toFixed(1)}/5)`);
    else if (activity.place.rating >= 4.0) reasons.push(`Well-reviewed (${activity.place.rating.toFixed(1)}/5)`);
  }

  // Category match to theme
  if (dayTheme) {
    const cat = (activity.place.category || '').toLowerCase();
    const theme = dayTheme.toLowerCase();
    if (theme.includes(cat) || cat.includes('museum') && theme.includes('art') ||
        cat.includes('temple') && (theme.includes('heritage') || theme.includes('culture')) ||
        cat.includes('restaurant') && theme.includes('food') ||
        cat.includes('park') && theme.includes('nature')) {
      reasons.push(`Matches today's "${dayTheme}" theme`);
    }
  }

  // Category explanation
  const catDescriptions: Record<string, string> = {
    museum: 'Cultural landmark worth visiting',
    restaurant: 'Popular local dining spot',
    cafe: 'Great spot for a break',
    park: 'Green space for relaxation',
    temple: 'Significant cultural site',
    church: 'Architectural & historical landmark',
    tourist_attraction: 'Must-see attraction',
    historical_landmark: 'Important historical site',
    art_gallery: 'Notable art collection',
    monument: 'Iconic landmark',
  };
  const cat = (activity.place.category || '').toLowerCase();
  for (const [key, desc] of Object.entries(catDescriptions)) {
    if (cat.includes(key)) {
      reasons.push(desc);
      break;
    }
  }

  // Cost value
  if (activity.estimated_cost_usd === 0) reasons.push('Free entry');
  else if (activity.estimated_cost_usd != null && activity.estimated_cost_usd < 10) reasons.push('Budget-friendly');

  return reasons.length > 0 ? reasons.join(' · ') : 'Selected based on location and interests';
}

// ── Feature 9: Sortable Activity Wrapper ──────────────────

function SortableActivity({ id, children }: { id: string; children: React.ReactNode }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };
  return (
    <div ref={setNodeRef} style={style} {...attributes}>
      <div className="flex items-start gap-1">
        <button
          type="button"
          className="mt-4 p-1 cursor-grab active:cursor-grabbing text-text-muted/40 hover:text-text-muted transition-colors touch-none"
          aria-label="Drag to reorder"
          {...listeners}
        >
          <GripVertical className="h-5 w-5" />
        </button>
        <div className="flex-1">{children}</div>
      </div>
    </div>
  );
}

// ── Timeline Activity ──────────────────────────────────────

function TimelineActivity({
  activity,
  tip,
  isLast,
  onChatAbout,
  onRemoveActivity,
  onAdjustDuration,
  dayNumber,
  dayTheme,
  recentChanges,
}: {
  activity: Activity;
  tip?: string;
  isLast: boolean;
  onChatAbout?: (activityName: string, dayNumber: number) => void;
  onRemoveActivity?: (dayNumber: number, activityId: string) => void;
  onAdjustDuration?: (dayNumber: number, activityId: string, change: number) => void;
  dayNumber: number;
  dayTheme?: string;
  recentChanges?: {
    added: Set<string>;
    modified: Set<string>;
    removed: string[];
  } | null;
}) {
  if (activity.duration_minutes === 0) return null;

  const isNew = recentChanges?.added.has(activity.place.place_id);

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
        <div className={`rounded-lg border ${isNew ? 'border-green-400 dark:border-green-600 ring-1 ring-green-200 dark:ring-green-800' : 'border-border-default'} bg-surface p-3 space-y-2`}>
          {/* Activity photo */}
          {activity.place.photo_urls && activity.place.photo_urls.length > 0 && (
            <div className="flex gap-1.5 overflow-x-auto -mx-1 px-1">
              {activity.place.photo_urls.slice(0, 3).map((url, i) => (
                <img
                  key={i}
                  src={`${url}${url.includes('?') ? '&' : '?'}w=400`}
                  alt={`${activity.place.name} photo ${i + 1}`}
                  loading="lazy"
                  className="h-20 w-28 sm:h-24 sm:w-32 rounded-md object-cover shrink-0"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                />
              ))}
            </div>
          )}

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
                <button
                  type="button"
                  className="text-text-muted/50 hover:text-primary-500 transition-colors"
                  title={getWhyThisPlace(activity, dayTheme)}
                  aria-label="Why this place?"
                >
                  <HelpCircle className="h-3.5 w-3.5" />
                </button>
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
            <div className="flex items-center gap-1.5 shrink-0">
              {/* Quick edit actions */}
              <div className="flex items-center gap-0.5">
                {onAdjustDuration && (
                  <>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); onAdjustDuration(dayNumber, activity.id, -15); }}
                      className="text-text-muted hover:text-primary-600 transition-colors p-1.5"
                      title="Shorten by 15 min"
                      aria-label="Shorten duration"
                    >
                      <Minus className="h-3 w-3" />
                    </button>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); onAdjustDuration(dayNumber, activity.id, 15); }}
                      className="text-text-muted hover:text-primary-600 transition-colors p-1.5"
                      title="Extend by 15 min"
                      aria-label="Extend duration"
                    >
                      <Plus className="h-3 w-3" />
                    </button>
                  </>
                )}
                {onRemoveActivity && (
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); onRemoveActivity(dayNumber, activity.id); }}
                    className="text-text-muted hover:text-red-500 transition-colors p-1.5"
                    title="Remove activity"
                    aria-label="Remove activity"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                )}
              </div>
              {isNew && (
                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 font-medium">
                  New
                </span>
              )}
              {/* Feature 19: Contextual Chat button */}
              {onChatAbout && (
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); onChatAbout(activity.place.name, dayNumber); }}
                  className="text-text-muted hover:text-primary-600 transition-colors shrink-0"
                  aria-label={`Chat about ${activity.place.name}`}
                  title={`Edit ${activity.place.name}`}
                >
                  <MessageSquare className="h-4 w-4" />
                </button>
              )}
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
          </div>

          {/* Address + Get Directions */}
          {activity.place.address && (
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <p className="flex items-center gap-1.5 text-sm text-text-muted">
                <MapPin className="h-3.5 w-3.5 shrink-0" />
                <span className="break-words">{activity.place.address}</span>
              </p>
              {/* Feature 11: Get Directions button */}
              {activity.place.location && (
                <a
                  href={`https://www.google.com/maps/dir/?api=1&destination=${activity.place.location.lat},${activity.place.location.lng}&destination_place_id=${activity.place.place_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-primary-600 dark:text-primary-400 hover:underline"
                >
                  <Navigation className="h-3 w-3" />Get Directions
                </a>
              )}
            </div>
          )}

          {/* Notes */}
          {activity.notes && (
            <p className="text-sm text-text-secondary break-words leading-relaxed">{activity.notes}</p>
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
          <div className="mt-2 ml-1 flex flex-wrap items-center gap-2 text-sm text-text-muted">
            <Navigation className="h-3.5 w-3.5 shrink-0" />
            <TravelModeLabel mode={activity.route_to_next.travel_mode} />
            <span>&middot;</span>
            <span>{formatDistance(activity.route_to_next.distance_meters)}</span>
            <span>&middot;</span>
            <span>{formatDuration(activity.route_to_next.duration_seconds)}</span>
            {/* Feature 17: Walking route preview */}
            {activity.route_to_next.travel_mode === 'WALK' && activity.route_to_next.distance_meters > 0 && (
              <span className="text-text-muted/70">
                ~{Math.round(activity.route_to_next.distance_meters / 0.75).toLocaleString()} steps · ~{Math.round(activity.route_to_next.distance_meters * 0.05)} cal
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────

export function DayTimeline({ dayPlan, tips, onChatAbout, onRemoveActivity, onAdjustDuration, onReorder, recentChanges }: DayTimelineProps) {
  // ── Feature 9: Drag-and-drop sensors and handler ──
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  );

  const visibleActivities = dayPlan.activities.filter(a => a.duration_minutes > 0);

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id || !onReorder) return;
    const oldIndex = visibleActivities.findIndex(a => a.id === active.id);
    const newIndex = visibleActivities.findIndex(a => a.id === over.id);
    if (oldIndex === -1 || newIndex === -1) return;
    const reordered = [...visibleActivities];
    const [moved] = reordered.splice(oldIndex, 1);
    reordered.splice(newIndex, 0, moved);
    onReorder(dayPlan.day_number, reordered.map(a => a.id));
  };

  // Excursion day — simplified card rendering
  if (dayPlan.is_excursion) {
    return (
      <div className="rounded-lg border-2 border-accent-300 dark:border-accent-700 bg-accent-50 dark:bg-accent-950/30 p-4 space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">&#x1F3AF;</span>
          <h4 className="text-sm font-semibold text-text-primary">
            {dayPlan.excursion_name || dayPlan.theme}
          </h4>
        </div>
        {dayPlan.activities.length > 0 && dayPlan.activities[0].notes && (
          <p className="text-sm text-text-secondary leading-relaxed">
            {dayPlan.activities[0].notes}
          </p>
        )}
        {dayPlan.daily_cost_usd != null && dayPlan.daily_cost_usd > 0 && (
          <p className="text-sm text-text-muted flex items-center gap-1">
            <DollarSign className="h-3.5 w-3.5" />
            Estimated cost: ~${dayPlan.daily_cost_usd.toFixed(0)}
          </p>
        )}
        <p className="text-sm text-text-muted">
          Full-day experience &mdash; no individual activity scheduling
        </p>
      </div>
    );
  }

  if (visibleActivities.length === 0) {
    return (
      <p className="text-sm text-text-muted text-center py-8">No activities planned for this day.</p>
    );
  }

  // ── Activity list rendering helper ──
  const renderActivityList = () =>
    visibleActivities.map((activity, i) => {
      const gap = i > 0
        ? getMinutesBetween(visibleActivities[i - 1].time_end, activity.time_start)
        : 0;

      const activityElement = (
        <>
          {/* Feature 10: Time gap card */}
          {gap > 60 && <TimeGap minutes={gap} />}
          <TimelineActivity
            activity={activity}
            tip={tips[activity.place.place_id]}
            isLast={i === visibleActivities.length - 1}
            onChatAbout={onChatAbout}
            onRemoveActivity={onRemoveActivity}
            onAdjustDuration={onAdjustDuration}
            dayNumber={dayPlan.day_number}
            dayTheme={dayPlan.theme}
            recentChanges={recentChanges}
          />
        </>
      );

      if (onReorder) {
        return (
          <SortableActivity key={activity.id} id={activity.id}>
            {activityElement}
          </SortableActivity>
        );
      }

      return (
        <div key={activity.id}>
          {activityElement}
        </div>
      );
    });

  return (
    <div className="space-y-0">
      {/* Feature 8: Weather card */}
      {dayPlan.weather && (
        <div className="mb-4 rounded-lg border border-border-default bg-gradient-to-r from-sky-50 to-blue-50 dark:from-sky-950/20 dark:to-blue-950/20 p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <WeatherIcon condition={dayPlan.weather.condition} />
              <div>
                <p className="text-sm font-semibold text-text-primary">{dayPlan.weather.condition}</p>
                <p className="text-xs text-text-muted">
                  {dayPlan.weather.temperature_high_c.toFixed(0)}° / {dayPlan.weather.temperature_low_c.toFixed(0)}°C
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 text-xs text-text-muted">
              {dayPlan.weather.precipitation_chance_percent > 0 && (
                <span className="flex items-center gap-1">
                  <Droplets className="h-3.5 w-3.5" />{dayPlan.weather.precipitation_chance_percent}%
                </span>
              )}
              {dayPlan.weather.wind_speed_kmh > 0 && (
                <span className="flex items-center gap-1">
                  <Wind className="h-3.5 w-3.5" />{dayPlan.weather.wind_speed_kmh.toFixed(0)} km/h
                </span>
              )}
              {dayPlan.weather.uv_index != null && (
                <span className="flex items-center gap-1">
                  <Sun className="h-3.5 w-3.5" />UV {dayPlan.weather.uv_index}
                </span>
              )}
            </div>
          </div>
          {dayPlan.weather.precipitation_chance_percent >= 50 && onChatAbout && (
            <button
              type="button"
              onClick={() => onChatAbout('Suggest indoor alternatives for rainy weather', dayPlan.day_number)}
              className="text-xs text-primary-600 dark:text-primary-400 hover:underline mt-1"
            >
              Suggest indoor alternatives
            </button>
          )}
        </div>
      )}

      {/* Activities with time gap detection — conditionally wrapped in DndContext */}
      {onReorder ? (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={visibleActivities.map(a => a.id)} strategy={verticalListSortingStrategy}>
            {renderActivityList()}
          </SortableContext>
        </DndContext>
      ) : (
        renderActivityList()
      )}
    </div>
  );
}
