import { ChevronLeft, Check } from 'lucide-react';

type Phase = 'input' | 'planning' | 'preview' | 'day-plans';

const PHASES: { key: Phase; label: string }[] = [
  { key: 'input', label: 'Plan' },
  { key: 'planning', label: 'Generating' },
  { key: 'preview', label: 'Preview' },
  { key: 'day-plans', label: 'Day Plans' },
];

const PHASE_ORDER: Record<Phase, number> = {
  input: 0,
  planning: 1,
  preview: 2,
  'day-plans': 3,
};

interface PhaseIndicatorProps {
  currentPhase: Phase;
  onBack?: () => void;
  backLabel?: string;
}

export function PhaseIndicator({ currentPhase, onBack, backLabel }: PhaseIndicatorProps) {
  if (currentPhase === 'input') return null;

  const currentIndex = PHASE_ORDER[currentPhase];

  return (
    <div className="flex items-center gap-3 mb-6">
      {onBack && (
        <button
          onClick={onBack}
          className="flex items-center gap-1 text-sm text-[#9C8E82] hover:text-[#3D3229] transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
          <span>{backLabel || 'Back'}</span>
        </button>
      )}
      <div className="flex items-center gap-2 flex-1">
        {PHASES.map((phase, index) => {
          const isCompleted = index < currentIndex;
          const isCurrent = index === currentIndex;

          return (
            <div key={phase.key} className="flex items-center gap-2">
              {index > 0 && (
                <div
                  className={`h-px w-6 sm:w-10 ${
                    isCompleted ? 'bg-[#8B9E6B]' : 'bg-[#E8E0D4]'
                  }`}
                />
              )}
              <div className="flex items-center gap-1.5">
                {isCompleted ? (
                  <div className="w-5 h-5 rounded-full bg-[#8B9E6B] flex items-center justify-center">
                    <Check className="h-3 w-3 text-white" />
                  </div>
                ) : isCurrent ? (
                  <div className="w-5 h-5 rounded-full bg-[#C97B5A] animate-pulse" />
                ) : (
                  <div className="w-5 h-5 rounded-full bg-[#E8E0D4]" />
                )}
                <span
                  className={`text-xs font-medium hidden sm:inline ${
                    isCurrent
                      ? 'text-[#C97B5A]'
                      : isCompleted
                      ? 'text-[#8B9E6B]'
                      : 'text-[#9C8E82]'
                  }`}
                >
                  {phase.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
