import { Check } from 'lucide-react';

const STEPS = [
  { label: 'Where', number: 1 },
  { label: 'When', number: 2 },
  { label: 'Style', number: 3 },
  { label: 'Budget', number: 4 },
  { label: 'Review', number: 5 },
];

interface WizardStepperProps {
  currentStep: number;
  onStepClick: (step: number) => void;
}

export function WizardStepper({ currentStep, onStepClick }: WizardStepperProps) {
  return (
    <nav aria-label="Wizard progress" className="w-full max-w-2xl mx-auto mb-8">
      <ol className="flex items-center justify-between">
        {STEPS.map((step, idx) => {
          const isCompleted = step.number < currentStep;
          const isActive = step.number === currentStep;
          const isPending = step.number > currentStep;

          return (
            <li key={step.number} className="flex-1 flex flex-col items-center relative">
              {/* Connector line (before this step) */}
              {idx > 0 && (
                <div
                  className={`absolute top-4 right-1/2 w-full h-0.5 -translate-y-1/2 ${
                    isCompleted || isActive ? 'bg-primary-500' : 'bg-border-default'
                  }`}
                  style={{ zIndex: 0 }}
                />
              )}

              {/* Step circle */}
              <button
                type="button"
                onClick={() => isCompleted && onStepClick(step.number)}
                disabled={isPending}
                className={`relative z-10 flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold transition-colors ${
                  isCompleted
                    ? 'bg-green-500 text-white cursor-pointer hover:bg-green-600'
                    : isActive
                      ? 'bg-primary-600 text-white ring-2 ring-primary-300 dark:ring-primary-700'
                      : 'bg-surface-muted text-text-muted border border-border-default cursor-default'
                }`}
                aria-current={isActive ? 'step' : undefined}
                aria-label={`Step ${step.number}: ${step.label}${isCompleted ? ' (completed)' : isActive ? ' (current)' : ''}`}
              >
                {isCompleted ? <Check className="h-4 w-4" /> : step.number}
              </button>

              {/* Label */}
              <span
                className={`mt-1.5 text-xs sm:text-sm font-medium ${
                  isActive
                    ? 'text-primary-600 dark:text-primary-400'
                    : isCompleted
                      ? 'text-text-secondary'
                      : 'text-text-muted'
                }`}
              >
                {step.label}
              </span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
