import { useState, useCallback, useEffect } from 'react';
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
  // Form state
  const [destination, setDestination] = useState('');
  const [origin, setOrigin] = useState('');
  const [startDate, setStartDate] = useState(getTomorrowDate());
  const [totalDays, setTotalDays] = useState(3);
  const [interests, setInterests] = useState<string[]>([]);
  const [pace, setPace] = useState<Pace>('moderate');
  const [mustInclude, setMustInclude] = useState<string[]>([]);
  const [avoid, setAvoid] = useState<string[]>([]);
  const [budget, setBudget] = useState<Budget>('moderate');
  const [budgetUsd, setBudgetUsd] = useState('');
  const [travelers, setTravelers] = useState<Travelers>({ adults: 1, children: 0, infants: 0 });

  // Saved trips
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [loadingTripId, setLoadingTripId] = useState<string | null>(null);

  const { savedTrips, loadTrips, loadTrip, deleteTrip } = useTripStore();
  const { wizardStep, setWizardStep, setPhase } = useUIStore();

  useEffect(() => {
    loadTrips();
  }, [loadTrips]);

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
    onSubmit(request);
  }, [destination, origin, startDate, totalDays, interests, pace, mustInclude, avoid, budget, budgetUsd, onSubmit]);

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
      {savedTrips.length > 0 && (
        <div className="mt-4 space-y-3">
          <h2 className="text-sm font-semibold text-text-muted uppercase tracking-wider px-1 flex items-center gap-1.5">
            <FolderOpen className="h-4 w-4" />
            Recent Trips
          </h2>
          <div className="space-y-2">
            {savedTrips.map((trip) => (
              <Card
                key={trip.id}
                className="cursor-pointer transition-colors hover:border-primary-300 hover:bg-surface-muted/50"
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
