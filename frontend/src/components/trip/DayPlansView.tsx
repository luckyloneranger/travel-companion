import { Suspense, useState, useCallback, useEffect, useRef } from 'react';
import {
  Calendar, Cloud, Sun, CloudRain, Snowflake, Thermometer,
  MessageSquare, PlusCircle, ArrowLeft, FileDown, CalendarPlus,
  ChevronDown, DollarSign, Sparkles, MapPin, Navigation, ArrowRight,
  Star, Car, Train, Bus, Plane, Ship, Hotel,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { DayNav } from '@/components/trip/DayNav';
import { DayTimeline } from '@/components/trip/DayTimeline';
import { BudgetSummary } from '@/components/trip/BudgetSummary';
import { DayMap } from '@/components/maps';
import { useTripStore } from '@/stores/tripStore';
import { useUIStore } from '@/stores/uiStore';
import { api } from '@/services/api';
import type { CityStop, TravelLeg } from '@/types';

const TRANSPORT_ICONS: Record<string, typeof Car> = {
  drive: Car, train: Train, bus: Bus, flight: Plane, ferry: Ship,
};

function formatDuration(hours: number): string {
  if (hours < 1) return `${Math.round(hours * 60)}m`;
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  return m > 0 ? `${h}h${m}m` : `${h}h`;
}

export function DayPlansView() {
  const { journey, dayPlans, costBreakdown, tips, tripId } = useTripStore();
  const { setPhase } = useUIStore();
  const [activeDay, setActiveDay] = useState(1);
  const [showExport, setShowExport] = useState(false);
  const [journeyExpanded, setJourneyExpanded] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  const activePlan = dayPlans?.find((dp) => dp.day_number === activeDay);

  // Find the city for the active day
  const activeCity: CityStop | undefined = journey?.cities.find(
    (c) => c.name.toLowerCase() === activePlan?.city_name?.toLowerCase(),
  );

  // Find outgoing transport leg (if this is the last day in this city)
  const isLastDayInCity = activePlan && dayPlans
    ? !dayPlans.some(
        (dp) =>
          dp.day_number > activeDay &&
          dp.city_name === activePlan.city_name,
      )
    : false;

  const departureLeg: TravelLeg | undefined =
    isLastDayInCity && journey && activeCity
      ? journey.travel_legs.find(
          (l) => l.from_city.toLowerCase() === activeCity.name.toLowerCase(),
        )
      : undefined;

  useEffect(() => {
    contentRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
  }, [activeDay]);

  const handleOpenChat = useCallback(() => {
    useUIStore.getState().openChat('day_plans');
  }, []);

  const handleBackToPreview = useCallback(() => {
    setPhase('preview');
  }, [setPhase]);

  const handleNewTrip = useCallback(() => {
    useTripStore.getState().reset();
    useUIStore.getState().resetUI();
  }, []);

  const handleExportPdf = useCallback(async () => {
    if (!tripId) return;
    try { await api.exportPdf(tripId); }
    catch { useUIStore.getState().setError('PDF export failed.'); }
  }, [tripId]);

  const handleExportCalendar = useCallback(async () => {
    if (!tripId) return;
    try { await api.exportCalendar(tripId); }
    catch { useUIStore.getState().setError('Calendar export failed.'); }
  }, [tripId]);

  if (!dayPlans || dayPlans.length === 0) return null;

  const WeatherIcon = activePlan?.weather
    ? activePlan.weather.condition.toLowerCase().includes('rain')
      ? CloudRain
      : activePlan.weather.condition.toLowerCase().includes('snow')
        ? Snowflake
        : activePlan.weather.temperature_high_c >= 30
          ? Thermometer
          : activePlan.weather.condition.toLowerCase().includes('cloud')
            ? Cloud
            : Sun
    : null;

  const formatDate = (dateStr: string): string => {
    try {
      const date = new Date(dateStr + 'T00:00:00');
      return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    } catch { return dateStr; }
  };

  const runningCost = dayPlans
    .filter((dp) => dp.day_number <= activeDay)
    .reduce((sum, dp) => sum + (dp.daily_cost_usd || 0), 0);

  return (
    <div className="space-y-4" ref={contentRef}>
      {/* ── Collapsible Journey Header ─────────────────────────── */}
      {journey && (
        <Collapsible open={journeyExpanded} onOpenChange={setJourneyExpanded}>
          <div className="rounded-lg border border-border-default bg-surface overflow-hidden">
            <CollapsibleTrigger asChild>
              <button
                type="button"
                className="w-full text-left px-4 py-3 hover:bg-surface-muted/50 transition-colors"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <Sparkles className="h-4 w-4 text-primary-500 shrink-0" />
                      <span className="text-sm font-semibold text-text-primary truncate">
                        {journey.theme}
                      </span>
                      {journey.review_score != null && (
                        <Badge
                          variant="default"
                          className={`text-xs shrink-0 ${
                            journey.review_score >= 70
                              ? 'bg-green-600 text-white'
                              : 'bg-amber-500 text-white'
                          }`}
                        >
                          {journey.review_score}
                        </Badge>
                      )}
                    </div>
                    {/* Compact route chain */}
                    <div className="flex flex-wrap items-center gap-1 mt-1.5">
                      {journey.cities.map((city, i) => {
                        const isActiveCity = city.name.toLowerCase() === activePlan?.city_name?.toLowerCase();
                        const leg = i > 0
                          ? journey.travel_legs.find((l) => l.to_city.toLowerCase() === city.name.toLowerCase())
                          : null;
                        const TransportIcon = leg ? (TRANSPORT_ICONS[leg.mode] ?? Car) : null;
                        return (
                          <span key={`${city.name}-${i}`} className="flex items-center gap-1">
                            {i > 0 && leg && TransportIcon && (
                              <span className="flex items-center gap-0.5 text-text-muted">
                                <TransportIcon className="h-3 w-3" />
                                <ArrowRight className="h-2.5 w-2.5" />
                              </span>
                            )}
                            {i > 0 && !leg && (
                              <ArrowRight className="h-2.5 w-2.5 text-text-muted" />
                            )}
                            <span
                              className={`text-xs px-1.5 py-0.5 rounded-full ${
                                isActiveCity
                                  ? 'bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 font-semibold'
                                  : 'text-text-muted'
                              }`}
                            >
                              {city.name}
                            </span>
                          </span>
                        );
                      })}
                    </div>
                    <div className="flex flex-wrap gap-3 mt-1 text-xs text-text-muted">
                      <span>{journey.total_days} days</span>
                      <span>{journey.cities.length} cities</span>
                      {journey.total_distance_km != null && (
                        <span>{journey.total_distance_km.toFixed(0)} km</span>
                      )}
                    </div>
                  </div>
                  <ChevronDown className={`h-4 w-4 text-text-muted shrink-0 transition-transform ${journeyExpanded ? 'rotate-180' : ''}`} />
                </div>
              </button>
            </CollapsibleTrigger>

            <CollapsibleContent>
              <div className="px-4 pb-4 border-t border-border-default space-y-3 pt-3">
                <p className="text-sm text-text-secondary break-words">{journey.summary}</p>
                {/* Per-city summary */}
                {journey.cities.map((city, i) => {
                  const leg = journey.travel_legs.find((l) => l.from_city.toLowerCase() === city.name.toLowerCase());
                  return (
                    <div key={i} className="text-xs text-text-muted">
                      <span className="font-medium text-text-primary">{city.name}, {city.country}</span>
                      {' — '}{city.days} days
                      {city.accommodation?.name && ` · ${city.accommodation.name}`}
                      {city.accommodation?.estimated_nightly_usd && ` ($${city.accommodation.estimated_nightly_usd}/n)`}
                      {leg && (
                        <span className="text-text-muted"> → {leg.mode} to {leg.to_city} ({formatDuration(leg.duration_hours)})</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </CollapsibleContent>
          </div>
        </Collapsible>
      )}

      {/* ── Day Navigation ─────────────────────────────────────── */}
      <DayNav dayPlans={dayPlans} activeDay={activeDay} onDayClick={setActiveDay} />

      {/* ── Active Day Header + City Context ───────────────────── */}
      {activePlan && (
        <div className="space-y-2">
          <h2 className="text-lg font-display font-bold text-text-primary">
            Day {activePlan.day_number}: {activePlan.theme}
          </h2>
          <div className="flex flex-wrap items-center gap-2 text-xs text-text-muted">
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {formatDate(activePlan.date)}
            </span>
            <Badge variant="secondary" className="text-xs">{activePlan.city_name}</Badge>
            <span>{activePlan.activities.filter(a => a.duration_minutes > 0).length} activities</span>
            {activePlan.weather && WeatherIcon && (
              <Badge variant="outline" className="text-xs flex items-center gap-1">
                <WeatherIcon className="h-3 w-3" />
                {activePlan.weather.temperature_low_c.toFixed(0)}–{activePlan.weather.temperature_high_c.toFixed(0)}°C
                {activePlan.weather.precipitation_chance_percent > 0 && (
                  <span> · {activePlan.weather.precipitation_chance_percent}% rain</span>
                )}
              </Badge>
            )}
            {activePlan.daily_cost_usd != null && activePlan.daily_cost_usd > 0 && (
              <Badge variant="outline" className="text-xs flex items-center gap-1">
                <DollarSign className="h-3 w-3" />~${activePlan.daily_cost_usd.toFixed(0)}/day
              </Badge>
            )}
          </div>

          {/* Current city accommodation */}
          {activeCity?.accommodation && (
            <div className="flex items-center gap-2 text-xs text-text-muted rounded-md bg-accent-50/50 dark:bg-accent-500/10 border border-accent-200 dark:border-accent-500/20 px-3 py-2">
              <Hotel className="h-3.5 w-3.5 text-accent-500 shrink-0" />
              <span className="font-medium text-text-primary">{activeCity.accommodation.name}</span>
              {activeCity.accommodation.rating && (
                <span className="flex items-center gap-0.5">
                  <Star className="h-3 w-3 fill-accent-400 text-accent-400" />
                  {activeCity.accommodation.rating.toFixed(1)}
                </span>
              )}
              {activeCity.accommodation.estimated_nightly_usd && (
                <span>${activeCity.accommodation.estimated_nightly_usd}/night</span>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Timeline ───────────────────────────────────────────── */}
      {activePlan && <DayTimeline dayPlan={activePlan} tips={tips} />}

      {/* ── Transport to next city banner ──────────────────────── */}
      {departureLeg && (() => {
        const TransportIcon = TRANSPORT_ICONS[departureLeg.mode] ?? Car;
        return (
          <div className="flex items-center gap-3 rounded-lg bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 px-4 py-3">
            <TransportIcon className="h-5 w-5 text-primary-500 shrink-0" />
            <div className="text-sm">
              <span className="font-medium text-primary-700 dark:text-primary-300">
                Tomorrow: {departureLeg.mode} to {departureLeg.to_city}
              </span>
              <span className="text-primary-600/70 dark:text-primary-400/70">
                {' '}· {formatDuration(departureLeg.duration_hours)}
                {departureLeg.fare && ` · ${departureLeg.fare}`}
              </span>
            </div>
          </div>
        );
      })()}

      {/* ── Day Map ────────────────────────────────────────────── */}
      {activePlan && (
        <Suspense fallback={<div className="h-64 rounded-lg bg-surface-muted animate-pulse" />}>
          <div className="h-64 rounded-lg overflow-hidden border border-border-default">
            <DayMap dayPlan={activePlan} />
          </div>
        </Suspense>
      )}

      {/* ── Budget ─────────────────────────────────────────────── */}
      {costBreakdown && (
        <BudgetSummary costBreakdown={costBreakdown} totalDays={dayPlans.length} />
      )}
      {runningCost > 0 && (
        <div className="text-center text-xs text-text-muted">
          Days 1–{activeDay}: ~${Math.round(runningCost)} spent so far
          {costBreakdown?.budget_usd ? ` of $${costBreakdown.budget_usd.toLocaleString()}` : ''}
        </div>
      )}

      {/* ── Action Bar ─────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border-default pt-4">
        <Button variant="ghost" size="sm" onClick={handleBackToPreview}>
          <ArrowLeft className="h-4 w-4" />
          Back to Overview
        </Button>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={handleOpenChat}>
            <MessageSquare className="h-4 w-4" />
            Edit via Chat
          </Button>
          <div className="relative">
            <Button variant="outline" size="sm" onClick={() => setShowExport(!showExport)}>
              <FileDown className="h-4 w-4" />
              Export
              <ChevronDown className={`h-3 w-3 transition-transform ${showExport ? 'rotate-180' : ''}`} />
            </Button>
            {showExport && (
              <div className="absolute bottom-full left-0 mb-1 z-10 rounded-md border border-border-default bg-surface shadow-lg py-1 min-w-[120px]">
                <button onClick={() => { handleExportPdf(); setShowExport(false); }} className="w-full text-left px-3 py-1.5 text-sm text-text-primary hover:bg-surface-muted flex items-center gap-2">
                  <FileDown className="h-3.5 w-3.5" /> PDF
                </button>
                <button onClick={() => { handleExportCalendar(); setShowExport(false); }} className="w-full text-left px-3 py-1.5 text-sm text-text-primary hover:bg-surface-muted flex items-center gap-2">
                  <CalendarPlus className="h-3.5 w-3.5" /> Calendar
                </button>
              </div>
            )}
          </div>
          <Button variant="ghost" size="sm" onClick={handleNewTrip}>
            <PlusCircle className="h-4 w-4" />
            New Trip
          </Button>
        </div>
      </div>
    </div>
  );
}
