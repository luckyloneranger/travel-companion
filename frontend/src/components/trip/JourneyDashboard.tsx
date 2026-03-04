import { Suspense, useCallback, useState } from 'react';
import {
  MapPin, Calendar, Navigation, ArrowRight, Sparkles,
  MessageSquare, PlusCircle, Copy, Check, Share2,
  FileDown, CalendarPlus, ChevronDown, Car, Train, Bus, Plane, Ship,
  Loader2, RefreshCw,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { CompactCityCard } from '@/components/trip/CompactCityCard';
import { BudgetSummary } from '@/components/trip/BudgetSummary';
import { TripMap } from '@/components/maps';
import { useTripStore } from '@/stores/tripStore';
import { useUIStore } from '@/stores/uiStore';
import { api } from '@/services/api';

interface JourneyDashboardProps {
  onGenerateDayPlans: () => void;
  onCancelDayPlans: () => void;
  onOpenChat: () => void;
  onNewTrip: () => void;
}

const TRANSPORT_ICONS: Record<string, typeof Car> = {
  drive: Car, train: Train, bus: Bus, flight: Plane, ferry: Ship,
};

function formatDuration(hours: number): string {
  if (hours < 1) return `${Math.round(hours * 60)}m`;
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  return m > 0 ? `${h}h${m}m` : `${h}h`;
}

export function JourneyDashboard({ onGenerateDayPlans, onCancelDayPlans, onOpenChat, onNewTrip }: JourneyDashboardProps) {
  const { journey, tripId, dayPlans, costBreakdown, tips } = useTripStore();
  const dayPlansGenerating = useUIStore((s) => s.dayPlansGenerating);
  const [copied, setCopied] = useState(false);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [showExport, setShowExport] = useState(false);

  const estimatedTotal = (() => {
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
        // Parse numeric value from fare string like "$30", "~$45", "€25"
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
    navigator.clipboard.writeText(lines.filter(Boolean).join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [journey]);

  const handleShare = useCallback(async () => {
    if (!tripId) return;
    try {
      const result = await api.shareTrip(tripId);
      setShareUrl(`${window.location.origin}/shared/${result.token}`);
    } catch (err) {
      useUIStore.getState().setError(err instanceof Error ? `Share failed: ${err.message}` : 'Share failed');
    }
  }, [tripId]);

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

  if (!journey) return null;

  return (
    <div className="space-y-6">
      {/* Header card */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <CardTitle className="text-xl font-display flex items-center gap-2 min-w-0">
                <Sparkles className="h-5 w-5 text-primary-500 shrink-0" />
                <span className="break-words">{journey.theme}</span>
              </CardTitle>
              <CardDescription className="mt-1 leading-relaxed break-words">
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
            {journey.total_distance_km != null && (
              <span className="flex items-center gap-1.5"><Navigation className="h-4 w-4 text-text-muted" />{journey.total_distance_km.toFixed(0)} km</span>
            )}
            {estimatedTotal > 0 && (
              <span className="flex items-center gap-1.5 font-medium">~${estimatedTotal.toLocaleString()} estimated</span>
            )}
          </div>

          <Separator />

          {/* Route visualization */}
          <div className="flex flex-wrap items-center gap-1.5">
            {journey.origin && (
              <span className="flex items-center gap-1.5">
                <Badge variant="outline" className="text-xs">{journey.origin}</Badge>
                <ArrowRight className="h-3.5 w-3.5 text-text-muted shrink-0" />
              </span>
            )}
            {journey.cities.map((city, i) => {
              const leg = i > 0 ? journey.travel_legs.find(l => l.to_city === city.name) : (journey.origin ? journey.travel_legs.find(l => l.to_city === city.name) : null);
              const TransportIcon = leg ? (TRANSPORT_ICONS[leg.mode] ?? Car) : null;
              return (
                <span key={`${city.name}-${i}`} className="flex items-center gap-1.5">
                  {(i > 0 || journey.origin) && leg && TransportIcon && (
                    <span className="flex items-center gap-0.5 text-xs text-text-muted">
                      <TransportIcon className="h-3 w-3" />
                      <span>{formatDuration(leg.duration_hours)}</span>
                      <ArrowRight className="h-3 w-3 shrink-0" />
                    </span>
                  )}
                  {i > 0 && !leg && (
                    <ArrowRight className="h-3.5 w-3.5 text-text-muted shrink-0" />
                  )}
                  <Badge variant="secondary" className="text-xs">{city.name}</Badge>
                </span>
              );
            })}
          </div>

          <Separator />

          {/* Day plans action button */}
          {dayPlansGenerating ? (
            <Button
              variant="outline"
              size="sm"
              onClick={onCancelDayPlans}
              className="border-primary-300 text-primary-600"
            >
              <Loader2 className="h-4 w-4 animate-spin" />
              Generating Day Plans...
            </Button>
          ) : dayPlans && dayPlans.length > 0 ? (
            <Button
              variant="outline"
              size="sm"
              onClick={onGenerateDayPlans}
            >
              <RefreshCw className="h-4 w-4" />
              Regenerate Day Plans
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

          {/* Secondary actions */}
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={onOpenChat}>
              <MessageSquare className="h-4 w-4" />
              Edit via Chat
            </Button>
            <Button variant="outline" size="sm" onClick={handleCopyItinerary}>
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              {copied ? 'Copied!' : 'Copy'}
            </Button>
            <Button variant="outline" size="sm" onClick={handleShare}>
              <Share2 className="h-4 w-4" />
              {shareUrl ? 'Shared!' : 'Share'}
            </Button>
            <div className="relative">
              <Button variant="outline" size="sm" onClick={() => setShowExport(!showExport)}>
                <FileDown className="h-4 w-4" />
                Export
                <ChevronDown className={`h-3 w-3 transition-transform ${showExport ? 'rotate-180' : ''}`} />
              </Button>
              {showExport && (
                <div className="absolute top-full left-0 mt-1 z-10 rounded-md border border-border-default bg-surface shadow-lg py-1 min-w-[120px]">
                  <button onClick={() => { handleExportPdf(); setShowExport(false); }} className="w-full text-left px-3 py-1.5 text-sm text-text-primary hover:bg-surface-muted flex items-center gap-2">
                    <FileDown className="h-3.5 w-3.5" /> PDF
                  </button>
                  <button onClick={() => { handleExportCalendar(); setShowExport(false); }} className="w-full text-left px-3 py-1.5 text-sm text-text-primary hover:bg-surface-muted flex items-center gap-2">
                    <CalendarPlus className="h-3.5 w-3.5" /> Calendar
                  </button>
                </div>
              )}
            </div>
            <Button variant="ghost" size="sm" onClick={onNewTrip}>
              <PlusCircle className="h-4 w-4" />
              New Trip
            </Button>
          </div>

          {/* Share URL */}
          {shareUrl && (
            <div className="flex items-center gap-2 rounded-md border border-border-default bg-surface-muted px-3 py-2">
              <input type="text" readOnly value={shareUrl} className="flex-1 bg-transparent text-xs text-text-secondary outline-none min-w-0" onFocus={(e) => e.target.select()} />
              <Button variant="ghost" size="sm" onClick={() => { navigator.clipboard.writeText(shareUrl).catch(() => window.prompt('Copy:', shareUrl)); }}>
                <Copy className="h-3.5 w-3.5" /> Copy
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Map — auto-visible */}
      <Suspense fallback={<div className="h-80 rounded-lg bg-surface-muted animate-pulse" />}>
        <div className="h-80 rounded-lg overflow-hidden border border-border-default">
          <TripMap journey={journey} />
        </div>
      </Suspense>

      {/* City cards */}
      <div className="space-y-3">
        {journey.cities.map((city, i) => {
          const departureLeg = journey.travel_legs.find(l => l.from_city === city.name);
          const cityDayPlans = dayPlans?.filter(
            (dp) => dp.city_name.toLowerCase() === city.name.toLowerCase(),
          );
          return (
            <CompactCityCard
              key={`city-${i}`}
              city={city}
              index={i}
              departureLeg={departureLeg}
              dayPlans={cityDayPlans}
              tips={tips}
            />
          );
        })}
      </div>

      {/* Budget summary (after day plans exist) */}
      {costBreakdown && dayPlans && dayPlans.length > 0 && (
        <BudgetSummary costBreakdown={costBreakdown} totalDays={dayPlans.length} />
      )}
    </div>
  );
}
