import { Suspense, useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  MapPin, Calendar, Navigation, Sparkles,
  MessageSquare, Copy, Check, Share2,
  FileDown, CalendarPlus, ChevronDown, ChevronUp,
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
import { api, photoUrl } from '@/services/api';
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
  const [showCelebration, setShowCelebration] = useState(true);
  const [showScrollTop, setShowScrollTop] = useState(false);
  const [adjustingActivityId, setAdjustingActivityId] = useState<string | null>(null);
  const [removingActivityId, setRemovingActivityId] = useState<string | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = (searchParams.get('tab') as 'overview' | 'cities' | 'budget' | 'map' | 'live') || 'overview';
  const [activeTabState, setActiveTabState] = useState<'overview' | 'cities' | 'budget' | 'map' | 'live'>(initialTab);

  const setActiveTab = useCallback((tab: 'overview' | 'cities' | 'budget' | 'map' | 'live') => {
    setActiveTabState(tab);
    setSearchParams({ tab }, { replace: true });
  }, [setSearchParams]);

  const activeTab = activeTabState;

  // Pick the best hero photo — prefer iconic landmarks over restaurants/hotels
  const heroPhoto = (() => {
    const iconicCategories = ['tourist_attraction', 'landmark', 'monument', 'castle', 'temple', 'museum', 'observation_deck', 'scenic_spot', 'park', 'garden', 'church', 'historic'];
    const diningCategories = ['restaurant', 'cafe', 'coffee', 'bar', 'bakery', 'food'];

    let bestIconic: string | null = null;
    let bestNonDining: string | null = null;
    let anyPhoto: string | null = null;

    for (const city of journey?.cities ?? []) {
      const cityDays = dayPlans?.filter(dp => dp.city_name.toLowerCase() === city.name.toLowerCase());
      for (const dp of cityDays ?? []) {
        for (const act of dp.activities) {
          if (!act.place.photo_urls?.[0]) continue;
          const cat = (act.place.category || '').toLowerCase();
          if (!anyPhoto) anyPhoto = act.place.photo_urls[0];
          if (!bestIconic && iconicCategories.some(k => cat.includes(k))) {
            bestIconic = act.place.photo_urls[0];
          }
          if (!bestNonDining && !diningCategories.some(k => cat.includes(k))) {
            bestNonDining = act.place.photo_urls[0];
          }
        }
      }
    }
    return bestIconic || bestNonDining || anyPhoto || null;
  })();

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
    setRemovingActivityId(activityId);
    try {
      const result = await api.removeActivity(tripId, dayNumber, activityId);
      useTripStore.getState().updateDayPlans(result.day_plans as DayPlan[]);
      showToast(`Removed "${name}"`, 'success');
    } catch (err) {
      if (!(err instanceof Error && err.message === '__auth_required__'))
        showToast('Failed to remove activity', 'error');
    } finally {
      setRemovingActivityId(null);
    }
  }, [tripId, dayPlans]);

  // Adjust activity duration (+/- 15 min)
  const handleAdjustDuration = useCallback(async (dayNumber: number, activityId: string, change: number) => {
    if (!tripId) return;
    setAdjustingActivityId(activityId);
    try {
      const result = await api.adjustDuration(tripId, dayNumber, activityId, change);
      useTripStore.getState().updateDayPlans(result.day_plans as DayPlan[]);
    } catch (err) {
      if (!(err instanceof Error && err.message === '__auth_required__'))
        showToast('Failed to adjust duration', 'error');
    } finally {
      setAdjustingActivityId(null);
    }
  }, [tripId]);

  // Feature 12: Daily budget for cost progress bars
  const dailyBudget = costBreakdown?.budget_usd && journey
    ? costBreakdown.budget_usd / journey.total_days
    : undefined;

  // Issue #35: Close export menu on click outside
  useEffect(() => {
    if (!showExport) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest('[data-export-menu]')) {
        setShowExport(false);
      }
    };
    document.addEventListener('click', handler);
    return () => document.removeEventListener('click', handler);
  }, [showExport]);

  // Celebration banner auto-dismiss
  useEffect(() => {
    if (showCelebration) {
      const timer = setTimeout(() => setShowCelebration(false), 6000);
      return () => clearTimeout(timer);
    }
  }, [showCelebration]);

  // Scroll-to-top button visibility
  useEffect(() => {
    const handleScroll = () => setShowScrollTop(window.scrollY > 600);
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Scroll-reveal for city cards in Cities tab
  useEffect(() => {
    if (activeTab !== 'cities') return;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('revealed');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1 }
    );
    // Small delay to let DOM render
    const timer = setTimeout(() => {
      const elements = document.querySelectorAll('.scroll-reveal');
      elements.forEach((el) => observer.observe(el));
    }, 50);
    return () => {
      clearTimeout(timer);
      observer.disconnect();
    };
  }, [activeTab, dayPlans]);

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
    { id: 'budget' as const, label: 'Budget', icon: DollarSign, hidden: !costBreakdown || !dayPlans || dayPlans.length === 0 || (costBreakdown && costBreakdown.total_usd === 0) },
    { id: 'map' as const, label: 'Map', icon: MapIcon },
  ];

  return (
    <div className="space-y-6">
      {/* Celebration banner */}
      {showCelebration && journey && (
        <div className="animate-fade-in-up mb-4 rounded-xl bg-gradient-to-r from-primary-600 to-accent-500 p-5 text-white text-center shadow-lg relative overflow-hidden">
          {/* Confetti particles */}
          <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
            {Array.from({ length: 20 }).map((_, i) => (
              <div
                key={i}
                className="absolute w-2 h-2 rounded-full"
                style={{
                  left: `${5 + (i * 4.7) % 90}%`,
                  backgroundColor: ['#FFD700', '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8'][i % 6],
                  animation: `confetti-fall ${2 + (i % 3) * 0.7}s ease-out ${(i % 5) * 0.1}s forwards`,
                  opacity: 0.8,
                }}
              />
            ))}
          </div>
          <p className="text-xl font-display font-bold relative">Your adventure awaits!</p>
          <p className="text-sm opacity-90 mt-1 relative">
            {journey.cities.length} cities · {journey.total_days} days{journey.review_score ? ` · Quality score ${journey.review_score}/100` : ''}
          </p>
          <div className="flex items-center justify-center gap-3 mt-3 relative">
            <button
              onClick={() => { handleShare(); setShowCelebration(false); }}
              className="text-xs bg-white/20 hover:bg-white/30 rounded-full px-4 py-1.5 transition-colors"
            >
              Share with friends
            </button>
            <button
              onClick={() => { handleExportPdf(); setShowCelebration(false); }}
              className="text-xs bg-white/20 hover:bg-white/30 rounded-full px-4 py-1.5 transition-colors"
            >
              Download PDF
            </button>
          </div>
        </div>
      )}

      {/* Header card — always visible */}
      <Card className="overflow-hidden">
        {heroPhoto && (
          <div className="relative h-36 sm:h-48">
            <img
              src={`${photoUrl(heroPhoto)}${heroPhoto.includes('?') ? '&' : '?'}w=1200`}
              alt={journey.theme}
              className="absolute inset-0 h-full w-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/30 to-black/10" />
            <div className="absolute bottom-0 left-0 right-0 p-4 sm:p-5">
              <div className="flex items-end justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <h2 className="text-xl sm:text-2xl font-display font-bold text-white drop-shadow-sm break-words">
                    {journey.theme}
                  </h2>
                  <p className="mt-1 text-sm text-white/80 line-clamp-2 break-words">
                    {journey.summary}
                  </p>
                </div>
                {journey.review_score != null && (
                  <Badge
                    className={`shrink-0 text-xs border-white/30 ${
                      journey.review_score >= 80 ? 'bg-green-500/80 text-white'
                        : journey.review_score >= 70 ? 'bg-green-500/60 text-white'
                          : 'bg-amber-500/60 text-white'
                    }`}
                  >
                    Score: {journey.review_score}
                  </Badge>
                )}
              </div>
            </div>
          </div>
        )}
        {!heroPhoto && (
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
        )}
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
            <div className="relative" data-export-menu>
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
              <input type="text" readOnly value={shareUrl} aria-label="Share link (read-only)" placeholder="Share link (read-only)" className="flex-1 bg-transparent text-sm text-text-secondary outline-none min-w-0 cursor-default select-all" onFocus={(e) => e.target.select()} />
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
              title={tab.label}
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
              <div
                className="relative group cursor-pointer"
                role="button"
                tabIndex={0}
                onClick={() => setActiveTab('map')}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setActiveTab('map'); } }}
              >
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
                <Card key={i} className={`cursor-pointer hover:border-primary-300 transition-colors animate-stagger-in stagger-${Math.min(i + 1, 8)}`} onClick={() => setActiveTab('cities')}>
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
                        {city.experience_themes && city.experience_themes.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mt-2">
                            {city.experience_themes.map((et) => (
                              <span key={et.theme} className="inline-flex items-center text-xs text-text-muted">
                                {et.theme}
                                {!!et.excursion_type && (
                                  <span className="ml-1 text-[10px] bg-accent-100 dark:bg-accent-500/20 text-accent-700 dark:text-accent-300 rounded px-1">excursion</span>
                                )}
                              </span>
                            ))}
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
            {dayPlansGenerating && (!dayPlans || dayPlans.length === 0) && (
              <div className="space-y-3 mt-4">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-32 rounded-lg bg-surface-muted animate-pulse" />
                ))}
              </div>
            )}
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
                          className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold transition-colors ${
                            dp.is_excursion
                              ? 'bg-accent-100 dark:bg-accent-900/40 text-accent-700 dark:text-accent-300 ring-1 ring-accent-400 hover:bg-accent-200 dark:hover:bg-accent-800/50'
                              : 'bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 hover:bg-primary-200 dark:hover:bg-primary-800/50'
                          }`}
                          title={`Day ${dp.day_number} of ${dayPlans.length}: ${dp.theme}${dp.is_excursion ? ' (Excursion)' : ''}`}
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
                <div key={`city-${i}-${allExpanded}`} className="scroll-reveal">
                  <CompactCityCard
                    city={city}
                    index={i}
                    departureLeg={departureLeg}
                    dayPlans={cityDayPlans}
                    tips={tips}
                    defaultExpanded={allExpanded}
                    hideHighlights={!!(dayPlans && dayPlans.length > 0)}
                    dailyBudget={dailyBudget}
                    totalDays={dayPlans?.length || 0}
                    onChatAbout={handleChatAbout}
                    onRemoveActivity={handleRemoveActivity}
                    onAdjustDuration={handleAdjustDuration}
                    onReorder={handleReorder}
                    recentChanges={recentChanges}
                    adjustingActivityId={adjustingActivityId}
                    removingActivityId={removingActivityId}
                  />
                </div>
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
            <BudgetSummary costBreakdown={costBreakdown} totalDays={dayPlans.length} travelers={travelers} />
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

      {/* Scroll-to-top button */}
      {showScrollTop && (
        <button
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          className="fixed bottom-6 right-6 z-40 rounded-full bg-primary-600 text-white shadow-lg p-3 hover:bg-primary-700 transition-all animate-fade-in-up"
          aria-label="Scroll to top"
        >
          <ChevronUp className="h-5 w-5" />
        </button>
      )}
    </div>
  );
}
