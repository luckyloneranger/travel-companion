import { useState, Suspense } from 'react';
import { MapPin, Star, Sparkles, ChevronDown, Clock, Navigation, ArrowRight, Car, Train, Bus, Plane, Ship, Map, X } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { DayTimeline } from '@/components/trip/DayTimeline';
import { DayMap } from '@/components/maps';
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

function parseFare(leg: TravelLeg): number {
  if (leg.fare_usd) return leg.fare_usd;
  if (leg.fare) {
    const match = leg.fare.match(/[\d.]+/);
    if (match) return parseFloat(match[0]);
  }
  return 0;
}

export function CompactCityCard({ city, index, departureLeg, dayPlans, tips = {}, defaultExpanded = false }: CompactCityCardProps) {
  const [showDayPlans, setShowDayPlans] = useState(defaultExpanded);
  const [mapDayPlan, setMapDayPlan] = useState<DayPlan | null>(null);

  // Complete per-city cost: accommodation + transport + day plan activities
  const estimatedCost = (() => {
    let cost = 0;
    if (city.accommodation?.estimated_nightly_usd) {
      cost += city.accommodation.estimated_nightly_usd * city.days;
    }
    if (departureLeg) {
      cost += parseFare(departureLeg);
    }
    if (dayPlans) {
      for (const dp of dayPlans) {
        if (dp.daily_cost_usd) cost += dp.daily_cost_usd;
      }
    }
    return cost > 0 ? cost : null;
  })();

  const hasDayPlans = dayPlans && dayPlans.length > 0;

  return (
    <div className="rounded-lg border border-border-default bg-surface overflow-hidden">
      {/* ── City Header (always visible) ──────────────────────── */}
      <div className="px-4 py-3">
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

              {/* Why visit — always visible */}
              {city.why_visit && (
                <p className="text-xs text-text-secondary mt-1 break-words leading-relaxed">
                  {city.why_visit}
                </p>
              )}
            </div>
          </div>

          {estimatedCost && (
            <span className="text-sm font-semibold text-text-primary shrink-0">~${Math.round(estimatedCost)}</span>
          )}
        </div>
      </div>

      {/* ── Highlights (always visible) ───────────────────────── */}
      {city.highlights.length > 0 && (
        <div className="px-4 pb-2 flex flex-wrap gap-x-3 gap-y-1">
          {city.highlights.map((h) => (
            <span key={h.name} className="text-xs text-text-secondary flex items-center gap-1">
              <Sparkles className="h-3 w-3 text-accent-400 shrink-0" />
              {h.name}
              {h.category && (
                <Badge variant="secondary" className="text-xs capitalize ml-0.5">{h.category}</Badge>
              )}
            </span>
          ))}
        </div>
      )}

      {/* ── Accommodation (always visible if exists) ──────────── */}
      {city.accommodation && (
        <div className="px-4 pb-2">
          <div className="flex items-center gap-3 rounded-md border border-accent-200 dark:border-accent-500/30 bg-accent-50/30 dark:bg-accent-500/10 p-2.5">
            {city.accommodation.photo_url && (
              <img
                src={city.accommodation.photo_url}
                alt={city.accommodation.name}
                loading="lazy"
                className="h-12 w-12 rounded-md object-cover shrink-0"
              />
            )}
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-text-primary break-words">{city.accommodation.name}</p>
              <div className="flex flex-wrap items-center gap-2 text-xs text-text-muted">
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
        </div>
      )}

      {/* ── Transport to next city (always visible if exists) ── */}
      {departureLeg && (() => {
        const TransportIcon = TRANSPORT_ICONS[departureLeg.mode] ?? Car;
        return (
          <div className="px-4 pb-3">
            <div className="flex items-center gap-2.5 rounded-md bg-surface-dim px-3 py-2 text-xs">
              <TransportIcon className="h-4 w-4 text-text-muted shrink-0" />
              <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-text-muted">
                <span className="font-medium text-text-primary">{departureLeg.from_city} → {departureLeg.to_city}</span>
                <span className="capitalize">{departureLeg.mode}</span>
                <span className="flex items-center gap-0.5"><Clock className="h-3 w-3" />{formatDuration(departureLeg.duration_hours)}</span>
                {departureLeg.distance_km != null && (
                  <span className="flex items-center gap-0.5"><Navigation className="h-3 w-3" />{departureLeg.distance_km.toFixed(0)} km</span>
                )}
                {departureLeg.fare && <span>{departureLeg.fare}</span>}
              </div>
            </div>
          </div>
        );
      })()}

      {/* ── Day Plans (collapsible — only this level expands) ── */}
      {hasDayPlans && (
        <Collapsible open={showDayPlans} onOpenChange={setShowDayPlans}>
          <div className="border-t border-border-default">
            <CollapsibleTrigger asChild>
              <button
                type="button"
                className="w-full flex items-center justify-between px-4 py-2.5 text-xs font-medium text-primary-600 dark:text-primary-400 hover:bg-surface-muted/50 transition-colors"
              >
                <span>
                  {showDayPlans ? 'Hide' : 'View'} Day-by-Day Itinerary ({dayPlans!.length} {dayPlans!.length === 1 ? 'day' : 'days'})
                </span>
                <ChevronDown className={`h-4 w-4 transition-transform ${showDayPlans ? 'rotate-180' : ''}`} />
              </button>
            </CollapsibleTrigger>

            <CollapsibleContent>
              <div className="px-4 pb-4 space-y-4">
                {dayPlans!.map((dp) => (
                  <div key={dp.day_number} className="space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-600 text-xs font-bold text-white shrink-0">
                        {dp.day_number}
                      </span>
                      <span className="text-sm font-medium text-text-primary">{dp.theme}</span>
                      <div className="flex items-center gap-1.5 ml-auto">
                        {dp.daily_cost_usd != null && dp.daily_cost_usd > 0 && (
                          <span className="text-xs text-text-muted">~${dp.daily_cost_usd.toFixed(0)}</span>
                        )}
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => setMapDayPlan(dp)}
                          title={`View Day ${dp.day_number} map`}
                        >
                          <Map className="h-4 w-4 text-text-muted" />
                        </Button>
                      </div>
                    </div>
                    <DayTimeline dayPlan={dp} tips={tips} />
                  </div>
                ))}
              </div>
            </CollapsibleContent>
          </div>
        </Collapsible>
      )}

      {/* ── Map Overlay ───────────────────────────────────────── */}
      {mapDayPlan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setMapDayPlan(null)}>
          <div
            className="relative w-[90vw] max-w-3xl h-[70vh] rounded-xl overflow-hidden bg-surface shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="absolute top-3 left-4 z-10 rounded-lg bg-surface/90 backdrop-blur-sm px-3 py-1.5 shadow-sm">
              <span className="text-sm font-semibold text-text-primary">
                Day {mapDayPlan.day_number}: {mapDayPlan.theme}
              </span>
            </div>
            <button
              type="button"
              onClick={() => setMapDayPlan(null)}
              className="absolute top-3 right-3 z-10 flex h-8 w-8 items-center justify-center rounded-full bg-surface/90 backdrop-blur-sm shadow-sm hover:bg-surface transition-colors"
              aria-label="Close map"
            >
              <X className="h-4 w-4 text-text-primary" />
            </button>
            <Suspense fallback={<div className="h-full w-full bg-surface-muted animate-pulse" />}>
              <DayMap dayPlan={mapDayPlan} />
            </Suspense>
          </div>
        </div>
      )}
    </div>
  );
}
