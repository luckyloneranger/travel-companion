import { useState, useEffect, useRef } from 'react';
import { useUIStore } from '@/stores/uiStore';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Search, MapPin, CheckCircle, Wrench, X, Clock, Loader2,
  CalendarDays,
} from 'lucide-react';

interface PlanningDashboardProps {
  onCancel: () => void;
  mode?: 'journey' | 'dayplans';
}

const PHASE_CONFIG: Record<string, { icon: typeof Loader2; label: string; description: string; color: string }> = {
  scouting: {
    icon: Search,
    label: 'Scouting',
    description: 'Finding the best destinations based on your interests...',
    color: 'text-primary-500',
  },
  enriching: {
    icon: MapPin,
    label: 'Enriching',
    description: 'Verifying with real data — routes, accommodation, transport...',
    color: 'text-accent-500',
  },
  reviewing: {
    icon: CheckCircle,
    label: 'Reviewing',
    description: 'Checking plan quality — timing, routing, balance...',
    color: 'text-green-500',
  },
  improving: {
    icon: Wrench,
    label: 'Improving',
    description: 'Fixing issues found during review...',
    color: 'text-yellow-500',
  },
  city_start: {
    icon: MapPin,
    label: 'Planning City',
    description: 'Discovering places and building itinerary...',
    color: 'text-primary-500',
  },
  city_complete: {
    icon: CheckCircle,
    label: 'City Planned',
    description: 'City itinerary complete!',
    color: 'text-green-500',
  },
};

