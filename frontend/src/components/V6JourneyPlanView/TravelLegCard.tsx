/**
 * TravelLegCard - Display travel between cities
 * Includes both full card and compact versions
 */
import { memo } from 'react';
import { ArrowRight, DollarSign, Info, Route } from 'lucide-react';
import type { V6TravelLeg } from '@/types';
import { transportIcons } from './styles';

interface TravelLegProps {
  leg: V6TravelLeg;
}

/** Full travel leg card with details */
export const TravelLegCard = memo(function TravelLegCard({ leg }: TravelLegProps) {
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
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100 rounded-xl p-4 flex items-center gap-4">
          {/* Transport icon */}
          <div 
            className="flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center text-white shadow-md"
            style={{ background: 'linear-gradient(135deg, #3b82f6, #6366f1)' }}
          >
            {transportIcons[leg.mode?.toLowerCase()] || <Route className="h-5 w-5" />}
          </div>

          {/* Route info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 text-sm font-semibold text-gray-900">
              <span className="truncate">{leg.from_city}</span>
              <ArrowRight className="h-3 w-3 text-blue-400 flex-shrink-0" />
              <span className="truncate">{leg.to_city}</span>
            </div>
            <div className="flex items-center gap-3 mt-1 text-xs text-gray-600">
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
          <div className="mt-2 flex items-start gap-2 text-xs text-gray-500 px-2 bg-gray-50 rounded-lg py-2">
            <Info className="h-3 w-3 flex-shrink-0 mt-0.5 text-blue-400" />
            <span>{leg.booking_tip || leg.notes}</span>
          </div>
        )}
      </div>
    </div>
  );
});

/** Compact travel leg display for between day sections */
export const TravelLegCompact = memo(function TravelLegCompact({ leg }: TravelLegProps) {
  const hasValidData = leg.duration_hours > 0 || (leg.distance_km && leg.distance_km > 0);
  
  return (
    <div className="flex items-center gap-4 py-3 px-5 bg-gradient-to-r from-slate-50 via-blue-50/50 to-slate-50 rounded-xl border border-dashed border-blue-200 my-3">
      <div 
        className="w-11 h-11 rounded-full flex items-center justify-center text-white shadow-md flex-shrink-0"
        style={{ background: 'linear-gradient(135deg, #3b82f6, #6366f1)' }}
      >
        {transportIcons[leg.mode?.toLowerCase()] || <Route className="h-5 w-5" />}
      </div>
      <div className="flex-1 flex items-center gap-3 text-sm flex-wrap">
        <span className="text-gray-700 font-semibold">Next destination</span>
        {leg.mode && (
          <>
            <span className="text-blue-300">•</span>
            <span className="font-bold text-blue-600 capitalize bg-blue-100 px-2 py-0.5 rounded-full text-xs">
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
