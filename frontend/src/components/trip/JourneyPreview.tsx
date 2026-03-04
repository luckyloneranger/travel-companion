import type { ReactNode } from 'react';
import { Suspense } from 'react';
import {
  MapPin,
  Calendar,
  Navigation,
  ArrowRight,
  Map,
  MessageSquare,
  Sparkles,
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
import { TravelLegCard } from '@/components/trip/TravelLegCard';
import { TripMap } from '@/components/maps';
import { useTripStore } from '@/stores/tripStore';
import { useUIStore } from '@/stores/uiStore';

interface JourneyPreviewProps {
  onGenerateDayPlans: () => void;
  onOpenChat: () => void;
}

export function JourneyPreview({
  onGenerateDayPlans,
  onOpenChat,
}: JourneyPreviewProps) {
  const { journey } = useTripStore();
  const { showJourneyMap, toggleJourneyMap } = useUIStore();

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
                  journey.review_score >= 70
                    ? 'bg-green-600 text-white'
                    : 'border-amber-400 text-amber-700'
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
              className="bg-primary-600 hover:bg-primary-700 text-white"
            >
              <Calendar className="h-4 w-4" />
              Generate Day Plans
            </Button>
            <Button variant="outline" onClick={toggleJourneyMap}>
              <Map className="h-4 w-4" />
              {showJourneyMap ? 'Hide Map' : 'Show Map'}
            </Button>
            <Button variant="outline" onClick={onOpenChat}>
              <MessageSquare className="h-4 w-4" />
              Edit via Chat
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

      {/* City cards interleaved with travel legs */}
      <div className="space-y-0">
        {(() => {
          // Build an ordered list: [leg?, city, leg?, city, leg?, city, leg?]
          // travel_legs[i] connects stop i to stop i+1 in the full route.
          // If origin is set, the stops are [origin, city0, city1, ...].
          // If no origin, the stops are [city0, city1, ...].
          const hasOrigin = Boolean(journey.origin);
          const elements: ReactNode[] = [];

          journey.cities.forEach((city, i) => {
            // Index into travel_legs for the leg arriving at this city
            const legIndex = hasOrigin ? i : i - 1;
            if (legIndex >= 0 && legIndex < journey.travel_legs.length) {
              elements.push(
                <TravelLegCard
                  key={`leg-${legIndex}`}
                  leg={journey.travel_legs[legIndex]}
                />,
              );
            }
            elements.push(
              <div key={`city-${i}`} className={elements.length > 0 ? 'mt-2' : ''}>
                <CityCard city={city} index={i} />
              </div>,
            );
          });

          // Any remaining legs after the last city (e.g., return to origin)
          const lastUsedLeg = hasOrigin
            ? journey.cities.length - 1
            : journey.cities.length - 2;
          for (
            let j = lastUsedLeg + 1;
            j < journey.travel_legs.length;
            j++
          ) {
            elements.push(
              <TravelLegCard key={`leg-${j}`} leg={journey.travel_legs[j]} />,
            );
          }

          return elements;
        })()}
      </div>
    </div>
  );
}
