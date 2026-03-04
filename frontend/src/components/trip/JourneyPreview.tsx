import { Suspense, useCallback, useState } from 'react';
import {
  MapPin,
  Calendar,
  Navigation,
  ArrowRight,
  Map,
  MessageSquare,
  Sparkles,
  PlusCircle,
  Copy,
  Check,
  Share2,
  FileDown,
  CalendarPlus,
} from 'lucide-react';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { CityCard } from '@/components/trip/CityCard';
import { TripMap } from '@/components/maps';
import { useTripStore } from '@/stores/tripStore';
import { useUIStore } from '@/stores/uiStore';
import { api } from '@/services/api';

interface JourneyPreviewProps {
  onGenerateDayPlans: () => void;
  onOpenChat: () => void;
  onNewTrip: () => void;
}

export function JourneyPreview({
  onGenerateDayPlans,
  onOpenChat,
  onNewTrip,
}: JourneyPreviewProps) {
  const { journey, tripId } = useTripStore();
  const { showJourneyMap, toggleJourneyMap } = useUIStore();
  const [copied, setCopied] = useState(false);

  const handleCopyItinerary = useCallback(() => {
    if (!journey) return;
    const lines: string[] = [
      `${journey.theme}`,
      journey.summary,
      '',
      `Route: ${journey.origin ? `${journey.origin} → ` : ''}${journey.cities.map(c => c.name).join(' → ')}`,
      `Duration: ${journey.total_days} days | ${journey.cities.length} cities`,
      journey.total_distance_km ? `Distance: ${journey.total_distance_km.toFixed(0)} km` : '',
      '',
    ];

    journey.cities.forEach((city, i) => {
      lines.push(`--- ${city.name}, ${city.country} (${city.days} days) ---`);
      if (city.why_visit) lines.push(city.why_visit);
      if (city.highlights.length > 0) {
        lines.push('Highlights:');
        city.highlights.forEach(h => lines.push(`  • ${h.name}${h.description ? ` - ${h.description}` : ''}`));
      }
      if (city.accommodation) {
        lines.push(`Stay: ${city.accommodation.name}${city.accommodation.rating ? ` (${city.accommodation.rating.toFixed(1)}★)` : ''}`);
      }

      if (i < journey.travel_legs.length) {
        const leg = journey.travel_legs[i];
        lines.push(`→ ${leg.mode} to ${leg.to_city} (${leg.duration_hours.toFixed(1)}h${leg.fare ? `, ${leg.fare}` : ''})`);
      }
      lines.push('');
    });

    navigator.clipboard.writeText(lines.filter(l => l !== undefined).join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [journey]);

  const handleShare = useCallback(async () => {
    if (!tripId) return;
    try {
      const result = await api.shareTrip(tripId);
      const fullUrl = `${window.location.origin}/shared/${result.token}`;
      await navigator.clipboard.writeText(fullUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Share failed:', err);
    }
  }, [tripId]);

  const handleExportPdf = useCallback(async () => {
    if (!tripId) return;
    try {
      await api.exportPdf(tripId);
    } catch (err) {
      console.error('PDF export failed:', err);
    }
  }, [tripId]);

  const handleExportCalendar = useCallback(async () => {
    if (!tripId) return;
    try {
      await api.exportCalendar(tripId);
    } catch (err) {
      console.error('Calendar export failed:', err);
    }
  }, [tripId]);

  if (!journey) return null;

  const cityNames = journey.cities.map((c) => c.name);
  const routeDisplay = journey.origin
    ? [journey.origin, ...cityNames]
    : cityNames;

  return (
    <div className="space-y-6">
      {/* Journey header */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div>
              <CardTitle className="text-xl font-display flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary-500" />
                {journey.theme}
              </CardTitle>
              <CardDescription className="mt-1 leading-relaxed">
                {journey.summary}
              </CardDescription>
            </div>
            {journey.review_score != null && (
              <Badge
                variant={journey.review_score >= 70 ? 'default' : 'outline'}
                className={`shrink-0 text-xs ${
                  journey.review_score >= 80
                    ? 'bg-green-600 dark:bg-green-700 text-white'
                    : journey.review_score >= 70
                      ? 'bg-green-600/80 dark:bg-green-700/80 text-white'
                      : 'border-amber-400 dark:border-amber-600 text-amber-700 dark:text-amber-400'
                }`}
              >
                Score: {journey.review_score}
              </Badge>
            )}
          </div>
        </CardHeader>

        <CardContent className="space-y-4 pt-0">
          {/* Stats row */}
          <div className="flex flex-wrap gap-4 text-sm text-text-secondary">
            <span className="flex items-center gap-1.5">
              <MapPin className="h-4 w-4 text-text-muted" />
              {journey.cities.length}{' '}
              {journey.cities.length === 1 ? 'city' : 'cities'}
            </span>
            <span className="flex items-center gap-1.5">
              <Calendar className="h-4 w-4 text-text-muted" />
              {journey.total_days} days
            </span>
            {journey.total_distance_km != null && (
              <span className="flex items-center gap-1.5">
                <Navigation className="h-4 w-4 text-text-muted" />
                {journey.total_distance_km.toFixed(0)} km total
              </span>
            )}
            {journey.total_travel_hours != null && (
              <span className="flex items-center gap-1.5">
                ~{journey.total_travel_hours.toFixed(1)}h travel
              </span>
            )}
            {journey.route && (
              <span className="flex items-center gap-1.5 text-text-muted">
                Route: {journey.route}
              </span>
            )}
          </div>

          <Separator />

          {/* Route visualization */}
          <div className="flex flex-wrap items-center gap-1.5">
            {routeDisplay.map((name, i) => (
              <span key={`${name}-${i}`} className="flex items-center gap-1.5">
                {i > 0 && (
                  <ArrowRight className="h-3.5 w-3.5 text-text-muted shrink-0" />
                )}
                <Badge
                  variant={i === 0 && journey.origin ? 'outline' : 'secondary'}
                  className="text-xs"
                >
                  {name}
                </Badge>
              </span>
            ))}
          </div>

          <Separator />

          {/* Action buttons */}
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={onGenerateDayPlans}
              size="sm"
              className="bg-primary-600 hover:bg-primary-700 text-white"
            >
              <Calendar className="h-4 w-4" />
              Generate Day Plans
            </Button>
            <Button variant="outline" size="sm" onClick={toggleJourneyMap}>
              <Map className="h-4 w-4" />
              {showJourneyMap ? 'Hide Map' : 'Show Map'}
            </Button>
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
              Share
            </Button>
            <Button variant="outline" size="sm" onClick={handleExportPdf}>
              <FileDown className="h-4 w-4" />
              PDF
            </Button>
            <Button variant="outline" size="sm" onClick={handleExportCalendar}>
              <CalendarPlus className="h-4 w-4" />
              Calendar
            </Button>
            <Button variant="ghost" size="sm" onClick={onNewTrip}>
              <PlusCircle className="h-4 w-4" />
              New Trip
            </Button>
          </div>

          {/* Map */}
          {showJourneyMap && (
            <Suspense fallback={<div className="h-80 rounded-lg bg-surface-muted animate-pulse" />}>
              <div className="h-80 rounded-lg overflow-hidden border border-border-default">
                <TripMap journey={journey} />
              </div>
            </Suspense>
          )}
        </CardContent>
      </Card>

      {/* City cards with integrated transport info */}
      <div className="space-y-4">
        {journey.cities.map((city, i) => {
          // The departure leg from this city to the next stop.
          // travel_legs[i] = leg from cities[i] to cities[i+1] (when no origin)
          // travel_legs[i] = leg from cities[i] to cities[i+1] (when origin, legs[0] is from origin/first city)
          // We simply match: leg whose from_city matches this city's name
          const departureLeg = journey.travel_legs.find(
            (leg) => leg.from_city === city.name,
          );

          return (
            <CityCard
              key={`city-${i}`}
              city={city}
              index={i}
              departureLeg={departureLeg}
            />
          );
        })}
      </div>
    </div>
  );
}
