import { useState, Suspense } from 'react';
import { Star, Sparkles, ChevronDown, Clock, Navigation, Car, Train, Bus, Plane, Ship, Map, X, Loader2, ArrowRightLeft } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { DayTimeline } from '@/components/trip/DayTimeline';
import { DayMap, DayMapLegend } from '@/components/maps';
import type { CityStop, TravelLeg, DayPlan } from '@/types';
import { api } from '@/services/api';
import { showToast } from '@/components/ui/toast';

interface CompactCityCardProps {
  city: CityStop;
  index: number;
  departureLeg?: TravelLeg;
  dayPlans?: DayPlan[];
  tips?: Record<string, string>;
  defaultExpanded?: boolean;
  hideHighlights?: boolean;
  dailyBudget?: number;
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

export function CompactCityCard({ city, index, departureLeg, dayPlans, tips = {}, defaultExpanded = false, hideHighlights = false, dailyBudget, onChatAbout, onRemoveActivity, onAdjustDuration, onReorder, recentChanges }: CompactCityCardProps) {
  const [showDayPlans, setShowDayPlans] = useState(defaultExpanded);
  const [mapDayPlan, setMapDayPlan] = useState<DayPlan | null>(null);
  const [alternatives, setAlternatives] = useState<{ name: string; rating: number | null; price_level: number | null; place_id: string; photo_url: string | null }[]>([]);
  const [loadingAlts, setLoadingAlts] = useState(false);
  const [showAlts, setShowAlts] = useState(false);

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

  const handleShowAlternatives = async () => {
    if (alternatives.length > 0) {
      setShowAlts(!showAlts);
      return;
    }
    if (!city.accommodation?.place_id || !city.location) return;
    setLoadingAlts(true);
    try {
      const alts = await api.getAlternativeHotels(
        city.accommodation.place_id,
        city.location.lat,
        city.location.lng,
      );
      setAlternatives(alts);
      setShowAlts(true);
    } catch {
      showToast('Could not load alternative hotels', 'error');
    } finally {
      setLoadingAlts(false);
    }
  };

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
                <h3 className="text-base font-display font-semibold text-text-primary break-words">
                  {city.name}, {city.country}
                </h3>
                <span className="text-xs text-text-muted shrink-0">
                  {city.days} {city.days === 1 ? 'day' : 'days'}
                </span>
              </div>

              {/* Why visit — always visible */}
              {city.why_visit && (
                <p className="text-sm text-text-secondary mt-1 break-words leading-relaxed">
                  {city.why_visit}
                </p>
              )}
              {city.best_time_to_visit && (
                <p className="text-xs text-text-muted mt-0.5 flex items-center gap-1">
                  <Clock className="h-3 w-3 shrink-0" />
                  {city.best_time_to_visit}
                </p>
              )}
            </div>
          </div>

          {estimatedCost && (
            <span className="text-sm font-semibold text-text-primary shrink-0">~${Math.round(estimatedCost)}</span>
          )}
        </div>
      </div>

      {/* ── Highlights (unless hidden) ───────────────────────────── */}
      {!hideHighlights && city.highlights.length > 0 && (
        <div className="px-4 pb-2 flex flex-wrap gap-x-3 gap-y-1">
          {city.highlights.map((h) => (
            <span key={h.name} className="text-sm text-text-secondary flex items-center gap-1">
              <Sparkles className="h-3 w-3 text-accent-400 shrink-0" />
              {h.name}
              {h.category && (
                <Badge variant="outline" className="text-xs capitalize ml-0.5">{h.category}</Badge>
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
              <p className="text-sm font-medium text-text-primary break-words" title={city.accommodation.why || undefined}>{city.accommodation.name}</p>
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
          {city.accommodation.place_id && city.location && (
            <div className="mt-1.5 space-y-1.5">
              <button
                type="button"
                onClick={handleShowAlternatives}
                disabled={loadingAlts}
                className="text-xs text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1"
              >
                {loadingAlts ? (
                  <><Loader2 className="h-3 w-3 animate-spin" />Finding alternatives...</>
                ) : (
                  <><ArrowRightLeft className="h-3 w-3" />{showAlts ? 'Hide' : 'Show'} alternative hotels</>
                )}
              </button>
              {showAlts && alternatives.length > 0 && (
                <div className="space-y-1">
                  {alternatives.map((alt) => (
                    <a
                      key={alt.place_id}
                      href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(alt.name)}&query_place_id=${alt.place_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 rounded-md border border-border-default bg-surface-muted/50 p-2 text-xs hover:border-primary-200 hover:bg-surface-muted transition-colors"
                    >
                      {alt.photo_url && (
                        <img
                          src={`${alt.photo_url}?w=200`}
                          alt={alt.name}
                          loading="lazy"
                          className="h-8 w-8 rounded object-cover shrink-0"
                        />
                      )}
                      <div className="min-w-0 flex-1">
                        <p className="font-medium text-text-primary truncate">{alt.name}</p>
                        <div className="flex items-center gap-1.5 text-text-muted">
                          {alt.rating && (
                            <span className="flex items-center gap-0.5">
                              <Star className="h-2.5 w-2.5 fill-accent-400 text-accent-400" />{alt.rating.toFixed(1)}
                            </span>
                          )}
                          {alt.price_level != null && (
                            <span>{'$'.repeat(Math.max(1, alt.price_level))}</span>
                          )}
                        </div>
                      </div>
                    </a>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Altitude / Seasonal / Visa badges ─────────────────── */}
      {(city.altitude_meters && city.altitude_meters > 2000 || city.seasonal_notes || city.visa_notes) && (
        <div className="px-4 pb-2 flex flex-wrap gap-1.5">
          {city.altitude_meters && city.altitude_meters > 2000 && (
            <span className="text-xs px-1.5 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300">
              {city.altitude_meters.toFixed(0)}m altitude
            </span>
          )}
          {city.seasonal_notes && (
            <span className="text-xs px-1.5 py-0.5 rounded-full bg-sky-100 dark:bg-sky-900/30 text-sky-700 dark:text-sky-300" title={city.seasonal_notes}>
              Seasonal info
            </span>
          )}
          {city.visa_notes && (
            <span className="text-xs px-1.5 py-0.5 rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300" title={city.visa_notes}>
              Visa info
            </span>
          )}
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
                  <div key={dp.day_number} id={`day-${dp.day_number}`} className="space-y-2 scroll-mt-16">
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
                          aria-label="View day map"
                        >
                          <Map className="h-4 w-4 text-text-muted" />
                        </Button>
                      </div>
                    </div>
                    {dailyBudget && dailyBudget > 0 && dp.daily_cost_usd != null && (
                      <div className="mt-1">
                        <div className="h-2 rounded-full bg-surface-muted overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${
                              dp.daily_cost_usd > dailyBudget
                                ? 'bg-red-500'
                                : dp.daily_cost_usd > dailyBudget * 0.8
                                  ? 'bg-amber-500'
                                  : 'bg-green-500'
                            }`}
                            style={{ width: `${Math.min(100, (dp.daily_cost_usd / dailyBudget) * 100)}%` }}
                          />
                        </div>
                      </div>
                    )}
                    <DayTimeline dayPlan={dp} tips={tips} onChatAbout={onChatAbout} onRemoveActivity={onRemoveActivity} onAdjustDuration={onAdjustDuration} onReorder={onReorder} recentChanges={recentChanges} />
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
            <div className="absolute top-3 left-3 right-3 z-10 flex items-center justify-between gap-2">
              <span className="rounded-lg bg-surface/90 backdrop-blur-sm px-3 py-1.5 shadow-sm text-sm font-semibold text-text-primary">
                Day {mapDayPlan.day_number}: {mapDayPlan.theme}
              </span>
              <button
                type="button"
                onClick={() => setMapDayPlan(null)}
                className="flex h-8 w-8 items-center justify-center rounded-full bg-surface/90 backdrop-blur-sm shadow-sm hover:bg-surface transition-colors shrink-0"
                aria-label="Close map"
              >
                <X className="h-4 w-4 text-text-primary" />
              </button>
            </div>
            <Suspense fallback={<div className="h-full w-full bg-surface-muted animate-pulse" />}>
              <DayMap dayPlan={mapDayPlan} mapInstanceId={`day-map-overlay-${mapDayPlan.day_number}`} />
            </Suspense>
            <div className="absolute bottom-3 left-3 z-10 rounded-lg bg-surface/90 backdrop-blur-sm shadow-sm">
              <DayMapLegend />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
