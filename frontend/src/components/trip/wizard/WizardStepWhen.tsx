import { Calendar, Clock, Users, ArrowLeft, Minus, Plus } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import type { Travelers } from '@/types';

interface WizardStepWhenProps {
  startDate: string;
  totalDays: number;
  destination: string;
  travelers: Travelers;
  onStartDateChange: (value: string) => void;
  onTotalDaysChange: (value: number) => void;
  onTravelersChange: (travelers: Travelers) => void;
  onNext: () => void;
  onBack: () => void;
}

function CounterInput({ label, sublabel, value, min, max, onChange }: {
  label: string;
  sublabel: string;
  value: number;
  min: number;
  max: number;
  onChange: (value: number) => void;
}) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <span className="text-sm font-medium text-text-primary">{label}</span>
        <p className="text-xs text-text-muted">{sublabel}</p>
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => onChange(Math.max(min, value - 1))}
          disabled={value <= min}
          className="flex h-10 w-10 items-center justify-center rounded-full border border-border-default bg-surface text-text-primary disabled:opacity-30 disabled:cursor-not-allowed hover:bg-surface-muted transition-colors"
          aria-label={`Decrease ${label}`}
        >
          <Minus className="h-3.5 w-3.5" />
        </button>
        <span className="w-8 text-center text-sm font-semibold text-text-primary">{value}</span>
        <button
          type="button"
          onClick={() => onChange(Math.min(max, value + 1))}
          disabled={value >= max}
          className="flex h-10 w-10 items-center justify-center rounded-full border border-border-default bg-surface text-text-primary disabled:opacity-30 disabled:cursor-not-allowed hover:bg-surface-muted transition-colors"
          aria-label={`Increase ${label}`}
        >
          <Plus className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

export function WizardStepWhen({
  startDate,
  totalDays,
  destination,
  travelers,
  onStartDateChange,
  onTotalDaysChange,
  onTravelersChange,
  onNext,
  onBack,
}: WizardStepWhenProps) {
  const endDate = (() => {
    try {
      const start = new Date(startDate + 'T00:00:00');
      const end = new Date(start);
      end.setDate(end.getDate() + totalDays - 1);
      return end.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
      return '';
    }
  })();

  const startFormatted = (() => {
    try {
      return new Date(startDate + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
      return '';
    }
  })();

  const totalTravelers = travelers.adults + travelers.children + travelers.infants;

  return (
    <div className="space-y-8 max-w-lg mx-auto">
      <div className="text-center">
        <h2 className="text-2xl font-display font-bold text-text-primary">
          When & who?
        </h2>
        <p className="text-sm text-text-muted mt-1">
          Pick your dates and group size for {destination || 'your trip'}
        </p>
      </div>

      <div className="space-y-6">
        <div className="space-y-2">
          <label htmlFor="wiz-start-date" className="text-sm font-medium text-text-primary flex items-center gap-1.5">
            <Calendar className="h-4 w-4 text-primary-500" />
            Start Date
          </label>
          <Input
            id="wiz-start-date"
            type="date"
            value={startDate}
            onChange={(e) => onStartDateChange(e.target.value)}
            className="h-11"
          />
        </div>

        <div className="space-y-3">
          <label htmlFor="wiz-duration" className="text-sm font-medium text-text-primary flex items-center gap-1.5">
            <Clock className="h-4 w-4 text-primary-500" />
            Duration
          </label>
          <div className="flex items-center gap-4">
            <input
              id="wiz-duration"
              type="range"
              min={1}
              max={30}
              value={totalDays}
              onChange={(e) => onTotalDaysChange(Number(e.target.value))}
              className="flex-1 accent-primary-600"
            />
            <span className="text-lg font-bold text-text-primary w-20 text-center">
              {totalDays} {totalDays === 1 ? 'day' : 'days'}
            </span>
          </div>
        </div>

        {/* Travelers */}
        <div className="space-y-3">
          <label className="text-sm font-medium text-text-primary flex items-center gap-1.5">
            <Users className="h-4 w-4 text-primary-500" />
            Travelers
          </label>
          <div className="rounded-lg border border-border-default bg-surface p-4 space-y-3">
            <CounterInput
              label="Adults"
              sublabel="13+ years"
              value={travelers.adults}
              min={1}
              max={20}
              onChange={(v) => onTravelersChange({ ...travelers, adults: v })}
            />
            <CounterInput
              label="Children"
              sublabel="2-12 years"
              value={travelers.children}
              min={0}
              max={10}
              onChange={(v) => onTravelersChange({ ...travelers, children: v })}
            />
            <CounterInput
              label="Infants"
              sublabel="Under 2 years"
              value={travelers.infants}
              min={0}
              max={5}
              onChange={(v) => onTravelersChange({ ...travelers, infants: v })}
            />
          </div>
        </div>

        {startDate && (
          <div className="rounded-lg bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 px-4 py-3 text-center">
            <p className="text-sm text-primary-700 dark:text-primary-300">
              {startFormatted} → {endDate} ({totalDays} {totalDays === 1 ? 'day' : 'days'}) · {totalTravelers} {totalTravelers === 1 ? 'traveler' : 'travelers'}
            </p>
          </div>
        )}
      </div>

      <div className="flex gap-3">
        <Button variant="outline" onClick={onBack} className="flex-1">
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>
        <Button
          onClick={onNext}
          className="flex-1 bg-primary-600 hover:bg-primary-700 text-white"
        >
          Next
        </Button>
      </div>
    </div>
  );
}
