import { useState, useRef, useEffect } from 'react';
import { format, addDays } from 'date-fns';
import {
  MapPin,
  Calendar,
  Sparkles,
  Loader2,
  AlertCircle,
  Plane,
  Globe,
} from 'lucide-react';
import type { JourneyRequest, Pace } from '@/types';
import {
  INTERESTS,
  SUGGESTED_REGIONS,
  DAYS_OPTIONS,
} from '@/types';

interface JourneyInputFormProps {
  onSubmit: (request: JourneyRequest) => Promise<void>;
  loading: boolean;
  error?: string | null;
}

export function JourneyInputForm({ onSubmit, loading, error }: JourneyInputFormProps) {
  const [origin, setOrigin] = useState('');
  const [region, setRegion] = useState('');
  const [totalDays, setTotalDays] = useState(7);
  const [startDate, setStartDate] = useState(format(addDays(new Date(), 14), 'yyyy-MM-dd'));
  const [selectedInterests, setSelectedInterests] = useState<string[]>(['food', 'history', 'culture']);
  const [pace, setPace] = useState<Pace>('moderate');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Ref for click-outside detection on region dropdown
  const regionDropdownRef = useRef<HTMLDivElement>(null);

  // Click-outside handler for region dropdown
  useEffect(() => {
    if (!showSuggestions) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (regionDropdownRef.current && !regionDropdownRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };

    // Use mousedown for quicker response
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showSuggestions]);

  const handleInterestToggle = (interestId: string) => {
    setSelectedInterests((prev) =>
      prev.includes(interestId)
        ? prev.filter((i) => i !== interestId)
        : [...prev, interestId]
    );
  };

  const handleRegionSelect = (value: string) => {
    setRegion(value);
    setShowSuggestions(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    if (!origin.trim()) {
      setValidationError('Please enter your starting location');
      return;
    }

    if (!region.trim()) {
      setValidationError('Please enter a destination region');
      return;
    }

    if (selectedInterests.length === 0) {
      setValidationError('Please select at least one interest');
      return;
    }

    await onSubmit({
      origin: origin.trim(),
      destinations: [],
      region: region.trim(),
      total_days: totalDays,
      interests: selectedInterests,
      pace,
      start_date: startDate,
      return_to_origin: true,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-lg border border-gray-100/60 p-8 space-y-7">
      {/* Error Alert (API or validation) */}
      {(error || validationError) && (
        <div className="flex items-start gap-3 p-4 bg-red-50/80 border border-red-200/60 rounded-2xl text-red-700 animate-scale-in">
          <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
          <div>
            <p className="font-display font-semibold">{validationError ? 'Please fix the following' : 'Something went wrong'}</p>
            <p className="text-sm mt-1">{validationError || error}</p>
          </div>
        </div>
      )}

      {/* Origin */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-600 mb-2">
          <Plane className="h-4 w-4 text-[#C97B5A]" />
          Where are you starting from?
        </label>
        <input
          type="text"
          value={origin}
          onChange={(e) => setOrigin(e.target.value)}
          placeholder="e.g., New York, London, Tokyo"
          className="w-full px-4 py-3 border border-gray-200/80 rounded-xl focus:ring-2 focus:ring-[#C97B5A]/20 focus:border-[#C97B5A] transition-all bg-gray-50/50 focus:bg-white"
          required
        />
      </div>

      {/* Destination Region */}
      <div className="relative" ref={regionDropdownRef}>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-600 mb-2">
          <MapPin className="h-4 w-4 text-[#C97B5A]" />
          Where do you want to explore?
        </label>
        <input
          type="text"
          value={region}
          onChange={(e) => {
            setRegion(e.target.value);
            setShowSuggestions(true);
          }}
          onFocus={() => setShowSuggestions(true)}
          placeholder="e.g., Northern Italy, Japanese Alps, Greek Islands"
          className="w-full px-4 py-3 border border-gray-200/80 rounded-xl focus:ring-2 focus:ring-[#C97B5A]/20 focus:border-[#C97B5A] transition-all bg-gray-50/50 focus:bg-white"
          required
          aria-expanded={showSuggestions}
          aria-haspopup="listbox"
          aria-autocomplete="list"
        />

        {/* Region Suggestions Dropdown */}
        {showSuggestions && (
          <div
            className="absolute z-10 w-full mt-2 bg-white/95 border border-gray-200/60 rounded-2xl shadow-xl max-h-60 overflow-y-auto"
            role="listbox"
            aria-label="Suggested regions"
          >
            {SUGGESTED_REGIONS
              .filter((r) => r.label.toLowerCase().includes(region.toLowerCase()) || region === '')
              .map((suggestion) => (
                <button
                  key={suggestion.value}
                  type="button"
                  role="option"
                  onClick={() => handleRegionSelect(suggestion.value)}
                  className="w-full px-4 py-3 text-left hover:bg-primary-50 flex justify-between items-center border-b border-gray-100/60 last:border-0 transition-colors"
                >
                  <span className="font-medium text-gray-900">{suggestion.label}</span>
                  <span className="text-xs text-gray-400">{suggestion.example}</span>
                </button>
              ))}
          </div>
        )}
      </div>

      {/* Trip Duration & Start Date */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="flex items-center gap-2 text-sm font-medium text-gray-600 mb-2">
            <Calendar className="h-4 w-4 text-[#C97B5A]" />
            How many days?
          </label>
          <select
            value={totalDays}
            onChange={(e) => setTotalDays(Number(e.target.value))}
            className="w-full px-4 py-3 border border-gray-200/80 rounded-xl focus:ring-2 focus:ring-[#C97B5A]/20 focus:border-[#C97B5A] transition-all bg-gray-50/50 focus:bg-white"
          >
            {DAYS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="flex items-center gap-2 text-sm font-medium text-gray-600 mb-2">
            <Calendar className="h-4 w-4 text-[#C97B5A]" />
            When?
          </label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            min={format(new Date(), 'yyyy-MM-dd')}
            className="w-full px-4 py-3 border border-gray-200/80 rounded-xl focus:ring-2 focus:ring-[#C97B5A]/20 focus:border-[#C97B5A] transition-all bg-gray-50/50 focus:bg-white"
            required
          />
        </div>
      </div>

      {/* Interests */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-600 mb-3">
          <Sparkles className="h-4 w-4 text-[#C97B5A]" />
          What do you love?
        </label>
        <div className="flex flex-wrap gap-2">
          {INTERESTS.map((interest) => (
            <button
              key={interest.id}
              type="button"
              onClick={() => handleInterestToggle(interest.id)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 ${
                selectedInterests.includes(interest.id)
                  ? 'bg-primary-100 text-primary-700 ring-2 ring-primary-400/40 shadow-sm'
                  : 'bg-gray-50 text-gray-600 hover:bg-gray-100 border border-gray-200/60'
              }`}
            >
              <span className="mr-1.5">{interest.icon}</span>
              {interest.label}
            </button>
          ))}
        </div>
        {selectedInterests.length === 0 && (
          <p className="text-sm text-amber-500 mt-2">
            Select at least one interest to personalize your journey
          </p>
        )}
      </div>

      {/* Pace - Simplified to inline options */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-600 mb-3">
          What's your travel pace?
        </label>
        <div className="flex gap-3">
          {[
            { value: 'relaxed' as Pace, label: '🧘 Relaxed', desc: 'Slow & deep' },
            { value: 'moderate' as Pace, label: '⚡ Moderate', desc: 'Balanced' },
            { value: 'packed' as Pace, label: '🚀 Packed', desc: 'See it all' },
          ].map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setPace(option.value)}
              className={`flex-1 py-3 px-4 rounded-xl text-center transition-all duration-200 ${
                pace === option.value
                  ? 'bg-primary-50 ring-2 ring-primary-400/40 text-primary-700 shadow-sm'
                  : 'bg-gray-50/50 text-gray-600 hover:bg-gray-100 border border-gray-200/60'
              }`}
            >
              <div className="font-display font-semibold">{option.label}</div>
              <div className="text-xs text-gray-400 mt-0.5">{option.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={loading || !origin.trim() || !region.trim() || selectedInterests.length === 0}
        className="w-full py-4 px-6 bg-[#C97B5A] hover:bg-[#A66244] text-white font-display font-semibold rounded-2xl disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 shadow-lg hover:shadow-xl hover:-translate-y-0.5 active:translate-y-0 flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <Loader2 className="h-5 w-5 animate-spin" />
            Crafting your journey...
          </>
        ) : (
          <>
            <Globe className="h-5 w-5" />
            Plan My Journey
          </>
        )}
      </button>
    </form>
  );
}
