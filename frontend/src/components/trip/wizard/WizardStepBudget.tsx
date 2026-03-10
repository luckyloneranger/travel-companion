import { Backpack, Briefcase, Diamond, DollarSign, ArrowLeft } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import type { Budget } from '@/types';

const BUDGET_OPTIONS: { id: Budget; label: string; description: string; icon: typeof Backpack; gradient: string }[] = [
  { id: 'budget', label: 'Budget', description: 'Hostels, street food, free attractions', icon: Backpack, gradient: 'from-emerald-500/8 to-green-500/4 dark:from-emerald-500/12 dark:to-green-500/8' },
  { id: 'moderate', label: 'Moderate', description: 'Hotels, restaurants, mix of free & paid', icon: Briefcase, gradient: 'from-primary-500/8 to-blue-500/4 dark:from-primary-500/12 dark:to-blue-500/8' },
  { id: 'luxury', label: 'Luxury', description: 'Premium hotels, fine dining, exclusive experiences', icon: Diamond, gradient: 'from-amber-500/8 to-yellow-500/4 dark:from-amber-500/12 dark:to-yellow-500/8' },
];

interface WizardStepBudgetProps {
  budget: Budget;
  budgetUsd: string;
  totalDays: number;
  onBudgetChange: (budget: Budget) => void;
  onBudgetUsdChange: (value: string) => void;
  onNext: () => void;
  onBack: () => void;
}

export function WizardStepBudget({
  budget,
  budgetUsd,
  totalDays,
  onBudgetChange,
  onBudgetUsdChange,
  onNext,
  onBack,
}: WizardStepBudgetProps) {
  const budgetNum = parseFloat(budgetUsd) || 0;
  const perDay = totalDays > 0 && budgetNum > 0 ? budgetNum / totalDays : 0;

  return (
    <div className="space-y-8 max-w-lg mx-auto">
      <div className="text-center">
        <h2 className="text-2xl font-display font-bold text-text-primary">
          What's your budget?
        </h2>
        <p className="text-sm text-text-muted mt-1">
          Choose your spending style
        </p>
      </div>

      {/* Budget tier */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {BUDGET_OPTIONS.map((opt) => {
          const Icon = opt.icon;
          const selected = budget === opt.id;
          return (
            <button
              key={opt.id}
              type="button"
              onClick={() => onBudgetChange(opt.id)}
              className={`flex flex-col items-center gap-2 rounded-xl border p-4 text-center transition-all hover:scale-[1.03] active:scale-[0.98] bg-gradient-to-br ${opt.gradient} ${
                selected
                  ? 'border-primary-500 ring-1 ring-primary-500 shadow-md'
                  : 'border-border-default hover:border-primary-300 hover:shadow-sm'
              }`}
            >
              <Icon className={`h-7 w-7 ${selected ? 'text-primary-600 dark:text-primary-400' : 'text-text-muted'}`} />
              <span className={`text-sm font-semibold ${selected ? 'text-primary-700 dark:text-primary-300' : 'text-text-primary'}`}>
                {opt.label}
              </span>
              <p className="text-xs text-text-muted">{opt.description}</p>
            </button>
          );
        })}
      </div>

      {/* Total budget */}
      <div className="space-y-2">
        <label htmlFor="wiz-budget-usd" className="text-sm font-medium text-text-muted flex items-center gap-1.5">
          <DollarSign className="h-4 w-4" />
          Total budget in USD <span className="text-xs">(optional)</span>
        </label>
        <Input
          id="wiz-budget-usd"
          type="number"
          placeholder="e.g. 3000"
          value={budgetUsd}
          onChange={(e) => onBudgetUsdChange(e.target.value)}
          min={0}
        />
        {perDay > 0 && (
          <p className="text-xs text-primary-600 dark:text-primary-400">
            ~${perDay.toFixed(0)}/day for {totalDays} days
          </p>
        )}
      </div>

      <div className="flex gap-3">
        <Button variant="outline" onClick={onBack} className="flex-1">
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>
        <Button
          onClick={onNext}
          className="flex-1 h-12 bg-primary-600 hover:bg-primary-700 text-white text-base font-semibold shadow-sm"
        >
          Continue
        </Button>
      </div>
    </div>
  );
}
