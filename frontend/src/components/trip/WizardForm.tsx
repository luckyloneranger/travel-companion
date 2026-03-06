import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FolderOpen, MapPin, Loader2, Trash2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { WizardStepper } from '@/components/trip/WizardStepper';
import {
  WizardStepWhere,
  WizardStepWhen,
  WizardStepStyle,
  WizardStepBudget,
  WizardStepReview,
} from '@/components/trip/wizard';
import { useTripStore } from '@/stores/tripStore';
import { useUIStore } from '@/stores/uiStore';
import { useAuthStore } from '@/stores/authStore';
import type { TripRequest, TripSummary, Pace, Budget, Travelers } from '@/types';

function getTomorrowDate(): string {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return d.toISOString().split('T')[0];
}

function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

interface WizardFormProps {
  onSubmit: (request: TripRequest) => void;
  isLoading?: boolean;
}

export function WizardForm({ onSubmit, isLoading = false }: WizardFormProps) {
  const navigate = useNavigate();

  // Restore wizard state from sessionStorage if available
  const saved = (() => {
    try {
      const raw = sessionStorage.getItem('tc_wizard');
      return raw ? JSON.parse(raw) : null;
    } catch { return null; }
  })();

  // Form state
  const [destination, setDestination] = useState(saved?.destination ?? '');
  const [origin, setOrigin] = useState(saved?.origin ?? '');
  const [startDate, setStartDate] = useState(saved?.startDate ?? getTomorrowDate());
  const [totalDays, setTotalDays] = useState(saved?.totalDays ?? 3);
  const [interests, setInterests] = useState<string[]>(saved?.interests ?? []);
  const [pace, setPace] = useState<Pace>(saved?.pace ?? 'moderate');
  const [mustInclude, setMustInclude] = useState<string[]>(saved?.mustInclude ?? []);
  const [avoid, setAvoid] = useState<string[]>(saved?.avoid ?? []);
  const [budget, setBudget] = useState<Budget>(saved?.budget ?? 'moderate');
  const [budgetUsd, setBudgetUsd] = useState(saved?.budgetUsd ?? '');
  const [travelers, setTravelers] = useState<Travelers>(saved?.travelers ?? { adults: 1, children: 0, infants: 0 });

  // Persist wizard state on change
  useEffect(() => {
    sessionStorage.setItem('tc_wizard', JSON.stringify({
      destination, origin, startDate, totalDays, interests, pace,
      mustInclude, avoid, budget, budgetUsd, travelers,
    }));
  }, [destination, origin, startDate, totalDays, interests, pace, mustInclude, avoid, budget, budgetUsd, travelers]);

  // Saved trips
  const [loadingTripId, setLoadingTripId] = useState<string | null>(null);

  const { savedTrips, loadTrips, loadTrip, deleteTrip } = useTripStore();
  const tripsLoading = useTripStore((s) => s.tripsLoading);
  const { wizardStep, setWizardStep, setPhase } = useUIStore();
  const setStoreTravelers = useTripStore((s) => s.setTravelers);
  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    loadTrips();
  }, [loadTrips, user]);

  const handleNext = useCallback(() => {
    setWizardStep(Math.min(wizardStep + 1, 5));
  }, [wizardStep, setWizardStep]);

  const handleBack = useCallback(() => {
    setWizardStep(Math.max(wizardStep - 1, 1));
  }, [wizardStep, setWizardStep]);

  const handleSelectTemplate = useCallback(
    (template: Partial<TripRequest>) => {
      if (template.destination) setDestination(template.destination);
      if (template.origin) setOrigin(template.origin);
      if (template.total_days) setTotalDays(template.total_days);
      if (template.interests) setInterests(template.interests);
      if (template.pace) setPace(template.pace);
      if (template.budget) setBudget(template.budget);
      if (template.must_include) setMustInclude(template.must_include);
      if (template.avoid) setAvoid(template.avoid);
      if (template.budget_usd) setBudgetUsd(String(template.budget_usd));
      if (template.travelers) setTravelers(template.travelers);
      setWizardStep(5); // Jump to Review
    },
    [setWizardStep],
  );

  const handleSubmit = useCallback(() => {
    if (!destination.trim()) return;
    const request: TripRequest = {
      destination: destination.trim(),
      origin: origin.trim(),
      start_date: startDate,
      total_days: totalDays,
      interests,
      pace,
      must_include: mustInclude,
      avoid,
      budget,
      budget_usd: budgetUsd ? parseFloat(budgetUsd) : undefined,
      travelers,
    };
    setStoreTravelers(travelers);
    onSubmit(request);
  }, [destination, origin, startDate, totalDays, interests, pace, mustInclude, avoid, budget, budgetUsd, onSubmit]);

  const handleLoadTrip = useCallback(
    async (trip: TripSummary) => {
      setLoadingTripId(trip.id);
      try {
        await loadTrip(trip.id);
        setPhase(trip.has_day_plans ? 'day-plans' : 'preview');
        navigate(`/trips/${trip.id}`);
      } catch {
        // loadTrip already logs the error
      } finally {
        setLoadingTripId(null);
      }
    },
    [loadTrip, setPhase],
  );

  const [isDeletingInFlight, setIsDeletingInFlight] = useState(false);

  const handleDeleteTrip = useCallback(
    async (e: React.MouseEvent, tripId: string) => {
      e.stopPropagation();
      if (!window.confirm('Delete this trip? This cannot be undone.')) return;
      setIsDeletingInFlight(true);
      try {
        await deleteTrip(tripId);
      } catch {
        // Error already surfaced via uiStore
      }
      setIsDeletingInFlight(false);
    },
    [deleteTrip],
  );

  return (
    <div className="space-y-8">
      {/* Tagline */}
      <div className="text-center">
        <p className="text-sm text-text-muted">
          AI plans your perfect multi-city trip in minutes
        </p>
      </div>

      {/* Stepper */}
      <WizardStepper currentStep={wizardStep} onStepClick={setWizardStep} />

      {/* Current step */}
      <div className="animate-fade-in-up">
        {wizardStep === 1 && (
          <WizardStepWhere
            destination={destination}
            origin={origin}
            onDestinationChange={setDestination}
            onOriginChange={setOrigin}
            onSelectTemplate={handleSelectTemplate}
            onNext={handleNext}
          />
        )}
        {wizardStep === 2 && (
          <WizardStepWhen
            startDate={startDate}
            totalDays={totalDays}
            destination={destination}
            travelers={travelers}
            onStartDateChange={setStartDate}
            onTotalDaysChange={setTotalDays}
            onTravelersChange={setTravelers}
            onNext={handleNext}
            onBack={handleBack}
          />
        )}
        {wizardStep === 3 && (
          <WizardStepStyle
            interests={interests}
            pace={pace}
            mustInclude={mustInclude}
            avoid={avoid}
            onInterestsChange={setInterests}
            onPaceChange={setPace}
            onMustIncludeChange={setMustInclude}
            onAvoidChange={setAvoid}
            onNext={handleNext}
            onBack={handleBack}
          />
        )}
        {wizardStep === 4 && (
          <WizardStepBudget
            budget={budget}
            budgetUsd={budgetUsd}
            totalDays={totalDays}
            onBudgetChange={setBudget}
            onBudgetUsdChange={setBudgetUsd}
            onNext={handleNext}
            onBack={handleBack}
          />
        )}
        {wizardStep === 5 && (
          <WizardStepReview
            destination={destination}
            origin={origin}
            startDate={startDate}
            totalDays={totalDays}
            interests={interests}
            pace={pace}
            mustInclude={mustInclude}
            avoid={avoid}
            budget={budget}
            budgetUsd={budgetUsd}
            travelers={travelers}
            isLoading={isLoading}
            onEditStep={setWizardStep}
            onSubmit={handleSubmit}
            onBack={handleBack}
          />
        )}
      </div>

      {/* Recent Trips */}
      {tripsLoading && savedTrips.length === 0 ? (
        <div className="mt-4 space-y-3">
          <h2 className="text-sm font-semibold text-text-muted uppercase tracking-wider px-1 flex items-center gap-1.5">
            <FolderOpen className="h-4 w-4" />
            Recent Trips
          </h2>
          <div className="space-y-2">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-20 rounded-lg bg-surface-muted animate-pulse" />
            ))}
          </div>
        </div>
      ) : savedTrips.length > 0 ? (
        <div className="mt-4 space-y-3">
          <h2 className="text-sm font-semibold text-text-muted uppercase tracking-wider px-1 flex items-center gap-1.5">
            <FolderOpen className="h-4 w-4" />
            Recent Trips
          </h2>
          <div className="space-y-2">
            {savedTrips.map((trip) => (
              <Card
                key={trip.id}
                className="cursor-pointer transition-colors hover:border-primary-300 hover:bg-surface-muted/50 focus-visible:ring-2 focus-visible:ring-primary-500/50 focus-visible:rounded-lg"
                role="button"
                tabIndex={0}
                onClick={() => handleLoadTrip(trip)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleLoadTrip(trip);
                  }
                }}
              >
                <CardContent className="flex items-center justify-between gap-3 py-3 px-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm text-text-primary truncate">
                        {trip.theme}
                      </span>
                      {trip.has_day_plans && (
                        <Badge variant="secondary" className="text-xs px-1.5 py-0 shrink-0">
                          Day Plans
                        </Badge>
                      )}
                    </div>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-text-muted">
                      <span className="flex items-center gap-1">
                        <MapPin className="h-3 w-3 shrink-0" />
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
                      className="h-8 w-8 p-0 text-text-muted hover:text-destructive"
                      onClick={(e) => handleDeleteTrip(e, trip.id)}
                      disabled={isDeletingInFlight}
                      title="Delete trip"
                    >
                      {isDeletingInFlight
                        ? <Loader2 className="h-4 w-4 animate-spin" />
                        : <Trash2 className="h-4 w-4" />}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ) : user ? (
        <div className="mt-4 text-center py-6 text-text-muted">
          <FolderOpen className="h-8 w-8 mx-auto mb-2 opacity-40" />
          <p className="text-sm">No trips yet. Plan your first adventure above!</p>
        </div>
      ) : null}
    </div>
  );
}
