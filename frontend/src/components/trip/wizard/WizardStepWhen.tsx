import { Calendar, Clock, ArrowLeft } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

interface WizardStepWhenProps {
  startDate: string;
  totalDays: number;
  destination: string;
  onStartDateChange: (value: string) => void;
  onTotalDaysChange: (value: number) => void;
  onNext: () => void;
  onBack: () => void;
}

export function WizardStepWhen({
  startDate,
  totalDays,
  destination,
  onStartDateChange,
  onTotalDaysChange,
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

  return (
    <div className="space-y-8 max-w-lg mx-auto">
      <div className="text-center">
        <h2 className="text-2xl font-display font-bold text-text-primary">
          When are you going?
        </h2>
        <p className="text-sm text-text-muted mt-1">
          Pick your dates for {destination || 'your trip'}
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

        {startDate && (
          <div className="rounded-lg bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 px-4 py-3 text-center">
            <p className="text-sm text-primary-700 dark:text-primary-300">
              {startFormatted} → {endDate} ({totalDays} {totalDays === 1 ? 'day' : 'days'})
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
