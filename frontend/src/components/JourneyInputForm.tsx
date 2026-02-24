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
      // No max_cities - Scout decides based on days, pace, and region
    });
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-xl p-8 space-y-8">
      {/* Error Alert (API or validation) */}
      {(error || validationError) && (
        <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">
          <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
          <div>
            <p className="font-medium">{validationError ? 'Please fix the following' : 'Something went wrong'}</p>
            <p className="text-sm mt-1">{validationError || error}</p>
          </div>
        </div>
      )}

      {/* Origin */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
          <Plane className="h-4 w-4" />
          Where are you starting from?
        </label>
        <input
          type="text"
          value={origin}
          onChange={(e) => setOrigin(e.target.value)}
          placeholder="e.g., New York, London, Tokyo"
          className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors bg-gray-50"
          required
        />
      </div>

      {/* Destination Region */}
      <div className="relative" ref={regionDropdownRef}>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
          <MapPin className="h-4 w-4" />
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
          className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors bg-gray-50"
          required
          aria-expanded={showSuggestions}
          aria-haspopup="listbox"
          aria-autocomplete="list"
        />
        
        {/* Region Suggestions Dropdown */}
        {showSuggestions && (
          <div 
            className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-xl shadow-lg max-h-60 overflow-y-auto"
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
                  className="w-full px-4 py-3 text-left hover:bg-gray-50 flex justify-between items-center border-b border-gray-100 last:border-0"
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
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
            <Calendar className="h-4 w-4" />
            How many days?
          </label>
          <select
            value={totalDays}
            onChange={(e) => setTotalDays(Number(e.target.value))}
            className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors bg-gray-50"
          >
            {DAYS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
            <Calendar className="h-4 w-4" />
            When?
          </label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            min={format(new Date(), 'yyyy-MM-dd')}
            className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors bg-gray-50"
            required
          />
        </div>
      </div>

      {/* Interests */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-3">
          <Sparkles className="h-4 w-4" />
          What do you love?
        </label>
        <div className="flex flex-wrap gap-2">
          {INTERESTS.map((interest) => (
            <button
              key={interest.id}
              type="button"
              onClick={() => handleInterestToggle(interest.id)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                selectedInterests.includes(interest.id)
                  ? 'bg-primary-100 text-primary-700 ring-2 ring-primary-500'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <span className="mr-1.5">{interest.icon}</span>
              {interest.label}
            </button>
          ))}
        </div>
        {selectedInterests.length === 0 && (
          <p className="text-sm text-amber-600 mt-2">
            Select at least one interest to personalize your journey
          </p>
        )}
      </div>

      {/* Pace - Simplified to inline options */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-3">
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
              className={`flex-1 py-3 px-4 rounded-xl text-center transition-all ${
                pace === option.value
                  ? 'bg-primary-50 ring-2 ring-primary-500 text-primary-700'
                  : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
              }`}
            >
              <div className="font-medium">{option.label}</div>
              <div className="text-xs text-gray-500 mt-0.5">{option.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={loading || !origin.trim() || !region.trim() || selectedInterests.length === 0}
        className="w-full py-4 px-6 bg-gradient-to-r from-primary-600 to-purple-600 hover:from-primary-700 hover:to-purple-700 text-white font-semibold rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-primary-500/25 flex items-center justify-center gap-2"
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
