import { ArrowRight, Car, Train, Bus, Plane, Ship, Clock, Navigation } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import type { TravelLeg } from '@/types';

interface TravelLegCardProps {
  leg: TravelLeg;
}

const TRANSPORT_CONFIG: Record<
  string,
  { icon: typeof Car; color: string; bgColor: string }
> = {
  drive: { icon: Car, color: 'text-blue-600', bgColor: 'bg-blue-50' },
  train: { icon: Train, color: 'text-green-600', bgColor: 'bg-green-50' },
  bus: { icon: Bus, color: 'text-amber-600', bgColor: 'bg-amber-50' },
  flight: { icon: Plane, color: 'text-purple-600', bgColor: 'bg-purple-50' },
  ferry: { icon: Ship, color: 'text-cyan-600', bgColor: 'bg-cyan-50' },
};

function formatDuration(hours: number): string {
  if (hours < 1) {
    return `${Math.round(hours * 60)} min`;
  }
  const wholeHours = Math.floor(hours);
  const minutes = Math.round((hours - wholeHours) * 60);
  return minutes > 0 ? `${wholeHours}h ${minutes}m` : `${wholeHours}h`;
}

export function TravelLegCard({ leg }: TravelLegCardProps) {
  const config = TRANSPORT_CONFIG[leg.mode] ?? TRANSPORT_CONFIG.drive;
  const TransportIcon = config.icon;

  return (
    <div className="relative my-2 mx-4">
      {/* Vertical connector lines */}
      <div className="absolute left-1/2 -top-2 h-2 w-px bg-border-default" aria-hidden="true" />
      <div className="absolute left-1/2 -bottom-2 h-2 w-px bg-border-default" aria-hidden="true" />

      {/* Card */}
      <div
        className={`flex items-center gap-3 rounded-lg border border-border-default ${config.bgColor} px-4 py-3`}
      >
        {/* Transport icon */}
        <div
          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface ${config.color} shadow-sm`}
        >
          <TransportIcon className="h-4 w-4" />
        </div>

        {/* Route info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 text-sm font-medium text-text-primary">
            <span className="truncate">{leg.from_city}</span>
            <ArrowRight className="h-3.5 w-3.5 shrink-0 text-text-muted" />
            <span className="truncate">{leg.to_city}</span>
          </div>

          <div className="flex items-center gap-2 mt-0.5 text-xs text-text-muted">
            <Badge variant="outline" className="text-[10px] capitalize">
              {leg.mode}
            </Badge>
            <span className="flex items-center gap-0.5">
              <Clock className="h-3 w-3" />
              {formatDuration(leg.duration_hours)}
            </span>
            {leg.distance_km && (
              <>
                <span className="text-border-default">&middot;</span>
                <span className="flex items-center gap-0.5">
                  <Navigation className="h-3 w-3" />
                  {leg.distance_km.toFixed(0)} km
                </span>
              </>
            )}
            {leg.fare && (
              <>
                <span className="text-border-default">&middot;</span>
                <span>{leg.fare}</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Notes / booking tip */}
      {(leg.notes || leg.booking_tip) && (
        <div className="mt-1 px-2">
          {leg.notes && (
            <p className="text-[11px] text-text-muted leading-relaxed">
              {leg.notes}
            </p>
          )}
          {leg.booking_tip && (
            <p className="text-[11px] text-primary-600 leading-relaxed mt-0.5">
              Tip: {leg.booking_tip}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
