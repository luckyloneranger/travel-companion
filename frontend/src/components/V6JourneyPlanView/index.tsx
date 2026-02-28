/**
 * V6JourneyPlanView - Display V6 journey plan results
 */
import { useMemo } from 'react';
import {
  MapPin,
  Calendar,
  Sparkles,
  ArrowRight,
  RefreshCw,
  CheckCircle2,
} from 'lucide-react';
import type { V6JourneyPlan, V6DayPlan } from '@/types';
import { cityColorPalettes } from './styles';
import { CityCard } from './CityCard';
import { TravelLegCard } from './TravelLegCard';
import { CityDaySection, type CityDayGroup } from './CityDaySection';

interface V6JourneyPlanViewProps {
  journey: V6JourneyPlan;
  dayPlans?: V6DayPlan[] | null;
  startDate?: string;
  onReset: () => void;
  onGenerateDayPlans?: () => void;
  loading?: boolean;
  generatingDayPlans?: boolean;
}

export function V6JourneyPlanView({
  journey,
  dayPlans,
  startDate,
  onReset,
  onGenerateDayPlans,
  loading = false,
  generatingDayPlans = false
}: V6JourneyPlanViewProps) {
  const hasDayPlans = dayPlans && dayPlans.length > 0;

  // Group day plans by city
  const cityDayGroups = useMemo<CityDayGroup[]>(() => {
    if (!hasDayPlans) return [];

    const groups: CityDayGroup[] = [];
    let currentDayIndex = 0;

    journey.cities.forEach((city, cityIndex) => {
      const cityDays = dayPlans!.slice(currentDayIndex, currentDayIndex + city.days);
      groups.push({
        city,
        cityIndex,
        days: cityDays,
        travelLeg: journey.travel_legs[cityIndex + 1],
        palette: cityColorPalettes[cityIndex % cityColorPalettes.length],
      });
      currentDayIndex += city.days;
    });

    return groups;
  }, [journey, dayPlans, hasDayPlans]);

  return (
    <div className="max-w-4xl mx-auto animate-fade-in">
      {/* Journey Header */}
      <div className="bg-white rounded-2xl shadow-lg overflow-hidden mb-6 border border-gray-100/40">
        <div
          className="text-white p-6 bg-[#C97B5A]"
        >
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="h-5 w-5" />
            <span className="text-sm font-display font-semibold opacity-90">Your Journey</span>
          </div>
          <h1 className="text-2xl font-display font-extrabold tracking-tight">{journey.theme}</h1>
          <p className="mt-2 text-white/80">{journey.summary}</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-px bg-gray-100/60">
          <div className="bg-white p-4 text-center">
            <p className="text-2xl font-display font-extrabold text-[#C97B5A]">{journey.total_days}</p>
            <p className="text-xs text-gray-400 uppercase tracking-wider font-medium">Days</p>
          </div>
          <div className="bg-white p-4 text-center">
            <p className="text-2xl font-display font-extrabold text-[#C97B5A]">{journey.cities.length}</p>
            <p className="text-xs text-gray-400 uppercase tracking-wider font-medium">Cities</p>
          </div>
          <div className="bg-white p-4 text-center">
            <p className="text-2xl font-display font-extrabold text-[#C97B5A]">
              {journey.total_distance_km ? Math.round(journey.total_distance_km) : '—'}
            </p>
            <p className="text-xs text-gray-400 uppercase tracking-wider font-medium">km</p>
          </div>
          <div className="bg-white p-4 text-center">
            <p className="text-2xl font-display font-extrabold text-[#C97B5A]">
              {journey.review_score || '—'}
            </p>
            <p className="text-xs text-gray-400 uppercase tracking-wider font-medium">Score</p>
          </div>
        </div>
      </div>

      {/* Route visualization */}
      <div className="bg-white rounded-2xl p-4 mb-6 shadow-sm border border-gray-100/60">
        <div className="flex items-center gap-1 text-sm overflow-x-auto pb-2 scrollbar-thin scrollbar-hide hover:scrollbar-thin" role="navigation" aria-label="Journey route">
          <div className="flex items-center gap-1.5 px-3 py-2 bg-gray-100/80 rounded-full whitespace-nowrap flex-shrink-0">
            <MapPin className="h-3.5 w-3.5 text-gray-500" />
            <span className="font-display font-semibold text-gray-700 truncate max-w-[120px]">{journey.origin}</span>
          </div>
          {journey.cities.map((city, idx) => {
            const palette = cityColorPalettes[idx % cityColorPalettes.length];
            return (
              <div key={idx} className="flex items-center gap-1 whitespace-nowrap flex-shrink-0">
                <ArrowRight className="h-4 w-4 text-gray-300 flex-shrink-0 mx-1" />
                <div
                  className="flex items-center gap-1.5 px-3 py-2 rounded-full border font-display font-semibold transition-all duration-200 hover:scale-105 hover:shadow-sm"
                  style={{
                    backgroundColor: palette.bgColor,
                    borderColor: palette.borderColor,
                    color: palette.textColor
                  }}
                >
                  <span className="truncate max-w-[100px]">{city.name}</span>
                  <span className="text-xs opacity-60 flex-shrink-0">({city.days}d)</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Day Plans grouped by City */}
      {hasDayPlans && (
        <div className="mb-6">
          <div className="bg-white rounded-2xl shadow-lg overflow-hidden mb-6 border border-gray-100/40">
            <div
              className="text-white p-5 bg-[#8B9E6B]"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center shadow-lg bg-white/25"
                  >
                    <Calendar className="h-6 w-6" />
                  </div>
                  <div>
                    <h2 className="text-xl font-display font-bold">Day-by-Day Itinerary</h2>
                    <p className="text-sm mt-0.5" style={{ color: 'rgba(255,255,255,0.85)' }}>{dayPlans.length} days of curated experiences across {journey.cities.length} destinations</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <p className="text-3xl font-display font-extrabold">{dayPlans.reduce((acc, d) => acc + d.activities.length, 0)}</p>
                    <p className="text-xs uppercase tracking-wider font-medium" style={{ color: 'rgba(255,255,255,0.85)' }}>Activities</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {cityDayGroups.map((group, idx) => (
            <CityDaySection key={idx} group={group} />
          ))}
        </div>
      )}

      {/* Timeline view with cities and travel legs */}
      {!hasDayPlans && (
        <div className="mb-6">
          {journey.cities.map((city, idx) => (
            <div key={idx}>
              <CityCard
                city={city}
                index={idx}
                isLast={idx === journey.cities.length - 1 && !journey.travel_legs[idx]}
              />
              {journey.travel_legs[idx] && (
                <TravelLegCard
                  leg={journey.travel_legs[idx]}
                  travelDate={startDate ? (() => {
                    const start = new Date(startDate);
                    const daysToAdd = journey.cities.slice(0, idx + 1).reduce((sum, c) => sum + c.days, 0);
                    const date = new Date(start);
                    date.setDate(date.getDate() + daysToAdd);
                    return date.toISOString().split('T')[0];
                  })() : undefined}
                />
              )}
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-4 sticky bottom-4 bg-[#F5F0E8] border border-[#E8E0D4] p-4 -mx-4 rounded-2xl shadow-lg">
        <button
          onClick={onReset}
          disabled={loading || generatingDayPlans}
          className="flex-1 py-3 px-6 border border-gray-200/80 text-gray-700 font-display font-medium rounded-xl hover:bg-gray-50 hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 transition-all duration-300 flex items-center justify-center gap-2"
        >
          <RefreshCw className="h-4 w-4" />
          Plan Another Journey
        </button>
        {!hasDayPlans && (
          <button
            onClick={onGenerateDayPlans}
            disabled={!onGenerateDayPlans || generatingDayPlans}
            className={`flex-1 py-3 px-6 bg-[#C97B5A] hover:bg-[#A66244] text-white font-display font-semibold rounded-xl transition-all duration-300 flex items-center justify-center gap-2 ${
              !onGenerateDayPlans || generatingDayPlans ? 'opacity-50 cursor-not-allowed' : 'hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0'
            }`}
            title={generatingDayPlans ? 'Generating day plans...' : 'Create detailed itineraries for each city'}
          >
            {generatingDayPlans ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" />
                Generating Day Plans...
              </>
            ) : (
              <>
                <CheckCircle2 className="h-4 w-4" />
                Generate Day Plans
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}
