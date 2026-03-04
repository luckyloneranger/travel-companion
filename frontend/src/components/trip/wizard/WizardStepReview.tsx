import {
  MapPin, Calendar, Sparkles, DollarSign, ArrowLeft, Rocket,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { Pace, Budget } from '@/types';

interface WizardStepReviewProps {
  destination: string;
  origin: string;
  startDate: string;
  totalDays: number;
  interests: string[];
  pace: Pace;
  mustInclude: string[];
  avoid: string[];
  budget: Budget;
  budgetUsd: string;
  isLoading: boolean;
  onEditStep: (step: number) => void;
  onSubmit: () => void;
  onBack: () => void;
}

function ReviewRow({ label, children, stepNumber, onEdit }: {
  label: string;
  children: React.ReactNode;
  stepNumber: number;
  onEdit: (step: number) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-3 border-b border-border-default last:border-0">
      <div className="min-w-0 flex-1">
        <span className="text-xs font-medium text-text-muted uppercase tracking-wider">{label}</span>
        <div className="mt-1">{children}</div>
      </div>
      <button
        type="button"
        onClick={() => onEdit(stepNumber)}
        className="text-xs text-primary-600 dark:text-primary-400 hover:underline shrink-0 mt-1"
      >
        Edit
      </button>
    </div>
  );
}

export function WizardStepReview({
  destination,
  origin,
  startDate,
  totalDays,
  interests,
  pace,
  mustInclude,
  avoid,
  budget,
  budgetUsd,
  isLoading,
  onEditStep,
  onSubmit,
  onBack,
}: WizardStepReviewProps) {
  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-US', {
        month: 'long', day: 'numeric', year: 'numeric',
      });
    } catch { return dateStr; }
  };

  const budgetNum = parseFloat(budgetUsd) || 0;

  return (
    <div className="space-y-6 max-w-lg mx-auto">
      <div className="text-center">
        <h2 className="text-2xl font-display font-bold text-text-primary">
          Ready to plan?
        </h2>
        <p className="text-sm text-text-muted mt-1">
          Review your trip details
        </p>
      </div>

      <div className="rounded-lg border border-border-default bg-surface p-4">
        <ReviewRow label="Destination" stepNumber={1} onEdit={onEditStep}>
          <div className="flex items-center gap-2">
            <MapPin className="h-4 w-4 text-primary-500 shrink-0" />
            <span className="text-sm font-medium text-text-primary">{destination}</span>
          </div>
          {origin && (
            <p className="text-xs text-text-muted mt-0.5">From {origin}</p>
          )}
        </ReviewRow>

        <ReviewRow label="Dates" stepNumber={2} onEdit={onEditStep}>
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-primary-500 shrink-0" />
            <span className="text-sm text-text-primary">
              {formatDate(startDate)} · {totalDays} {totalDays === 1 ? 'day' : 'days'}
            </span>
          </div>
        </ReviewRow>

        <ReviewRow label="Style" stepNumber={3} onEdit={onEditStep}>
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary-500 shrink-0" />
              <span className="text-sm text-text-primary capitalize">{pace} pace</span>
            </div>
            {interests.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {interests.map((i) => (
                  <Badge key={i} variant="secondary" className="text-xs capitalize">{i}</Badge>
                ))}
              </div>
            )}
            {mustInclude.length > 0 && (
              <p className="text-xs text-text-muted">Must include: {mustInclude.join(', ')}</p>
            )}
            {avoid.length > 0 && (
              <p className="text-xs text-text-muted">Avoid: {avoid.join(', ')}</p>
            )}
          </div>
        </ReviewRow>

        <ReviewRow label="Budget" stepNumber={4} onEdit={onEditStep}>
          <div className="flex items-center gap-2">
            <DollarSign className="h-4 w-4 text-primary-500 shrink-0" />
            <span className="text-sm text-text-primary capitalize">{budget}</span>
            {budgetNum > 0 && (
              <span className="text-xs text-text-muted">
                · ${budgetNum.toLocaleString()} total (~${Math.round(budgetNum / totalDays)}/day)
              </span>
            )}
          </div>
        </ReviewRow>
      </div>

      <div className="flex gap-3">
        <Button variant="outline" onClick={onBack} className="flex-1">
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>
        <Button
          onClick={onSubmit}
          disabled={isLoading}
          className="flex-1 bg-primary-600 hover:bg-primary-700 text-white h-12 text-base font-semibold"
        >
          <Rocket className="h-5 w-5" />
          Plan My Trip
        </Button>
      </div>
    </div>
  );
}
