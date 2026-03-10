import { Check, MapPin, Calendar, Sparkles, DollarSign, ClipboardCheck } from 'lucide-react';

const STEPS = [
  { label: 'Where', number: 1, icon: MapPin },
  { label: 'When', number: 2, icon: Calendar },
  { label: 'Style', number: 3, icon: Sparkles },
  { label: 'Budget', number: 4, icon: DollarSign },
  { label: 'Review', number: 5, icon: ClipboardCheck },
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
          const Icon = step.icon;

          return (
            <li key={step.number} className="flex-1 flex flex-col items-center relative">
              {/* Connector line */}
              {idx > 0 && (
                <div
                  className={`absolute top-4 right-1/2 w-full h-0.5 -translate-y-1/2 transition-colors duration-300 ${
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
                className={`relative z-10 flex h-9 w-9 items-center justify-center rounded-full text-sm font-semibold transition-all duration-300 ${
                  isCompleted
                    ? 'bg-green-500 text-white cursor-pointer hover:bg-green-600 hover:scale-110'
                    : isActive
                      ? 'bg-primary-600 text-white ring-2 ring-primary-300 dark:ring-primary-700 shadow-md shadow-primary-500/20'
                      : 'bg-surface-muted text-text-muted border border-border-default cursor-default'
                }`}
                aria-current={isActive ? 'step' : undefined}
                aria-label={`Step ${step.number}: ${step.label}${isCompleted ? ' (completed)' : isActive ? ' (current)' : ''}`}
              >
                {isCompleted ? <Check className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
              </button>

              {/* Label */}
              <span
                className={`mt-1.5 text-xs sm:text-sm font-medium transition-colors duration-300 ${
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
