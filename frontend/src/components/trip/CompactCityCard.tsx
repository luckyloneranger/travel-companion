import { useState } from 'react';
import { MapPin, Star, Sparkles, ChevronDown, Clock, Navigation, ArrowRight, Car, Train, Bus, Plane, Ship } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { DayTimeline } from '@/components/trip/DayTimeline';
import type { CityStop, TravelLeg, DayPlan } from '@/types';

interface CompactCityCardProps {
  city: CityStop;
  index: number;
  departureLeg?: TravelLeg;
  dayPlans?: DayPlan[];
  tips?: Record<string, string>;
  defaultExpanded?: boolean;
}

const TRANSPORT_ICONS: Record<string, typeof Car> = {
  drive: Car, train: Train, bus: Bus, flight: Plane, ferry: Ship,
};

function formatDuration(hours: number): string {
  if (hours < 1) return `${Math.round(hours * 60)} min`;
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

export function CompactCityCard({ city, index, departureLeg, dayPlans, tips = {}, defaultExpanded = false }: CompactCityCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const estimatedCost = (() => {
    let cost = 0;
    if (city.accommodation?.estimated_nightly_usd) {
      cost += city.accommodation.estimated_nightly_usd * city.days;
    }
    if (departureLeg?.fare_usd) {
      cost += departureLeg.fare_usd;
    }
    return cost > 0 ? cost : null;
  })();

  return (
    <div className="rounded-lg border border-border-default bg-surface overflow-hidden">
      <Collapsible open={expanded} onOpenChange={setExpanded}>
        {/* Compact header */}
        <CollapsibleTrigger asChild>
          <button
            type="button"
            className="w-full text-left px-4 py-3 hover:bg-surface-muted/50 transition-colors"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3 min-w-0 flex-1">
                <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/40 text-xs font-bold text-primary-700 dark:text-primary-300 shrink-0 mt-0.5">
                  {index + 1}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-text-primary break-words">
                      {city.name}, {city.country}
                    </h3>
                    <span className="text-xs text-text-muted shrink-0">
                      {city.days} {city.days === 1 ? 'day' : 'days'}
                    </span>
                  </div>

                  {/* Top 3 highlights */}
                  {city.highlights.length > 0 && (
                    <div className="mt-1.5 space-y-0.5">
                      {city.highlights.slice(0, 3).map((h) => (
                        <p key={h.name} className="text-xs text-text-secondary flex items-center gap-1">
                          <Sparkles className="h-3 w-3 text-accent-400 shrink-0" />
                          {h.name}
                        </p>
                      ))}
                    </div>
                  )}

                  {/* Accommodation + cost */}
                  {city.accommodation && (
                    <div className="mt-1.5 flex items-center gap-2 text-xs text-text-muted">
                      <MapPin className="h-3 w-3 shrink-0" />
                      <span className="break-words">{city.accommodation.name}</span>
                      {city.accommodation.estimated_nightly_usd && (
                        <span className="shrink-0">${city.accommodation.estimated_nightly_usd}/n</span>
                      )}
                    </div>
                  )}
                </div>
              </div>

              <div className="flex flex-col items-end gap-1 shrink-0">
                {estimatedCost && (
                  <span className="text-sm font-semibold text-text-primary">~${Math.round(estimatedCost)}</span>
                )}
                <ChevronDown className={`h-4 w-4 text-text-muted transition-transform ${expanded ? 'rotate-180' : ''}`} />
              </div>
            </div>
          </button>
        </CollapsibleTrigger>

        {/* Expanded details */}
        <CollapsibleContent>
          <div className="px-4 pb-4 pt-0 border-t border-border-default space-y-4">
            {/* Why visit */}
            {city.why_visit && (
              <p className="text-sm text-text-secondary leading-relaxed break-words mt-3">
                {city.why_visit}
              </p>
            )}

            {/* Full highlights */}
            {city.highlights.length > 0 && (
              <div className="space-y-1.5">
                <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider">Highlights</h4>
                {city.highlights.map((h) => (
                  <div key={h.name} className="flex flex-wrap items-start justify-between gap-x-2 gap-y-1 text-xs">
                    <div className="min-w-0 flex-1">
                      <span className="font-medium text-text-primary">{h.name}</span>
                      {h.description && <span className="text-text-muted"> — {h.description}</span>}
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      {h.suggested_duration_hours && <span className="text-text-muted">~{h.suggested_duration_hours}h</span>}
                      <Badge variant="secondary" className="text-xs capitalize">{h.category}</Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Accommodation detail */}
            {city.accommodation && (
              <div className="flex items-center gap-3 rounded-md border border-accent-200 dark:border-accent-500/30 bg-accent-50/30 dark:bg-accent-500/10 p-3">
                {city.accommodation.photo_url && (
                  <img
                    src={city.accommodation.photo_url}
                    alt={city.accommodation.name}
                    loading="lazy"
                    className="h-14 w-14 rounded-md object-cover shrink-0"
                  />
                )}
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-text-primary break-words">{city.accommodation.name}</p>
                  {city.accommodation.address && (
                    <p className="text-xs text-text-muted break-words">{city.accommodation.address}</p>
                  )}
                  <div className="flex items-center gap-2 mt-1 text-xs text-text-muted">
                    {city.accommodation.rating && (
                      <span className="flex items-center gap-0.5">
                        <Star className="h-3 w-3 fill-accent-400 text-accent-400" />
                        {city.accommodation.rating.toFixed(1)}
                      </span>
                    )}
                    {city.accommodation.estimated_nightly_usd && (
                      <span>${city.accommodation.estimated_nightly_usd}/night</span>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Transport leg detail */}
            {departureLeg && (() => {
              const TransportIcon = TRANSPORT_ICONS[departureLeg.mode] ?? Car;
              return (
                <div className="flex items-center gap-3 rounded-md bg-surface-dim px-3 py-2.5 text-xs">
                  <TransportIcon className="h-4 w-4 text-text-muted shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5 font-medium text-text-primary">
                      <span>{departureLeg.from_city}</span>
                      <ArrowRight className="h-3 w-3 text-text-muted shrink-0" />
                      <span>{departureLeg.to_city}</span>
                    </div>
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 mt-0.5 text-text-muted">
                      <span className="capitalize">{departureLeg.mode}</span>
                      <span className="flex items-center gap-0.5"><Clock className="h-3 w-3" />{formatDuration(departureLeg.duration_hours)}</span>
                      {departureLeg.distance_km != null && (
                        <span className="flex items-center gap-0.5"><Navigation className="h-3 w-3" />{departureLeg.distance_km.toFixed(0)} km</span>
                      )}
                      {departureLeg.fare && <span>{departureLeg.fare}</span>}
                    </div>
                    {departureLeg.notes && <p className="text-text-muted mt-1 break-words">{departureLeg.notes}</p>}
                    {departureLeg.booking_tip && <p className="text-primary-600 dark:text-primary-400 mt-0.5 break-words">Tip: {departureLeg.booking_tip}</p>}
                  </div>
                </div>
              );
            })()}

            {/* Inline day plans for this city */}
            {dayPlans && dayPlans.length > 0 && (
              <div className="space-y-4 pt-2 border-t border-border-default">
                <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider">Day-by-Day Itinerary</h4>
                {dayPlans.map((dp) => (
                  <div key={dp.day_number} className="space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-600 text-xs font-bold text-white shrink-0">
                        {dp.day_number}
                      </span>
                      <span className="text-sm font-medium text-text-primary">{dp.theme}</span>
                      {dp.daily_cost_usd != null && dp.daily_cost_usd > 0 && (
                        <span className="text-xs text-text-muted ml-auto">~${dp.daily_cost_usd.toFixed(0)}</span>
                      )}
                    </div>
                    <DayTimeline dayPlan={dp} tips={tips} />
                  </div>
                ))}
              </div>
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}
