/**
 * TravelLegCard - Display travel between cities
 * Includes both full card and compact versions
 */
import { memo } from 'react';
import { ArrowRight, Calendar, DollarSign, Info, Route } from 'lucide-react';
import type { V6TravelLeg } from '@/types';
import { transportIcons } from './styles';
import { headerGradients } from '@/styles';

/** Format date for display */
function formatTravelDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

interface TravelLegProps {
  leg: V6TravelLeg;
  travelDate?: string;
}

/** Full travel leg card with details */
export const TravelLegCard = memo(function TravelLegCard({ leg, travelDate }: TravelLegProps) {
  const hasValidDuration = leg.duration_hours && leg.duration_hours > 0;
  const hasValidDistance = leg.distance_km && leg.distance_km > 0;
  
  return (
    <div className="flex gap-4 py-2">
      {/* Timeline spacer */}
      <div className="flex flex-col items-center flex-shrink-0 w-12">
        <div className="w-0.5 flex-1 bg-gradient-to-b from-gray-200 via-blue-300 to-gray-200" />
      </div>

      {/* Travel info */}
      <div className="flex-1 min-w-0">
        <div className="bg-gradient-to-r from-blue-50/80 to-indigo-50/80 border border-blue-100/60 rounded-2xl p-4 flex items-center gap-4">
          {/* Transport icon */}
          <div 
            className="flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center text-white shadow-md"
            style={{ background: headerGradients.transport.css }}
          >
            {transportIcons[leg.mode?.toLowerCase()] || <Route className="h-5 w-5" />}
          </div>

          {/* Route info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 text-sm font-display font-semibold text-gray-900">
              <span className="truncate">{leg.from_city}</span>
              <ArrowRight className="h-3 w-3 text-blue-400 flex-shrink-0" />
              <span className="truncate">{leg.to_city}</span>
            </div>
            <div className="flex items-center gap-3 mt-1 text-xs text-gray-600 flex-wrap">
              {travelDate && (
                <span className="flex items-center gap-1 font-semibold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">
                  <Calendar className="h-3 w-3" />
                  {formatTravelDate(travelDate)}
                </span>
              )}
              {leg.mode && (
                <span className="capitalize font-bold text-blue-600 bg-blue-100 px-2 py-0.5 rounded-full">{leg.mode}</span>
              )}
              {hasValidDuration && (
                <>
                  <span className="text-gray-300">•</span>
                  <span className="font-medium">{leg.duration_hours.toFixed(1)} hours</span>
                </>
              )}
              {hasValidDistance && (
                <>
                  <span className="text-gray-300">•</span>
                  <span className="font-medium">{Math.round(leg.distance_km!)} km</span>
                </>
              )}
            </div>
          </div>

          {/* Cost estimate */}
          {leg.estimated_cost && (
            <div className="flex-shrink-0 text-right">
              <div className="text-xs text-gray-500">Est. cost</div>
              <span className="text-sm font-semibold text-gray-700 flex items-center gap-1">
                <DollarSign className="h-3 w-3" />
                {leg.estimated_cost}
              </span>
            </div>
          )}
        </div>

        {/* Booking tip */}
        {(leg.booking_tip || leg.notes) && (
          <div className="mt-2 flex items-start gap-2 text-xs text-gray-500 px-2 bg-gray-50/80 rounded-xl py-2">
            <Info className="h-3 w-3 flex-shrink-0 mt-0.5 text-blue-400" />
            <span>{leg.booking_tip || leg.notes}</span>
          </div>
        )}
      </div>
    </div>
  );
});

interface TravelLegCompactProps extends TravelLegProps {
  /** Optional color palette from destination city */
  palette?: { gradientFrom: string; gradientTo: string; bgColor: string; borderColor: string; textColor: string };
}

/** Compact travel leg display for between day sections */
export const TravelLegCompact = memo(function TravelLegCompact({ leg, palette }: TravelLegCompactProps) {
  const hasValidData = leg.duration_hours > 0 || (leg.distance_km && leg.distance_km > 0);
  
  // Default to blue gradient if no palette provided
  const gradient = palette 
    ? `linear-gradient(135deg, ${palette.gradientFrom}, ${palette.gradientTo})`
    : headerGradients.transport.css;
  const bgStyle = palette
    ? `linear-gradient(to right, ${palette.bgColor}, white, ${palette.bgColor})`
    : 'linear-gradient(to right, #f8fafc, #eff6ff, #f8fafc)';
  const borderColor = palette?.borderColor || '#bfdbfe';
  const accentColor = palette?.textColor || '#2563eb';
  
  return (
    <div 
      className="flex items-center gap-4 py-3 px-5 rounded-2xl border border-dashed my-3 shadow-sm"
      style={{ background: bgStyle, borderColor }}
    >
      <div 
        className="w-11 h-11 rounded-full flex items-center justify-center text-white shadow-md flex-shrink-0"
        style={{ background: gradient }}
      >
        {transportIcons[leg.mode?.toLowerCase()] || <Route className="h-5 w-5" />}
      </div>
      <div className="flex-1 flex items-center gap-3 text-sm flex-wrap">
        <span className="text-gray-700 font-display font-semibold">
          Travel to <span style={{ color: accentColor }}>{leg.to_city}</span>
        </span>
        {leg.mode && (
          <>
            <span style={{ color: `${accentColor}40` }}>•</span>
            <span 
              className="font-bold capitalize px-2 py-0.5 rounded-full text-xs"
              style={{ backgroundColor: palette?.bgColor || '#dbeafe', color: accentColor }}
            >
              {leg.mode}
            </span>
          </>
        )}
        {hasValidData && (
          <>
            {leg.duration_hours > 0 && (
              <>
                <span className="text-gray-300">•</span>
                <span className="text-gray-600 font-medium">{leg.duration_hours.toFixed(1)} hours</span>
              </>
            )}
            {leg.distance_km && leg.distance_km > 0 && (
              <>
                <span className="text-gray-300">•</span>
                <span className="text-gray-600 font-medium">{Math.round(leg.distance_km)} km</span>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
});
