import { Suspense, useCallback, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  MapPin, Calendar, Navigation, Sparkles,
  MessageSquare, Copy, Check, Share2,
  FileDown, CalendarPlus, ChevronDown,
  Loader2, RefreshCw, Users, Map as MapIcon, DollarSign, LayoutList, Maximize2, ChevronRight,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { CompactCityCard } from '@/components/trip/CompactCityCard';
import { FullDayView } from '@/components/trip/FullDayView';
import { BudgetSummary } from '@/components/trip/BudgetSummary';
import { NavigationSidebar } from '@/components/trip/NavigationSidebar';
import { LiveTripView } from '@/components/trip/LiveTripView';
import { RouteTimeline } from '@/components/trip/RouteTimeline';
import { TripMap, TripMapLegend, DayMap, DayMapLegend } from '@/components/maps';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { useTripStore } from '@/stores/tripStore';
import { useUIStore } from '@/stores/uiStore';
import { api } from '@/services/api';
import { showToast } from '@/components/ui/toast';
import type { DayPlan } from '@/types';

interface JourneyDashboardProps {
  onGenerateDayPlans: () => void;
  onCancelDayPlans: () => void;
  onOpenChat: () => void;
}

export function JourneyDashboard({ onGenerateDayPlans, onCancelDayPlans, onOpenChat }: JourneyDashboardProps) {
  const { journey, tripId, dayPlans, costBreakdown, tips, recentChanges } = useTripStore();
  const travelers = useTripStore((s) => s.travelers);
  const dayPlansGenerating = useUIStore((s) => s.dayPlansGenerating);
  const openChat = useUIStore((s) => s.openChat);
  const [copied, setCopied] = useState(false);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [showExport, setShowExport] = useState(false);
  const [isSharing, setIsSharing] = useState(false);
  const [isExporting, setIsExporting] = useState<string | null>(null);
  const [allExpanded, setAllExpanded] = useState(true);
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = (searchParams.get('tab') as 'overview' | 'cities' | 'budget' | 'map' | 'live') || 'overview';
  const [activeTabState, setActiveTabState] = useState<'overview' | 'cities' | 'budget' | 'map' | 'live'>(initialTab);

  const setActiveTab = useCallback((tab: 'overview' | 'cities' | 'budget' | 'map' | 'live') => {
    setActiveTabState(tab);
    setSearchParams({ tab }, { replace: true });
  }, [setSearchParams]);

  const activeTab = activeTabState;
  const [fullDayViewDay, setFullDayViewDay] = useState<number | null>(null);
  const [mapDayFilter, setMapDayFilter] = useState('journey');

  // Feature 19: Contextual chat — open chat pre-filled with activity context
  const handleChatAbout = useCallback((activityName: string, dayNumber: number) => {
    openChat('day_plans', `About "${activityName}" on Day ${dayNumber}: `);
  }, [openChat]);

  // Feature 9: Drag-and-drop reorder activities
  const handleReorder = useCallback(async (dayNumber: number, activityIds: string[]) => {
    if (!tripId) return;
    try {
      const result = await api.reorderActivities(tripId, dayNumber, activityIds);
      useTripStore.getState().updateDayPlans(result.day_plans as DayPlan[]);
    } catch (err) {
      if (!(err instanceof Error && err.message === '__auth_required__'))
        useUIStore.getState().setError('Failed to reorder activities.');
    }
  }, [tripId]);

  // Remove activity with confirmation
  const handleRemoveActivity = useCallback(async (dayNumber: number, activityId: string) => {
    if (!tripId) return;
    const activity = dayPlans?.flatMap(dp => dp.activities).find(a => a.id === activityId);
    const name = activity?.place?.name || 'Activity';
    if (!window.confirm(`Remove "${name}" from Day ${dayNumber}?`)) return;
    try {
      const result = await api.removeActivity(tripId, dayNumber, activityId);
      useTripStore.getState().updateDayPlans(result.day_plans as DayPlan[]);
      showToast(`Removed "${name}"`, 'success');
    } catch (err) {
      if (!(err instanceof Error && err.message === '__auth_required__'))
        showToast('Failed to remove activity', 'error');
    }
  }, [tripId, dayPlans]);

  // Adjust activity duration (+/- 15 min)
  const handleAdjustDuration = useCallback(async (dayNumber: number, activityId: string, change: number) => {
    if (!tripId) return;
    try {
      const result = await api.adjustDuration(tripId, dayNumber, activityId, change);
      useTripStore.getState().updateDayPlans(result.day_plans as DayPlan[]);
    } catch (err) {
      if (!(err instanceof Error && err.message === '__auth_required__'))
        showToast('Failed to adjust duration', 'error');
    }
  }, [tripId]);

  // Feature 12: Daily budget for cost progress bars
  const dailyBudget = costBreakdown?.budget_usd && journey
    ? costBreakdown.budget_usd / journey.total_days
    : undefined;

  // Use complete cost breakdown when day plans exist, otherwise estimate from journey data
  const estimatedTotal = (() => {
    if (costBreakdown && costBreakdown.total_usd > 0) {
      return Math.round(costBreakdown.total_usd);
    }
    if (!journey) return 0;
    let total = 0;
    for (const city of journey.cities) {
      if (city.accommodation?.estimated_nightly_usd) {
        total += city.accommodation.estimated_nightly_usd * city.days;
      }
    }
    for (const leg of journey.travel_legs) {
      if (leg.fare_usd) {
        total += leg.fare_usd;
      } else if (leg.fare) {
        const match = leg.fare.match(/[\d.]+/);
        if (match) total += parseFloat(match[0]);
      }
    }
    return Math.round(total);
  })();

  const handleCopyItinerary = useCallback(() => {
    if (!journey) return;
    const lines: string[] = [
      journey.theme, journey.summary, '',
      `Route: ${journey.origin ? `${journey.origin} → ` : ''}${journey.cities.map(c => c.name).join(' → ')}`,
      `Duration: ${journey.total_days} days | ${journey.cities.length} cities`,
      journey.total_distance_km ? `Distance: ${journey.total_distance_km.toFixed(0)} km` : '', '',
    ];
    journey.cities.forEach((city, i) => {
      lines.push(`--- ${city.name}, ${city.country} (${city.days} days) ---`);
      if (city.why_visit) lines.push(city.why_visit);
      city.highlights.forEach(h => lines.push(`  • ${h.name}${h.description ? ` - ${h.description}` : ''}`));
      if (city.accommodation) lines.push(`Stay: ${city.accommodation.name}`);
      if (i < journey.travel_legs.length) {
        const leg = journey.travel_legs[i];
        lines.push(`→ ${leg.mode} to ${leg.to_city} (${leg.duration_hours.toFixed(1)}h)`);
      }
      lines.push('');
    });
    navigator.clipboard.writeText(lines.filter(Boolean).join('\n')).then(() => {
      showToast('Itinerary copied!', 'success');
    }).catch(() => {
      showToast('Could not copy itinerary', 'error');
    });
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [journey]);

  const handleShare = useCallback(async () => {
    if (!tripId) return;
    setIsSharing(true);
    try {
      const result = await api.shareTrip(tripId);
      const url = `${window.location.origin}/shared/${result.token}`;
      setShareUrl(url);
      // Auto-copy to clipboard
      navigator.clipboard.writeText(url).then(() => {
        showToast('Share link copied!', 'success');
      }).catch(() => {
        showToast('Could not copy link — use the URL field below', 'error');
      });
    } catch (err) {
      if (!(err instanceof Error && err.message === '__auth_required__'))
        useUIStore.getState().setError(err instanceof Error ? `Share failed: ${err.message}` : 'Share failed');
    } finally {
      setIsSharing(false);
    }
  }, [tripId]);

  const handleExportPdf = useCallback(async () => {
    if (!tripId) return;
    setIsExporting('pdf');
    try { await api.exportPdf(tripId); showToast('PDF downloaded', 'success'); }
    catch (e) { if (!(e instanceof Error && e.message === '__auth_required__')) useUIStore.getState().setError('PDF export failed.'); }
    finally { setIsExporting(null); }
  }, [tripId]);

  const handleExportCalendar = useCallback(async () => {
    if (!tripId) return;
    setIsExporting('calendar');
    try { await api.exportCalendar(tripId); showToast('Calendar file downloaded', 'success'); }
    catch (e) { if (!(e instanceof Error && e.message === '__auth_required__')) useUIStore.getState().setError('Calendar export failed.'); }
    finally { setIsExporting(null); }
  }, [tripId]);

  if (!journey) return null;

  const tabs = [
    { id: 'overview' as const, label: 'Overview', icon: Sparkles },
    { id: 'cities' as const, label: `Cities (${journey.cities.length})`, icon: LayoutList },
    { id: 'budget' as const, label: 'Budget', icon: DollarSign, hidden: !costBreakdown || !dayPlans || dayPlans.length === 0 },
    { id: 'map' as const, label: 'Map', icon: MapIcon },
  ];

  return (
    <div className="space-y-6">
      {/* Header card — always visible */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <CardTitle className="text-xl font-display flex items-center gap-2 min-w-0">
                <Sparkles className="h-5 w-5 text-primary-500 shrink-0" />
                <span className="break-words">{journey.theme}</span>
              </CardTitle>
              <CardDescription className="mt-2 text-base leading-relaxed break-words">
                {journey.summary}
              </CardDescription>
            </div>
            {journey.review_score != null && (
              <Badge
                variant={journey.review_score >= 70 ? 'default' : 'outline'}
                className={`shrink-0 text-xs ${
                  journey.review_score >= 80 ? 'bg-green-600 text-white'
                    : journey.review_score >= 70 ? 'bg-green-600/80 text-white'
                      : 'border-amber-400 text-amber-700 dark:text-amber-400'
                }`}
              >
                Score: {journey.review_score}
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4 pt-0">
          {/* Stats */}
          <div className="flex flex-wrap gap-4 text-sm text-text-secondary">
            <span className="flex items-center gap-1.5"><MapPin className="h-4 w-4 text-text-muted" />{journey.cities.length} {journey.cities.length === 1 ? 'city' : 'cities'}</span>
            <span className="flex items-center gap-1.5"><Calendar className="h-4 w-4 text-text-muted" />{journey.total_days} days</span>
            <span className="flex items-center gap-1.5">
              <Users className="h-4 w-4 text-text-muted" />
              {travelers.adults} adult{travelers.adults !== 1 ? 's' : ''}
              {travelers.children > 0 && `, ${travelers.children} child${travelers.children !== 1 ? 'ren' : ''}`}
              {travelers.infants > 0 && `, ${travelers.infants} infant${travelers.infants !== 1 ? 's' : ''}`}
            </span>
            {journey.total_distance_km != null && (
              <span className="flex items-center gap-1.5"><Navigation className="h-4 w-4 text-text-muted" />{journey.total_distance_km.toFixed(0)} km</span>
            )}
            {estimatedTotal > 0 && (
              <span className="flex items-center gap-1.5 font-medium">
                ~${estimatedTotal.toLocaleString()} estimated
                {!costBreakdown && <span className="text-xs font-normal text-text-muted">(accom + transport)</span>}
              </span>
            )}
          </div>

          <Separator />

          {/* Actions */}
          <div className="flex flex-wrap gap-2">
            {/* Day plans action button */}
            {dayPlansGenerating ? (
              <Button
                variant="outline"
                size="sm"
                onClick={onCancelDayPlans}
                className="border-primary-300 text-primary-600"
              >
                <Loader2 className="h-4 w-4 animate-spin" />
                Generating...
              </Button>
            ) : dayPlans && dayPlans.length > 0 ? (
              <Button variant="outline" size="sm" onClick={onGenerateDayPlans}>
                <RefreshCw className="h-4 w-4" />
                Regenerate
              </Button>
            ) : (
              <Button
                onClick={onGenerateDayPlans}
                size="sm"
                className="bg-primary-600 hover:bg-primary-700 text-white"
              >
                <Calendar className="h-4 w-4" />
                Generate Day Plans
              </Button>
            )}

            <Button variant="outline" size="sm" onClick={onOpenChat}>
              <MessageSquare className="h-4 w-4" />
              Chat
            </Button>
            <Button variant="outline" size="sm" onClick={handleCopyItinerary}>
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              {copied ? 'Copied!' : 'Copy'}
            </Button>
            <Button variant="outline" size="sm" onClick={handleShare} disabled={isSharing}>
              {isSharing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Share2 className="h-4 w-4" />}
              {isSharing ? 'Sharing...' : shareUrl ? 'Shared!' : 'Share'}
            </Button>
            <div className="relative">
              <Button variant="outline" size="sm" onClick={() => setShowExport(!showExport)}>
                <FileDown className="h-4 w-4" />
                Export
                <ChevronDown className={`h-3 w-3 transition-transform ${showExport ? 'rotate-180' : ''}`} />
              </Button>
              {showExport && (
                <div role="menu" className="absolute top-full right-0 mt-1 z-10 rounded-md border border-border-default bg-surface shadow-lg py-1 min-w-[120px]">
                  <button role="menuitem" onClick={() => { handleExportPdf(); setShowExport(false); }} disabled={isExporting === 'pdf'} className="w-full text-left px-3 py-1.5 text-sm text-text-primary hover:bg-surface-muted flex items-center gap-2 disabled:opacity-50">
                    {isExporting === 'pdf' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileDown className="h-3.5 w-3.5" />} PDF
                  </button>
                  <button role="menuitem" onClick={() => { handleExportCalendar(); setShowExport(false); }} disabled={isExporting === 'calendar'} className="w-full text-left px-3 py-1.5 text-sm text-text-primary hover:bg-surface-muted flex items-center gap-2 disabled:opacity-50">
                    {isExporting === 'calendar' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CalendarPlus className="h-3.5 w-3.5" />} Calendar
                  </button>
                </div>
              )}
            </div>
            {/* Feature 25: Live trip "Today" button */}
            {dayPlans && dayPlans.some(dp => dp.date === new Date().toISOString().split('T')[0]) && (
              <Button variant="ghost" size="sm" onClick={() => setActiveTab('live')}>
                <Navigation className="h-4 w-4" />
                Today
              </Button>
            )}
          </div>

          {/* Share URL */}
          {shareUrl && (
            <div className="flex items-center gap-2 rounded-md border border-border-default bg-surface-muted px-3 py-2">
              <input type="text" readOnly value={shareUrl} aria-label="Shared trip URL" className="flex-1 bg-transparent text-sm text-text-secondary outline-none min-w-0" onFocus={(e) => e.target.select()} />
              <Button variant="ghost" size="sm" onClick={() => { navigator.clipboard.writeText(shareUrl).catch(() => window.prompt('Copy:', shareUrl)); }}>
                <Copy className="h-3.5 w-3.5" /> Copy
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tab navigation */}
      <div className="flex gap-1 border-b border-border-default" role="tablist">
        {tabs.filter(t => !t.hidden).map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              role="tab"
              aria-selected={isActive}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                isActive
                  ? 'border-primary-600 text-primary-600 dark:text-primary-400 dark:border-primary-400'
                  : 'border-transparent text-text-muted hover:text-text-primary hover:border-border-default'
              }`}
            >
              <Icon className="h-4 w-4" />
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div role="tabpanel">
        {/* Overview tab */}
        {activeTab === 'overview' && (
          <div className="space-y-4 animate-fade-in-up">
            {/* Route visualization */}
            <Card>
              <CardContent className="py-4">
                <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">Route</h3>
                <RouteTimeline journey={journey} onCityClick={() => setActiveTab('cities')} />
              </CardContent>
            </Card>

            {/* Map preview */}
            <div>
              <div className="relative group cursor-pointer" onClick={() => setActiveTab('map')}>
                <ErrorBoundary fallback={<div className="h-60 sm:h-80 rounded-lg bg-surface-muted flex items-center justify-center text-sm text-text-muted">Map unavailable</div>}>
                  <Suspense fallback={<div className="h-60 sm:h-80 rounded-lg bg-surface-muted animate-pulse" />}>
                    <div className="h-60 sm:h-80 rounded-lg overflow-hidden border border-border-default">
                      <TripMap journey={journey} onCityClick={() => setActiveTab('cities')} />
                    </div>
                  </Suspense>
                </ErrorBoundary>
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors rounded-lg flex items-center justify-center">
                  <span className="opacity-0 group-hover:opacity-100 transition-opacity text-sm font-medium text-white bg-black/60 px-3 py-1.5 rounded-full">
                    Click to explore map
                  </span>
                </div>
              </div>
              <TripMapLegend />
            </div>

            {/* City highlights */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {journey.cities.map((city, i) => (
                <Card key={i} className="cursor-pointer hover:border-primary-300 transition-colors" onClick={() => setActiveTab('cities')}>
                  <CardContent className="py-4 px-5">
                    <div className="flex items-start gap-3">
                      <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/40 text-xs font-bold text-primary-700 dark:text-primary-300 shrink-0 mt-0.5">
                        {i + 1}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <p className="text-base font-semibold text-text-primary">{city.name}, {city.country}</p>
                          <span className="text-xs text-text-muted">{city.days} {city.days === 1 ? 'day' : 'days'}</span>
                        </div>
                        {city.why_visit && (
                          <p className="text-sm text-text-secondary mt-1.5 line-clamp-2">{city.why_visit}</p>
                        )}
                        {city.highlights.length > 0 && (
                          <div className="flex flex-wrap gap-2 mt-2.5">
                            {city.highlights.slice(0, 4).map((h) => (
                              <span key={h.name} className="inline-flex items-center gap-1 text-xs text-text-muted">
                                <Sparkles className="h-2.5 w-2.5 text-accent-400" />
                                {h.name}
                              </span>
                            ))}
                            {city.highlights.length > 4 && (
                              <span className="text-xs text-text-muted">+{city.highlights.length - 4} more</span>
                            )}
                          </div>
                        )}
                        <span className="text-xs text-primary-500 flex items-center gap-0.5 mt-1">
                          View itinerary <ChevronRight className="h-3 w-3" />
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Cities tab */}
        {activeTab === 'cities' && (
          <div className="space-y-3 animate-fade-in-up">
            {/* Feature 13: Sticky day navigator */}
            {dayPlans && dayPlans.length > 0 && (
              <div className="sticky top-0 z-10 bg-surface/95 backdrop-blur-sm border-b border-border-default -mx-1 px-1 py-2 flex items-center gap-2 overflow-x-auto">
                {journey.cities.map((city, ci) => {
                  const cityDays = dayPlans.filter(dp => dp.city_name.toLowerCase() === city.name.toLowerCase());
                  return (
                    <div key={ci} className="flex items-center gap-1 shrink-0">
                      {ci > 0 && <span className="text-text-muted/40 mx-0.5">|</span>}
                      <span className="text-xs font-medium text-text-muted mr-1">{city.name}</span>
                      {cityDays.map(dp => (
                        <button
                          key={dp.day_number}
                          type="button"
                          onClick={() => {
                            document.getElementById(`day-${dp.day_number}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                          }}
                          className="flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 hover:bg-primary-200 dark:hover:bg-primary-800/50 transition-colors"
                          title={`Day ${dp.day_number}: ${dp.theme}`}
                        >
                          {dp.day_number}
                        </button>
                      ))}
                    </div>
                  );
                })}
                {journey.cities.length > 1 && (
                  <Button variant="ghost" size="xs" onClick={() => setAllExpanded(!allExpanded)} className="ml-auto shrink-0">
                    {allExpanded ? 'Collapse' : 'Expand'}
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="xs"
                  onClick={() => setFullDayViewDay(dayPlans[0].day_number)}
                  className="shrink-0"
                  title="Full-screen day view"
                >
                  <Maximize2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            )}
            {!(dayPlans && dayPlans.length > 0) && journey.cities.length > 1 && (
              <div className="flex justify-end">
                <Button variant="ghost" size="sm" onClick={() => setAllExpanded(!allExpanded)}>
                  {allExpanded ? 'Collapse All' : 'Expand All'}
                </Button>
              </div>
            )}
            {journey.cities.map((city, i) => {
              const departureLeg = journey.travel_legs.find(l => l.from_city === city.name);
              const cityDayPlans = dayPlans?.filter(
                (dp) => dp.city_name.toLowerCase() === city.name.toLowerCase(),
              );
              return (
                <CompactCityCard
                  key={`city-${i}-${allExpanded}`}
                  city={city}
                  index={i}
                  departureLeg={departureLeg}
                  dayPlans={cityDayPlans}
                  tips={tips}
                  defaultExpanded={allExpanded}
                  hideHighlights={!!(dayPlans && dayPlans.length > 0)}
                  dailyBudget={dailyBudget}
                  onChatAbout={handleChatAbout}
                  onRemoveActivity={handleRemoveActivity}
                  onAdjustDuration={handleAdjustDuration}
                  onReorder={handleReorder}
                  recentChanges={recentChanges}
                />
              );
            })}
            {!dayPlans && !dayPlansGenerating && (
              <div className="text-center py-8 space-y-3">
                <p className="text-sm text-text-muted">Generate day plans to see detailed activities, routes, and weather for each city</p>
                <Button onClick={onGenerateDayPlans} size="sm">
                  Generate Day Plans
                </Button>
              </div>
            )}
          </div>
        )}

        {/* Budget tab */}
        {activeTab === 'budget' && costBreakdown && dayPlans && dayPlans.length > 0 && (
          <div className="animate-fade-in-up">
            <BudgetSummary costBreakdown={costBreakdown} totalDays={dayPlans.length} />
          </div>
        )}

        {/* Map tab — Feature 16: Unified Map Mode + Feature 18: What's Nearby */}
        {activeTab === 'map' && (
          <div className="animate-fade-in-up space-y-3">
            {dayPlans && dayPlans.length > 0 && (
              <div className="flex items-center gap-2">
                <select
                  value={mapDayFilter}
                  onChange={(e) => setMapDayFilter(e.target.value)}
                  className="rounded-md border border-border-default bg-surface px-3 py-1.5 text-sm text-text-primary"
                >
                  <option value="journey">Full Journey Route</option>
                  {dayPlans.map(dp => (
                    <option key={dp.day_number} value={String(dp.day_number)}>
                      Day {dp.day_number}: {dp.theme} ({dp.city_name})
                    </option>
                  ))}
                </select>
              </div>
            )}
            {/* Feature 18: What's Nearby link */}
            {mapDayFilter !== 'journey' && (() => {
              const dp = dayPlans?.find(d => d.day_number === Number(mapDayFilter));
              const firstAct = dp?.activities.find(a => a.duration_minutes > 0);
              if (!firstAct) return null;
              const { lat, lng } = firstAct.place.location;
              return (
                <a
                  href={`https://www.google.com/maps/search/restaurants+ATMs+pharmacy/@${lat},${lng},15z`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs text-primary-600 dark:text-primary-400 hover:underline"
                >
                  <MapPin className="h-3.5 w-3.5" />Explore what&apos;s nearby on Google Maps
                </a>
              );
            })()}
            <ErrorBoundary fallback={<div className="h-[60vh] rounded-lg bg-surface-muted flex items-center justify-center text-sm text-text-muted">Map unavailable</div>}>
              <Suspense fallback={<div className="h-[60vh] rounded-lg bg-surface-muted animate-pulse" />}>
                <div className="h-[60vh] rounded-lg overflow-hidden border border-border-default">
                  {mapDayFilter === 'journey' ? (
                    <TripMap journey={journey} onCityClick={() => setActiveTab('cities')} />
                  ) : (
                    (() => {
                      const dp = dayPlans?.find(d => d.day_number === Number(mapDayFilter));
                      return dp ? (
                        <DayMap dayPlan={dp} mapInstanceId="unified-day-map" />
                      ) : (
                        <TripMap journey={journey} onCityClick={() => setActiveTab('cities')} />
                      );
                    })()
                  )}
                </div>
              </Suspense>
            </ErrorBoundary>
            {mapDayFilter === 'journey' ? (
              <TripMapLegend />
            ) : (
              <DayMapLegend />
            )}
          </div>
        )}

        {/* Feature 25: Live trip tab */}
        {activeTab === 'live' && dayPlans && (
          <div className="animate-fade-in-up">
            <LiveTripView
              dayPlans={dayPlans}
              tips={tips}
              tripStartDate={dayPlans[0]?.date ?? ''}
              onChatAbout={handleChatAbout}
            />
          </div>
        )}
      </div>

      {/* Feature 15: Quick navigation sidebar */}
      {dayPlans && dayPlans.length > 0 && (
        <NavigationSidebar
          journey={journey}
          dayPlans={dayPlans}
          onSelectDay={(dayNum) => {
            setActiveTab('cities');
            setTimeout(() => {
              document.getElementById(`day-${dayNum}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
          }}
        />
      )}

      {fullDayViewDay && dayPlans && (
        <FullDayView
          dayPlans={dayPlans}
          tips={tips}
          initialDay={fullDayViewDay}
          onClose={() => setFullDayViewDay(null)}
          onChatAbout={handleChatAbout}
        />
      )}
    </div>
  );
}