const JOURNEY_STEPS = ['scouting', 'enriching', 'reviewing', 'improving'];

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export function PlanningDashboard({ onCancel, mode = 'journey' }: PlanningDashboardProps) {
  const { progress } = useUIStore();
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [activityLog, setActivityLog] = useState<string[]>([]);
  const [completedCities, setCompletedCities] = useState<string[]>([]);
  const [currentCity, setCurrentCity] = useState<string | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);
  const prevMessageRef = useRef<string>('');

  const isDayPlans = mode === 'dayplans';

  // Elapsed timer
  useEffect(() => {
    const interval = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
    return () => clearInterval(interval);
  }, []);

  // Append progress messages to activity log + track cities
  useEffect(() => {
    if (!progress) return;

    if (progress.message && progress.message !== prevMessageRef.current) {
      prevMessageRef.current = progress.message;
      setActivityLog((prev) => [...prev, progress.message]);
    }

    // Track city progress for day plans mode
    if (isDayPlans && progress.data) {
      const data = progress.data as Record<string, unknown>;
      const cityName = data.city as string | undefined;
      if (progress.phase === 'city_start' && cityName) {
        setCurrentCity(cityName);
      }
      if (progress.phase === 'city_complete' && cityName) {
        setCompletedCities((prev) =>
          prev.includes(cityName) ? prev : [...prev, cityName],
        );
        setCurrentCity(null);
      }
    }
  }, [progress, isDayPlans]);

  // Scroll log to bottom
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activityLog]);

  const phase = progress?.phase || (isDayPlans ? 'city_start' : 'scouting');
  const config = PHASE_CONFIG[phase] || PHASE_CONFIG[isDayPlans ? 'city_start' : 'scouting'];
  const Icon = config.icon;

  // Journey mode: determine which pipeline steps are done
  const currentStepIdx = JOURNEY_STEPS.indexOf(phase);

  const title = isDayPlans ? 'Generating day plans...' : 'Planning your journey...';
  const timeEstimate = isDayPlans ? 'Usually takes 1-3 minutes' : 'Usually takes 2-4 minutes';

  return (
    <Card className="max-w-xl mx-auto mt-8">
      <CardContent className="p-6 space-y-6">
        {/* Header */}
        <div className="text-center">
          <h2 className="text-xl font-display font-bold text-text-primary">
            {title}
          </h2>
          <p className="text-xs text-text-muted mt-1 flex items-center justify-center gap-1.5">
            <Clock className="h-3 w-3" />
            {formatElapsed(elapsedSeconds)} elapsed · {timeEstimate}
          </p>
        </div>

        {/* Pipeline stepper (journey mode) */}
        {!isDayPlans && (
          <div className="flex items-center justify-between gap-1">
            {JOURNEY_STEPS.map((step, idx) => {
              const stepConfig = PHASE_CONFIG[step];
              const StepIcon = stepConfig.icon;
              const isDone = idx < currentStepIdx;
              const isActive = step === phase;

              return (
                <div key={step} className="flex-1 flex flex-col items-center gap-1">
                  <div
                    className={`flex h-8 w-8 items-center justify-center rounded-full text-xs transition-colors ${
                      isDone
                        ? 'bg-green-500 text-white'
                        : isActive
                          ? `bg-primary-100 dark:bg-primary-900/40 ${stepConfig.color}`
                          : 'bg-surface-muted text-text-muted'
                    }`}
                  >
                    {isDone ? (
                      <CheckCircle className="h-4 w-4" />
                    ) : isActive ? (
                      <StepIcon className="h-4 w-4 animate-pulse" />
                    ) : (
                      <StepIcon className="h-4 w-4" />
                    )}
                  </div>
                  <span className={`text-xs ${isActive ? 'font-medium text-text-primary' : 'text-text-muted'}`}>
                    {stepConfig.label}
                  </span>
                </div>
              );
            })}
          </div>
        )}

        {/* City progress (day plans mode) */}
        {isDayPlans && (completedCities.length > 0 || currentCity) && (
          <div className="space-y-2">
            <h3 className="text-xs font-medium text-text-muted">City Progress</h3>
            <div className="flex flex-wrap gap-2">
              {completedCities.map((city) => (
                <span
                  key={city}
                  className="inline-flex items-center gap-1 rounded-full bg-green-100 dark:bg-green-900/30 px-2.5 py-1 text-xs font-medium text-green-700 dark:text-green-300"
                >
                  <CheckCircle className="h-3 w-3" />
                  {city}
                </span>
              ))}
              {currentCity && (
                <span className="inline-flex items-center gap-1 rounded-full bg-primary-100 dark:bg-primary-900/30 px-2.5 py-1 text-xs font-medium text-primary-700 dark:text-primary-300">
                  <CalendarDays className="h-3 w-3 animate-pulse" />
                  {currentCity}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Current status */}
        <div className="text-center space-y-2">
          <div className="flex items-center justify-center gap-2">
            <Icon className={`h-5 w-5 animate-pulse ${config.color}`} />
            <span className="text-base font-semibold text-text-primary">{config.label}</span>
          </div>
          <p className="text-sm text-text-muted">{config.description}</p>
        </div>

        {/* Progress bar */}
        {progress && (
          <div>
            <div
              className="w-full bg-surface-muted rounded-full h-2"
              role="progressbar"
              aria-valuenow={progress.progress}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`${isDayPlans ? 'Day plan' : 'Planning'} progress: ${progress.progress}% complete`}
            >
              <div
                className="bg-primary-500 h-2 rounded-full transition-all duration-500"
                style={{ width: `${progress.progress}%` }}
              />
            </div>
            <p className="text-xs text-text-muted text-center mt-1">{progress.progress}%</p>
          </div>
        )}

        {/* Activity log */}
        {activityLog.length > 0 && (
          <div className="rounded-lg border border-border-default bg-surface-dim p-3 max-h-32 overflow-y-auto">
            <h3 className="text-xs font-medium text-text-muted mb-2">Activity</h3>
            <div className="space-y-1">
              {activityLog.map((msg, i) => (
                <p key={i} className="text-xs text-text-secondary flex items-start gap-1.5">
                  <CheckCircle className="h-3 w-3 text-green-500 mt-0.5 shrink-0" />
                  {msg}
                </p>
              ))}
              <div ref={logEndRef} />
            </div>
          </div>
        )}

        {/* Cancel */}
        <div className="text-center">
          <Button variant="outline" size="sm" onClick={onCancel}>
            <X className="h-4 w-4" />
            Cancel and start over
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
