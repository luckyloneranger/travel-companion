import { useState, useEffect, useCallback, type KeyboardEvent, type FormEvent } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { MapPin, Calendar, Clock, Sparkles, X, Plus, Loader2, Trash2, FolderOpen } from 'lucide-react';
import { useTripStore } from '@/stores/tripStore';
import { useUIStore } from '@/stores/uiStore';
import type { TripRequest, Pace, TravelMode, TripSummary } from '@/types';

interface InputFormProps {
  onSubmit: (request: TripRequest) => void;
  isLoading?: boolean;
}

const INTEREST_PRESETS: string[] = [
  'food',
  'culture',
  'nature',
  'nightlife',
  'shopping',
  'adventure',
  'history',
  'art',
  'architecture',
];

function getTomorrowDate(): string {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  return tomorrow.toISOString().split('T')[0];
}

export function InputForm({ onSubmit, isLoading = false }: InputFormProps) {
  const [destination, setDestination] = useState('');
  const [origin, setOrigin] = useState('');
  const [startDate, setStartDate] = useState(getTomorrowDate());
  const [totalDays, setTotalDays] = useState(3);
  const [interests, setInterests] = useState<string[]>([]);
  const [pace, setPace] = useState<Pace>('moderate');
  const [interestInput, setInterestInput] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [loadingTripId, setLoadingTripId] = useState<string | null>(null);

  const { savedTrips, loadTrips, loadTrip, deleteTrip } = useTripStore();
  const { setPhase } = useUIStore();

  useEffect(() => {
    loadTrips();
  }, [loadTrips]);

  const addInterest = useCallback(
    (interest: string) => {
      const trimmed = interest.trim().toLowerCase();
      if (trimmed && !interests.includes(trimmed)) {
        setInterests((prev) => [...prev, trimmed]);
      }
      setInterestInput('');
    },
    [interests],
  );

  const removeInterest = useCallback((interest: string) => {
    setInterests((prev) => prev.filter((i) => i !== interest));
  }, []);

  const handleInterestKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        addInterest(interestInput);
      }
    },
    [addInterest, interestInput],
  );

  const handleSubmit = useCallback(
    (e: FormEvent) => {
      e.preventDefault();
      if (!destination.trim()) return;

      const request: TripRequest = {
        destination: destination.trim(),
        origin: origin.trim(),
        start_date: startDate,
        total_days: totalDays,
        interests,
        pace,
        travel_mode: 'WALK' as TravelMode,
        must_include: [],
        avoid: [],
      };

      onSubmit(request);
    },
    [destination, origin, startDate, totalDays, interests, pace, onSubmit],
  );

  const handleLoadTrip = useCallback(
    async (trip: TripSummary) => {
      setLoadingTripId(trip.id);
      try {
        await loadTrip(trip.id);
        setPhase(trip.has_day_plans ? 'day-plans' : 'preview');
      } finally {
        setLoadingTripId(null);
      }
    },
    [loadTrip, setPhase],
  );

  const handleDeleteTrip = useCallback(
    async (e: React.MouseEvent, tripId: string) => {
      e.stopPropagation();
      if (deletingId === tripId) {
        await deleteTrip(tripId);
        setDeletingId(null);
      } else {
        setDeletingId(tripId);
      }
    },
    [deletingId, deleteTrip],
  );

  const formatDate = (isoDate: string) => {
    try {
      return new Date(isoDate).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return isoDate;
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg font-display">
            <Sparkles className="h-5 w-5 text-primary-500" />
            Plan Your Trip
          </CardTitle>
          <CardDescription>
            Tell us where you want to go and we'll create a personalized itinerary.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Destination */}
            <div className="space-y-2">
              <label
                htmlFor="destination"
                className="text-sm font-medium text-text-primary flex items-center gap-1.5"
              >
                <MapPin className="h-4 w-4 text-text-muted" />
                Destination
                <span className="text-destructive">*</span>
              </label>
              <Input
                id="destination"
                placeholder="e.g. Tokyo, Paris, New York"
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>

            {/* Origin */}
            <div className="space-y-2">
              <label
                htmlFor="origin"
                className="text-sm font-medium text-text-primary flex items-center gap-1.5"
              >
                <MapPin className="h-4 w-4 text-text-muted" />
                Starting From
                <span className="text-xs text-text-muted font-normal">(optional)</span>
              </label>
              <Input
                id="origin"
                placeholder="e.g. San Francisco, London"
                value={origin}
                onChange={(e) => setOrigin(e.target.value)}
                disabled={isLoading}
              />
            </div>

            {/* Date and Duration row */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label
                  htmlFor="start-date"
                  className="text-sm font-medium text-text-primary flex items-center gap-1.5"
                >
                  <Calendar className="h-4 w-4 text-text-muted" />
                  Start Date
                </label>
                <Input
                  id="start-date"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  min={getTomorrowDate()}
                  disabled={isLoading}
                />
              </div>

              <div className="space-y-2">
                <label
                  htmlFor="duration"
                  className="text-sm font-medium text-text-primary flex items-center gap-1.5"
                >
                  <Clock className="h-4 w-4 text-text-muted" />
                  Duration (days)
                </label>
                <Input
                  id="duration"
                  type="number"
                  min={1}
                  max={21}
                  value={totalDays}
                  onChange={(e) =>
                    setTotalDays(
                      Math.max(1, Math.min(21, parseInt(e.target.value, 10) || 1)),
                    )
                  }
                  disabled={isLoading}
                />
              </div>
            </div>

            {/* Pace */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-text-primary">Pace</label>
              <Select
                value={pace}
                onValueChange={(value) => setPace(value as Pace)}
                disabled={isLoading}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select pace" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="relaxed">
                    Relaxed -- fewer stops, more free time
                  </SelectItem>
                  <SelectItem value="moderate">
                    Moderate -- balanced schedule
                  </SelectItem>
                  <SelectItem value="packed">
                    Packed -- maximize sightseeing
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Interests */}
            <div className="space-y-3">
              <label className="text-sm font-medium text-text-primary">Interests</label>

              {/* Preset chips */}
              <div className="flex flex-wrap gap-2">
                {INTEREST_PRESETS.map((preset) => {
                  const isSelected = interests.includes(preset);
                  return (
                    <button
                      key={preset}
                      type="button"
                      disabled={isLoading}
                      onClick={() =>
                        isSelected ? removeInterest(preset) : addInterest(preset)
                      }
                      className={`
                        inline-flex items-center rounded-full px-3 py-1 text-xs font-medium
                        border transition-colors cursor-pointer
                        disabled:opacity-50 disabled:cursor-not-allowed
                        ${
                          isSelected
                            ? 'bg-primary-100 border-primary-300 text-primary-700'
                            : 'bg-surface border-border-default text-text-secondary hover:bg-surface-muted hover:border-border-default'
                        }
                      `}
                    >
                      {isSelected ? (
                        <X className="h-3 w-3 mr-1" />
                      ) : (
                        <Plus className="h-3 w-3 mr-1" />
                      )}
                      {preset}
                    </button>
                  );
                })}
              </div>

              {/* Custom interest input */}
              <div className="flex gap-2">
                <Input
                  placeholder="Add custom interest..."
                  value={interestInput}
                  onChange={(e) => setInterestInput(e.target.value)}
                  onKeyDown={handleInterestKeyDown}
                  disabled={isLoading}
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => addInterest(interestInput)}
                  disabled={isLoading || !interestInput.trim()}
                  className="h-9"
                >
                  <Plus className="h-4 w-4" />
                  Add
                </Button>
              </div>

              {/* Selected interests display */}
              {interests.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {interests.map((interest) => (
                    <Badge
                      key={interest}
                      variant="secondary"
                      className="gap-1 pr-1"
                    >
                      {interest}
                      <button
                        type="button"
                        onClick={() => removeInterest(interest)}
                        disabled={isLoading}
                        className="ml-0.5 rounded-full p-0.5 hover:bg-muted-foreground/20 transition-colors"
                        aria-label={`Remove ${interest}`}
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              )}
            </div>

            {/* Submit */}
            <Button
              type="submit"
              size="lg"
              className="w-full bg-primary-600 hover:bg-primary-700 text-white"
              disabled={isLoading || !destination.trim()}
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Planning...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  Plan My Trip
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Recent Trips */}
      {savedTrips.length > 0 && (
        <div className="mt-8 space-y-3">
          <h3 className="text-sm font-semibold text-text-muted uppercase tracking-wider px-1 flex items-center gap-1.5">
            <FolderOpen className="h-4 w-4" />
            Recent Trips
          </h3>

          <div className="space-y-2">
            {savedTrips.map((trip) => (
              <Card
                key={trip.id}
                className="cursor-pointer transition-colors hover:border-primary-300 hover:bg-surface-muted/50"
                onClick={() => handleLoadTrip(trip)}
              >
                <CardContent className="flex items-center justify-between gap-3 py-3 px-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm text-text-primary truncate">
                        {trip.theme}
                      </span>
                      {trip.has_day_plans && (
                        <Badge variant="secondary" className="text-[10px] px-1.5 py-0 shrink-0">
                          Day Plans
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-xs text-text-muted">
                      <span className="flex items-center gap-1">
                        <MapPin className="h-3 w-3" />
                        {trip.destination}
                      </span>
                      <span>{trip.cities_count} {trip.cities_count === 1 ? 'city' : 'cities'}</span>
                      <span>{trip.total_days} {trip.total_days === 1 ? 'day' : 'days'}</span>
                      <span className="hidden sm:inline">{formatDate(trip.created_at)}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-1 shrink-0">
                    {loadingTripId === trip.id && (
                      <Loader2 className="h-4 w-4 animate-spin text-primary-500" />
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      className={`h-8 w-8 p-0 ${
                        deletingId === trip.id
                          ? 'text-destructive hover:text-destructive hover:bg-red-100'
                          : 'text-text-muted hover:text-destructive'
                      }`}
                      onClick={(e) => handleDeleteTrip(e, trip.id)}
                      onBlur={() => setDeletingId(null)}
                      title={deletingId === trip.id ? 'Click again to confirm delete' : 'Delete trip'}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
