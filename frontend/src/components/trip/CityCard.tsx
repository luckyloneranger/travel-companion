import { MapPin, Star, Sparkles, Car, Train, Bus, Plane, Ship, Clock, Navigation, ArrowRight } from 'lucide-react';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { CityStop, TravelLeg } from '@/types';

interface CityCardProps {
  city: CityStop;
  index: number;
  departureLeg?: TravelLeg;
}

const TRANSPORT_CONFIG: Record<
  string,
  { icon: typeof Car; color: string; bgColor: string }
> = {
  drive: { icon: Car, color: 'text-blue-600 dark:text-blue-400', bgColor: 'bg-blue-50 dark:bg-blue-950/30' },
  train: { icon: Train, color: 'text-green-600 dark:text-green-400', bgColor: 'bg-green-50 dark:bg-green-950/30' },
  bus: { icon: Bus, color: 'text-amber-600 dark:text-amber-400', bgColor: 'bg-amber-50 dark:bg-amber-950/30' },
  flight: { icon: Plane, color: 'text-purple-600 dark:text-purple-400', bgColor: 'bg-purple-50 dark:bg-purple-950/30' },
  ferry: { icon: Ship, color: 'text-cyan-600 dark:text-cyan-400', bgColor: 'bg-cyan-50 dark:bg-cyan-950/30' },
};

function formatDuration(hours: number): string {
  if (hours < 1) {
    return `${Math.round(hours * 60)} min`;
  }
  const wholeHours = Math.floor(hours);
  const minutes = Math.round((hours - wholeHours) * 60);
  return minutes > 0 ? `${wholeHours}h ${minutes}m` : `${wholeHours}h`;
}

function RatingStars({ rating }: { rating: number }) {
  const fullStars = Math.floor(rating);
  const hasHalf = rating - fullStars >= 0.5;
  const stars: string[] = [];

  for (let i = 0; i < fullStars; i++) stars.push('full');
  if (hasHalf) stars.push('half');
  while (stars.length < 5) stars.push('empty');

  return (
    <div className="flex items-center gap-0.5">
      {stars.map((type, i) => (
        <Star
          key={i}
          className={`h-3 w-3 ${
            type === 'full'
              ? 'fill-accent-400 text-accent-400'
              : type === 'half'
                ? 'fill-accent-400/50 text-accent-400'
                : 'text-border-default'
          }`}
        />
      ))}
    </div>
  );
}

export function CityCard({ city, index, departureLeg }: CityCardProps) {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/40 text-sm font-bold text-primary-700 dark:text-primary-300">
              {index + 1}
            </div>
            <div>
              <CardTitle className="text-base font-display break-words">
                {city.name}, {city.country}
              </CardTitle>
              <CardDescription className="text-xs">
                {city.days} {city.days === 1 ? 'day' : 'days'}
              </CardDescription>
            </div>
          </div>
          {city.best_time_to_visit && (
            <Badge variant="outline" className="text-xs shrink-0">
              Best: {city.best_time_to_visit}
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-0">
        {/* Why visit */}
        {city.why_visit && (
          <p className="text-sm text-text-secondary leading-relaxed break-words">
            {city.why_visit}
          </p>
        )}

        {/* Highlights */}
        {city.highlights.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles className="h-3 w-3" />
              Highlights
            </h4>
            <div className="grid gap-1.5">
              {city.highlights.map((highlight) => (
                <div
                  key={highlight.name}
                  className="flex flex-wrap items-start justify-between gap-x-2 gap-y-1 rounded-md border border-border-default bg-surface-dim px-3 py-2"
                >
                  <div className="min-w-0 flex-1">
                    <span className="text-sm font-medium text-text-primary break-words">
                      {highlight.name}
                    </span>
                    {highlight.description && (
                      <span className="text-xs text-text-muted block break-words">
                        {highlight.description}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {highlight.suggested_duration_hours && (
                      <span className="text-xs text-text-muted">
                        ~{highlight.suggested_duration_hours}h
                      </span>
                    )}
                    <Badge variant="secondary" className="text-xs capitalize">
                      {highlight.category}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Accommodation */}
        {city.accommodation && (
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider flex items-center gap-1.5">
              <MapPin className="h-3 w-3" />
              Accommodation
            </h4>
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
                <p className="text-sm font-semibold text-text-primary truncate">
                  {city.accommodation.name}
                </p>
                {city.accommodation.address && (
                  <p className="text-xs text-text-muted truncate">
                    {city.accommodation.address}
                  </p>
                )}
                <div className="flex items-center gap-2 mt-1">
                  {city.accommodation.rating && (
                    <RatingStars rating={city.accommodation.rating} />
                  )}
                  {city.accommodation.rating && (
                    <span className="text-xs text-text-secondary">
                      {city.accommodation.rating.toFixed(1)}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Travel to next city */}
        {departureLeg && (() => {
          const config = TRANSPORT_CONFIG[departureLeg.mode] ?? TRANSPORT_CONFIG.drive;
          const TransportIcon = config.icon;
          return (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider flex items-center gap-1.5">
                <ArrowRight className="h-3 w-3" />
                Next
              </h4>
              <div className={`flex items-center gap-3 rounded-md ${config.bgColor} px-3 py-2.5`}>
                <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface shadow-sm ${config.color}`}>
                  <TransportIcon className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-text-primary">
                    <span className="truncate">{departureLeg.from_city}</span>
                    <ArrowRight className="h-3 w-3 shrink-0 text-text-muted" />
                    <span className="truncate">{departureLeg.to_city}</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 mt-0.5 text-xs text-text-muted">
                    <Badge variant="outline" className="text-xs capitalize px-1.5 py-0">
                      {departureLeg.mode}
                    </Badge>
                    <span className="flex items-center gap-0.5">
                      <Clock className="h-3 w-3" />
                      {formatDuration(departureLeg.duration_hours)}
                    </span>
                    {departureLeg.distance_km != null && (
                      <>
                        <span className="text-border-default">&middot;</span>
                        <span className="flex items-center gap-0.5">
                          <Navigation className="h-3 w-3" />
                          {departureLeg.distance_km.toFixed(0)} km
                        </span>
                      </>
                    )}
                    {departureLeg.fare && (
                      <>
                        <span className="text-border-default">&middot;</span>
                        <span>{departureLeg.fare}</span>
                      </>
                    )}
                  </div>
                  {departureLeg.notes && (
                    <p className="text-xs text-text-muted mt-1 leading-relaxed break-words">{departureLeg.notes}</p>
                  )}
                  {departureLeg.booking_tip && (
                    <p className="text-xs text-primary-600 dark:text-primary-400 mt-0.5 leading-relaxed break-words">
                      Tip: {departureLeg.booking_tip}
                    </p>
                  )}
                </div>
              </div>
            </div>
          );
        })()}
      </CardContent>
    </Card>
  );
}
