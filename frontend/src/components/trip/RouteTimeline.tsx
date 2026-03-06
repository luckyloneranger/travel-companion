import { Car, Train, Bus, Plane, Ship, MapPin, Clock, ArrowDown } from 'lucide-react';
import type { JourneyPlan } from '@/types';

interface RouteTimelineProps {
  journey: JourneyPlan;
  onCityClick?: (cityName: string) => void;
}

const TRANSPORT_ICONS: Record<string, typeof Car> = {
  drive: Car, train: Train, bus: Bus, flight: Plane, ferry: Ship,
};

function formatDuration(hours: number): string {
  if (hours < 1) return `${Math.round(hours * 60)}m`;
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

export function RouteTimeline({ journey, onCityClick }: RouteTimelineProps) {
  return (
    <div className="space-y-0">
      {journey.cities.map((city, i) => {
        const leg = journey.travel_legs.find(l => l.from_city === city.name);
        const TransportIcon = leg ? (TRANSPORT_ICONS[leg.mode] ?? Car) : null;
        const isLast = i === journey.cities.length - 1;

        return (
          <div key={i}>
            {/* City node */}
            <button
              type="button"
              onClick={() => onCityClick?.(city.name)}
              className="w-full flex items-start gap-3 p-3 rounded-lg hover:bg-surface-muted/50 transition-colors text-left group focus-visible:ring-2 focus-visible:ring-primary-500/50"
            >
              <div className="flex flex-col items-center shrink-0">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/40 text-sm font-bold text-primary-700 dark:text-primary-300 group-hover:bg-primary-200 dark:group-hover:bg-primary-800/50 transition-colors">
                  {i + 1}
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-semibold text-text-primary">{city.name}</h4>
                  <span className="text-xs text-text-muted">{city.country}</span>
                  <span className="ml-auto text-xs font-medium text-primary-600 dark:text-primary-400 shrink-0">
                    {city.days} {city.days === 1 ? 'day' : 'days'}
                  </span>
                </div>
                {city.why_visit && (
                  <p className="text-xs text-text-secondary mt-0.5 line-clamp-1">{city.why_visit}</p>
                )}
                {city.accommodation?.name && (
                  <p className="text-xs text-text-muted mt-0.5 flex items-center gap-1">
                    <MapPin className="h-3 w-3" />{city.accommodation.name}
                  </p>
                )}
              </div>
            </button>

            {/* Transport leg connector */}
            {!isLast && leg && (
              <div className="flex items-center gap-3 pl-3 py-1">
                <div className="flex flex-col items-center w-8 shrink-0">
                  <div className="w-px h-3 bg-border-default" />
                  <ArrowDown className="h-4 w-4 text-text-muted/50" />
                  <div className="w-px h-3 bg-border-default" />
                </div>
                <div className="flex items-center gap-2 text-xs text-text-muted">
                  {TransportIcon && <TransportIcon className="h-3.5 w-3.5" />}
                  <span className="capitalize">{leg.mode}</span>
                  <span>&middot;</span>
                  <span className="flex items-center gap-0.5">
                    <Clock className="h-3 w-3" />{formatDuration(leg.duration_hours)}
                  </span>
                  {leg.distance_km != null && (
                    <>
                      <span>&middot;</span>
                      <span>{leg.distance_km.toFixed(0)} km</span>
                    </>
                  )}
                  {leg.fare && (
                    <>
                      <span>&middot;</span>
                      <span>{leg.fare}</span>
                    </>
                  )}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
