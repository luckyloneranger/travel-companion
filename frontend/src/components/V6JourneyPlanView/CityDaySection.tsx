/**
 * CityDaySection - City header with its day cards when day plans are generated
 */
import { memo, useState } from 'react';
import { Calendar, ChevronDown, ChevronUp, MapPin, Star } from 'lucide-react';
import type { V6CityStop, V6DayPlan, V6TravelLeg } from '@/types';
import type { CityColorPalette } from './styles';
import { DayCard } from './DayCard';
import { TravelLegCompact } from './TravelLegCard';

export interface CityDayGroup {
  city: V6CityStop;
  cityIndex: number;
  days: V6DayPlan[];
  travelLeg?: V6TravelLeg;
  palette: CityColorPalette;
}

interface CityDaySectionProps {
  group: CityDayGroup;
}

export const CityDaySection = memo(function CityDaySection({ group }: CityDaySectionProps) {
  const [expanded, setExpanded] = useState(true);
  const { city, cityIndex, days, travelLeg, palette } = group;

  return (
    <div className="mb-8">
      {/* City Header */}
      <div className="rounded-2xl overflow-hidden shadow-lg mb-4 border border-gray-100/40">
        <div
          className="text-white p-6"
          style={{ background: `linear-gradient(135deg, ${palette.gradientFrom}, ${palette.gradientTo})` }}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center font-display font-extrabold text-2xl shadow-lg bg-white/25"
                aria-label={`City ${cityIndex + 1}`}
              >
                {cityIndex + 1}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <MapPin className="h-5 w-5 opacity-90" />
                  <h3 className="text-2xl font-display font-extrabold tracking-tight" style={{ textShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
                    {city.name}
                  </h3>
                  <span className="text-white/80 text-sm font-medium ml-1">{city.country}</span>
                </div>
                <div className="flex items-center gap-3 mt-2 text-sm font-medium" style={{ color: 'rgba(255,255,255,0.9)' }}>
                  <span className="flex items-center gap-1.5 bg-white/15 px-2.5 py-0.5 rounded-full">
                    <Calendar className="h-3.5 w-3.5" />
                    {city.days} {city.days === 1 ? 'day' : 'days'}
                  </span>
                  <span className="flex items-center gap-1.5 bg-white/15 px-2.5 py-0.5 rounded-full">
                    <Star className="h-3.5 w-3.5" />
                    {days.reduce((acc, d) => acc + d.activities.length, 0)} activities
                  </span>
                </div>
              </div>
            </div>
            <button
              onClick={() => setExpanded(!expanded)}
              className="p-2.5 rounded-xl transition-colors"
              style={{ backgroundColor: 'rgba(255,255,255,0.12)' }}
              aria-expanded={expanded}
              aria-label={expanded ? 'Collapse days' : 'Expand days'}
            >
              {expanded ? (
                <ChevronUp className="h-6 w-6" />
              ) : (
                <ChevronDown className="h-6 w-6" />
              )}
            </button>
          </div>
        </div>

        {/* Days List */}
        {expanded && (
          <div className="bg-white p-5 space-y-4">
            {days.map((day, idx) => (
              <DayCard
                key={idx}
                dayPlan={day}
                dayNumberInCity={idx + 1}
                paletteIndex={cityIndex}
                defaultExpanded={idx === 0}
              />
            ))}
          </div>
        )}
      </div>

      {/* Travel Leg to Next City - uses next city's palette for visual continuity */}
      {travelLeg && (
        <TravelLegCompact leg={travelLeg} palette={palette} />
      )}
    </div>
  );
});
