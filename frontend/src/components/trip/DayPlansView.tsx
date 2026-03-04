import { Suspense, useState, useCallback, useEffect, useRef } from 'react';
import {
  Calendar, Cloud, Sun, CloudRain, Snowflake, Thermometer,
  MessageSquare, PlusCircle, ArrowLeft, FileDown, CalendarPlus, ChevronDown, DollarSign,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { DayNav } from '@/components/trip/DayNav';
import { DayTimeline } from '@/components/trip/DayTimeline';
import { BudgetSummary } from '@/components/trip/BudgetSummary';
import { DayMap } from '@/components/maps';
import { useTripStore } from '@/stores/tripStore';
import { useUIStore } from '@/stores/uiStore';
import { api } from '@/services/api';

export function DayPlansView() {
  const { dayPlans, costBreakdown, tips, tripId } = useTripStore();
  const { setPhase } = useUIStore();
  const [activeDay, setActiveDay] = useState(1);
  const [showExport, setShowExport] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  const activePlan = dayPlans?.find((dp) => dp.day_number === activeDay);

  // Scroll to top when active day changes
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

  // Running cost total up to active day
  const runningCost = dayPlans
    .filter((dp) => dp.day_number <= activeDay)
    .reduce((sum, dp) => sum + (dp.daily_cost_usd || 0), 0);

  return (
    <div className="space-y-4" ref={contentRef}>
      {/* Day navigation */}
      <DayNav dayPlans={dayPlans} activeDay={activeDay} onDayClick={setActiveDay} />

      {/* Active day header */}
      {activePlan && (
        <div className="space-y-1">
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
        </div>
      )}

      {/* Timeline */}
      {activePlan && <DayTimeline dayPlan={activePlan} tips={tips} />}

      {/* Day map — auto-visible */}
      {activePlan && (
        <Suspense fallback={<div className="h-64 rounded-lg bg-surface-muted animate-pulse" />}>
          <div className="h-64 rounded-lg overflow-hidden border border-border-default">
            <DayMap dayPlan={activePlan} />
          </div>
        </Suspense>
      )}

      {/* Budget summary */}
      {costBreakdown && (
        <BudgetSummary costBreakdown={costBreakdown} totalDays={dayPlans.length} />
      )}

      {/* Running total */}
      {runningCost > 0 && (
        <div className="text-center text-xs text-text-muted">
          Days 1–{activeDay}: ~${Math.round(runningCost)} spent so far
          {costBreakdown?.budget_usd ? ` of $${costBreakdown.budget_usd.toLocaleString()}` : ''}
        </div>
      )}

      {/* Action bar */}
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
