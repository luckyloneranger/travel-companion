/**
 * ItineraryView - Display single-city itinerary results
 * 
 * Shows the complete itinerary with:
 * - Destination header with trip summary
 * - Quality score (if available)
 * - Day-by-day activities in expandable cards
 * - Action buttons for reset/export
 * 
 * Design language matches V6JourneyPlanView
 */
import { useMemo } from 'react';
import {
  MapPin,
  Calendar,
  Sparkles,
  RefreshCw,
  Star,
  Award,
} from 'lucide-react';
import type { ItineraryResponse } from '@/types/itinerary';
import { dayColorPalettes, getGradeColor } from './styles';
import { ItineraryDayCard } from './ItineraryDayCard';

interface ItineraryViewProps {
  itinerary: ItineraryResponse;
  onReset: () => void;
  loading?: boolean;
}

export function ItineraryView({ 
  itinerary, 
  onReset, 
  loading = false,
}: ItineraryViewProps) {
  // Calculate stats
  const stats = useMemo(() => {
    const totalActivities = itinerary.days.reduce((acc, day) => acc + day.activities.length, 0);
    const totalDuration = itinerary.days.reduce((acc, day) => 
      acc + day.activities.reduce((a, act) => a + act.duration_minutes, 0), 0
    );
    return { totalActivities, totalDuration };
  }, [itinerary]);

  // Format dates
  const dateRange = useMemo(() => {
    const start = new Date(itinerary.trip_dates.start);
    const end = new Date(itinerary.trip_dates.end);
    const options: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' };
    return `${start.toLocaleDateString('en-US', options)} - ${end.toLocaleDateString('en-US', options)}`;
  }, [itinerary.trip_dates]);

  const gradeColor = getGradeColor(itinerary.quality_score?.grade);

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header Card */}
      <div className="bg-white rounded-2xl shadow-lg overflow-hidden mb-6">
        {/* Gradient Header */}
        <div className="bg-gradient-to-r from-primary-600 via-purple-600 to-pink-500 text-white p-6">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="h-5 w-5" />
            <span className="text-sm font-medium opacity-90">Your Itinerary</span>
          </div>
          
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold flex items-center gap-3">
                <MapPin className="h-7 w-7" />
                {itinerary.destination.name}
              </h1>
              <p className="mt-2 text-white/80 flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                {dateRange}
                <span className="mx-2">•</span>
                {itinerary.trip_dates.duration_days} {itinerary.trip_dates.duration_days === 1 ? 'day' : 'days'}
              </p>
            </div>
            
            {/* Quality Score Badge */}
            {itinerary.quality_score && (
              <div 
                className="flex flex-col items-center px-4 py-2 rounded-xl"
                style={{ 
                  backgroundColor: gradeColor.bg,
                  border: `2px solid ${gradeColor.border}`,
                }}
              >
                <Award className="h-5 w-5 mb-1" style={{ color: gradeColor.text }} />
                <span className="text-2xl font-bold" style={{ color: gradeColor.text }}>
                  {itinerary.quality_score.grade || Math.round(itinerary.quality_score.overall)}
                </span>
                <span className="text-xs" style={{ color: gradeColor.text }}>Quality</span>
              </div>
            )}
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-4 gap-px bg-gray-100">
          <div className="bg-white p-4 text-center">
            <p className="text-2xl font-bold text-primary-600">{itinerary.days.length}</p>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Days</p>
          </div>
          <div className="bg-white p-4 text-center">
            <p className="text-2xl font-bold text-primary-600">{stats.totalActivities}</p>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Activities</p>
          </div>
          <div className="bg-white p-4 text-center">
            <p className="text-2xl font-bold text-primary-600">
              {itinerary.summary.total_distance_km.toFixed(1)}
            </p>
            <p className="text-xs text-gray-500 uppercase tracking-wide">km</p>
          </div>
          <div className="bg-white p-4 text-center">
            <p className="text-2xl font-bold text-primary-600">
              {Math.round(stats.totalDuration / 60)}h
            </p>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Planned</p>
          </div>
        </div>

        {/* Interests covered */}
        {itinerary.summary.interests_covered.length > 0 && (
          <div className="px-6 py-4 border-t border-gray-100">
            <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Interests Covered</p>
            <div className="flex flex-wrap gap-2">
              {itinerary.summary.interests_covered.map((interest, idx) => (
                <span 
                  key={idx}
                  className="px-3 py-1 rounded-full text-sm font-medium capitalize"
                  style={{
                    backgroundColor: dayColorPalettes[idx % dayColorPalettes.length].bgColor,
                    color: dayColorPalettes[idx % dayColorPalettes.length].textColor,
                    border: `1px solid ${dayColorPalettes[idx % dayColorPalettes.length].borderColor}`,
                  }}
                >
                  {interest}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Day Plans Section */}
      <div className="mb-6">
        {/* Section header */}
        <div className="bg-white rounded-2xl shadow-lg overflow-hidden mb-6">
          <div className="bg-gradient-to-r from-emerald-600 to-teal-600 text-white p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div 
                  className="w-12 h-12 rounded-xl flex items-center justify-center shadow-lg"
                  style={{ backgroundColor: 'rgba(255,255,255,0.2)', backdropFilter: 'blur(10px)' }}
                >
                  <Calendar className="h-6 w-6" />
                </div>
                <div>
                  <h2 className="text-xl font-bold">Day-by-Day Itinerary</h2>
                  <p className="text-emerald-100 text-sm mt-0.5">
                    {itinerary.days.length} days of curated experiences in {itinerary.destination.name}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-6">
                <div className="text-right">
                  <p className="text-3xl font-bold">{stats.totalActivities}</p>
                  <p className="text-xs text-emerald-100 uppercase tracking-wide">Activities</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        {/* Day cards */}
        {itinerary.days.map((day, idx) => (
          <ItineraryDayCard 
            key={day.day_number} 
            dayPlan={day}
            palette={dayColorPalettes[idx % dayColorPalettes.length]}
          />
        ))}
      </div>

      {/* Quality Details (if available) */}
      {itinerary.quality_score && (
        <div className="bg-white rounded-2xl shadow-lg overflow-hidden mb-6 p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Star className="h-5 w-5 text-amber-500" />
            Quality Breakdown
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Meal Timing', value: itinerary.quality_score.meal_timing },
              { label: 'Route Efficiency', value: itinerary.quality_score.travel_efficiency },
              { label: 'Variety', value: itinerary.quality_score.variety },
              { label: 'Clustering', value: itinerary.quality_score.geographic_clustering },
            ].map((metric) => (
              <div key={metric.label} className="text-center">
                <div className="relative w-16 h-16 mx-auto mb-2">
                  <svg className="w-16 h-16 transform -rotate-90">
                    <circle
                      cx="32"
                      cy="32"
                      r="28"
                      stroke="#e5e7eb"
                      strokeWidth="6"
                      fill="none"
                    />
                    <circle
                      cx="32"
                      cy="32"
                      r="28"
                      stroke={metric.value >= 80 ? '#10b981' : metric.value >= 60 ? '#f59e0b' : '#ef4444'}
                      strokeWidth="6"
                      fill="none"
                      strokeDasharray={`${(metric.value / 100) * 175.93} 175.93`}
                      strokeLinecap="round"
                    />
                  </svg>
                  <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-gray-700">
                    {Math.round(metric.value)}
                  </span>
                </div>
                <p className="text-xs text-gray-500">{metric.label}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-4 sticky bottom-4 bg-white/80 backdrop-blur-sm p-4 -mx-4 rounded-xl shadow-lg border border-gray-100">
        <button
          onClick={onReset}
          disabled={loading}
          className="flex-1 py-3 px-6 bg-gradient-to-r from-primary-600 to-purple-600 text-white font-semibold rounded-xl hover:shadow-lg hover:scale-[1.02] disabled:opacity-50 transition-all flex items-center justify-center gap-2"
        >
          <RefreshCw className="h-4 w-4" />
          Plan Another Trip
        </button>
      </div>
    </div>
  );
}

export { ItineraryDayCard } from './ItineraryDayCard';
export { ItineraryActivityCard } from './ItineraryActivityCard';
