/**
 * ItineraryInputForm - Form for single-city itinerary generation
 * Matches the design language of JourneyInputForm
 */
import { useState, useCallback } from 'react';
import { MapPin, Calendar, Sparkles, Zap, AlertCircle } from 'lucide-react';
import type { ItineraryRequest, Pace } from '@/types/itinerary';
import { INTERESTS } from '@/types/itinerary';
import { headerGradients } from '@/styles';

interface ItineraryInputFormProps {
  onSubmit: (request: ItineraryRequest) => void;
  loading: boolean;
  error: string | null;
}

export function ItineraryInputForm({ onSubmit, loading, error }: ItineraryInputFormProps) {
  const [destination, setDestination] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [selectedInterests, setSelectedInterests] = useState<string[]>([]);
  const [pace, setPace] = useState<Pace>('moderate');

  // Validation
  const isValid = destination.trim().length >= 2 && 
                  startDate && 
                  endDate && 
                  selectedInterests.length >= 1 &&
                  new Date(endDate) >= new Date(startDate);

  const toggleInterest = useCallback((id: string) => {
    setSelectedInterests(prev => 
      prev.includes(id) 
        ? prev.filter(i => i !== id)
        : prev.length < 5 ? [...prev, id] : prev
    );
  }, []);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid || loading) return;

    const request: ItineraryRequest = {
      destination: destination.trim(),
      start_date: startDate,
      end_date: endDate,
      interests: selectedInterests,
      pace,
      travel_mode: 'WALK',
      mode: 'fast',
    };

    onSubmit(request);
  }, [destination, startDate, endDate, selectedInterests, pace, isValid, loading, onSubmit]);

  // Get min date (today)
  const today = new Date().toISOString().split('T')[0];

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-red-800">Generation Error</p>
            <p className="text-sm text-red-600 mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Destination Card */}
      <div className="bg-white rounded-2xl shadow-lg overflow-hidden border border-gray-100">
        <div 
          className="text-white p-4"
          style={{ background: `linear-gradient(to right, ${headerGradients.journey.from}, ${headerGradients.journey.to})` }}
        >
          <div className="flex items-center gap-2">
            <MapPin className="h-5 w-5" />
            <h3 className="font-semibold">Destination</h3>
          </div>
        </div>
        <div className="p-5">
          <input
            type="text"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            placeholder="e.g., Paris, France or Tokyo, Japan"
            className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors text-lg"
            disabled={loading}
          />
          <p className="text-xs text-gray-500 mt-2">Enter a city and country for best results</p>
        </div>
      </div>

      {/* Dates Card */}
      <div className="bg-white rounded-2xl shadow-lg overflow-hidden border border-gray-100">
        <div 
          className="text-white p-4"
          style={{ background: `linear-gradient(to right, ${headerGradients.dayPlan.from}, ${headerGradients.dayPlan.to})` }}
        >
          <div className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            <h3 className="font-semibold">Trip Dates</h3>
          </div>
        </div>
        <div className="p-5">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Start Date</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                min={today}
                className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
                disabled={loading}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">End Date</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                min={startDate || today}
                className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
                disabled={loading}
              />
            </div>
          </div>
          {startDate && endDate && new Date(endDate) < new Date(startDate) && (
            <p className="text-xs text-red-500 mt-2 flex items-center gap-1">
              <AlertCircle className="h-3 w-3" />
              End date must be after start date
            </p>
          )}
        </div>
      </div>

      {/* Interests Card */}
      <div className="bg-white rounded-2xl shadow-lg overflow-hidden border border-gray-100">
        <div 
          className="text-white p-4"
          style={{ background: `linear-gradient(to right, ${headerGradients.accent.from}, ${headerGradients.accent.to})` }}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5" />
              <h3 className="font-semibold">Interests</h3>
            </div>
            <span className="text-sm opacity-90">{selectedInterests.length}/5 selected</span>
          </div>
        </div>
        <div className="p-5">
          <div className="flex flex-wrap gap-2">
            {INTERESTS.map((interest) => (
              <button
                key={interest.id}
                type="button"
                onClick={() => toggleInterest(interest.id)}
                disabled={loading}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                  selectedInterests.includes(interest.id)
                    ? 'text-white shadow-md scale-105'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                } disabled:opacity-50`}
                style={selectedInterests.includes(interest.id) ? { backgroundColor: headerGradients.journey.from } : {}}
              >
                <span className="mr-1.5">{interest.icon}</span>
                {interest.label}
              </button>
            ))}
          </div>
          {selectedInterests.length === 0 && (
            <p className="text-xs text-gray-500 mt-3">Select 1-5 interests to personalize your itinerary</p>
          )}
        </div>
      </div>

      {/* Pace Card */}
      <div className="bg-white rounded-2xl shadow-lg overflow-hidden border border-gray-100">
        <div 
          className="text-white p-4"
          style={{ background: `linear-gradient(to right, ${headerGradients.rose.from}, ${headerGradients.rose.to})` }}
        >
          <div className="flex items-center gap-2">
            <Zap className="h-5 w-5" />
            <h3 className="font-semibold">Trip Pace</h3>
          </div>
        </div>
        <div className="p-5">
          <div className="grid grid-cols-3 gap-3">
            {(['relaxed', 'moderate', 'packed'] as const).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setPace(p)}
                disabled={loading}
                className={`p-4 rounded-xl border-2 text-center transition-all ${
                  pace === p
                    ? 'border-violet-500 bg-violet-50 text-violet-700'
                    : 'border-gray-200 hover:border-gray-300'
                } disabled:opacity-50`}
              >
                <span className="text-2xl mb-1 block">
                  {p === 'relaxed' ? '🧘' : p === 'moderate' ? '🚶' : '🏃'}
                </span>
                <span className="text-sm font-medium capitalize">{p}</span>
                <span className="text-xs text-gray-500 block mt-1">
                  {p === 'relaxed' ? '2-3 activities/day' : p === 'moderate' ? '4-5 activities/day' : '6+ activities/day'}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={!isValid || loading}
        className={`w-full py-4 px-6 rounded-xl font-bold text-lg transition-all flex items-center justify-center gap-3 ${
          isValid && !loading
            ? 'text-white hover:shadow-xl hover:scale-[1.02]'
            : 'bg-gray-200 text-gray-500 cursor-not-allowed'
        }`}
        style={isValid && !loading ? { background: `linear-gradient(to right, ${headerGradients.journey.from}, ${headerGradients.journey.to})` } : {}}
      >
        {loading ? (
          <>
            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Generating Your Itinerary...
          </>
        ) : (
          <>
            <Sparkles className="h-5 w-5" />
            Generate Itinerary
          </>
        )}
      </button>
    </form>
  );
}
