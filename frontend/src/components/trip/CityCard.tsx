import { MapPin, Star, Sparkles } from 'lucide-react';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { CityStop } from '@/types';

interface CityCardProps {
  city: CityStop;
  index: number;
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

export function CityCard({ city, index }: CityCardProps) {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 text-sm font-bold text-primary-700">
              {index + 1}
            </div>
            <div>
              <CardTitle className="text-base font-display">
                {city.name}, {city.country}
              </CardTitle>
              <CardDescription className="text-xs">
                {city.days} {city.days === 1 ? 'day' : 'days'}
              </CardDescription>
            </div>
          </div>
          {city.best_time_to_visit && (
            <Badge variant="outline" className="text-[10px] shrink-0">
              Best: {city.best_time_to_visit}
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-0">
        {/* Why visit */}
        {city.why_visit && (
          <p className="text-sm text-text-secondary leading-relaxed">
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
                  className="flex items-center justify-between gap-2 rounded-md border border-border-default bg-surface-dim px-3 py-2"
                >
                  <div className="min-w-0">
                    <span className="text-sm font-medium text-text-primary block truncate">
                      {highlight.name}
                    </span>
                    {highlight.description && (
                      <span className="text-xs text-text-muted block truncate">
                        {highlight.description}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {highlight.suggested_duration_hours && (
                      <span className="text-[10px] text-text-muted">
                        ~{highlight.suggested_duration_hours}h
                      </span>
                    )}
                    <Badge variant="secondary" className="text-[10px] capitalize">
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
            <div className="flex items-center gap-3 rounded-md border border-accent-200 bg-accent-50/30 p-3">
              {city.accommodation.photo_url && (
                <img
                  src={city.accommodation.photo_url}
                  alt={city.accommodation.name}
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
      </CardContent>
    </Card>
  );
}
