import { useState, useEffect, useRef, useMemo } from 'react';
import { useUIStore } from '@/stores/uiStore';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Search, MapPin, CheckCircle, Wrench, X, Clock, Loader2,
  CalendarDays, Lightbulb,
} from 'lucide-react';

interface PlanningDashboardProps {
  onCancel: () => void;
  mode?: 'journey' | 'dayplans';
}

function getTravelFacts(destination: string): string[] {
  const lower = destination.toLowerCase();

  const contextual: Record<string, string[]> = {
    japan: [
      "In Japan, it's polite to slurp your noodles — it shows appreciation!",
      "Japanese convenience stores have some of the best food in the country.",
      "Most temples close by 5 PM — plan morning visits for the best experience.",
      "Get a Suica/Pasmo IC card — works on trains, buses, and vending machines.",
      "Japan's trains have an average delay of just 18 seconds per year.",
      "Tipping is not expected in Japan — it can even be considered rude.",
    ],
    thailand: [
      "In Thailand, the head is considered sacred — never touch anyone's head.",
      "Thai street food costs $1-3 per dish — some of the best food is the cheapest.",
      "Always remove your shoes before entering a Thai temple.",
      "Bangkok's official name is 168 characters long — the longest city name!",
      "The Thai greeting 'Wai' (palms together bow) shows respect to elders.",
    ],
    italy: [
      "In Italy, cappuccino is a morning drink — locals never order it after 11 AM.",
      "Most Italian museums close on Mondays — plan your visits accordingly!",
      "Restaurants charge 'coperto' (cover charge) — it's normal, not a scam.",
      "Tap water in Rome is safe and delicious — from ancient aqueducts!",
    ],
    france: [
      "French restaurants must offer free tap water — ask for 'une carafe d'eau'.",
      "Paris museums are free on the first Sunday of each month.",
      "Learn basic French greetings — 'Bonjour' before entering any shop.",
      "The Paris Metro is the fastest way around — buy a carnet of 10 tickets.",
    ],
    spain: [
      "Lunch in Spain is 2-4 PM, dinner after 9 PM — adjust your schedule!",
      "Siesta is real — many shops close between 2-5 PM in smaller towns.",
      "Tapas are often free with drinks in Granada and parts of Andalusia.",
    ],
    india: [
      "India's trains connect 8,000+ stations — the largest rail network in Asia.",
      "Bargaining is expected in Indian markets — start at half the quoted price.",
      "Remove shoes before entering temples and many homes.",
      "Indian street food is incredible but stick to busy stalls for freshness.",
    ],
    korea: [
      "In South Korea, age determines social hierarchy — older = more respect.",
      "T-money card works on all Seoul public transport and convenience stores.",
      "Korean BBQ is a social event — never pour your own drink!",
    ],
  };

  const general = [
    "The longest commercial flight is 19 hours — Singapore to New York.",
    "Iceland has no mosquitoes — one of the few places on Earth.",
    "Tuesday is statistically the cheapest day to book flights.",
    "The world's oldest hotel has been operating in Japan since 705 AD.",
    "Venice charges a day-trip entry fee — book online to save time.",
    "Pack a universal power adapter — it works in 150+ countries.",
    "Travel insurance costs 4-8% of your trip — worth every penny.",
    "Airport lounges cost $30-50 for day passes — or free with some credit cards.",
  ];

  for (const [key, facts] of Object.entries(contextual)) {
    if (lower.includes(key)) return [...facts, ...general].slice(0, 8);
  }
  return general.slice(0, 8);
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
  const [factIndex, setFactIndex] = useState(0);
  const logEndRef = useRef<HTMLDivElement>(null);
  const prevMessageRef = useRef<string>('');

  const isDayPlans = mode === 'dayplans';

  // Get destination from wizard sessionStorage for contextual facts
  const destination = useMemo(() => {
    try {
      const raw = sessionStorage.getItem('tc_wizard');
      return raw ? (JSON.parse(raw).destination as string) || '' : '';
    } catch { return ''; }
  }, []);
  const facts = useMemo(() => getTravelFacts(destination), [destination]);

  // Elapsed timer
  useEffect(() => {
    const interval = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
    return () => clearInterval(interval);
  }, []);

  // Rotate travel facts
  useEffect(() => {
    const timer = setInterval(() => {
      setFactIndex((prev) => (prev + 1) % facts.length);
    }, 8000);
    return () => clearInterval(timer);
  }, [facts.length]);

  // Append progress messages to activity log + track cities
  useEffect(() => {
    if (!progress) return;

    if (progress.message && progress.message !== prevMessageRef.current) {
      prevMessageRef.current = progress.message;
      setActivityLog((prev) => {
        // Deduplicate consecutive identical messages
        if (prev.length > 0 && prev[prev.length - 1] === progress.message) return prev;
        return [...prev, progress.message];
      });
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

  const etaText = isDayPlans
    ? (elapsedSeconds < 60 ? 'Usually completes in 1-3 min' : 'Almost done...')
    : (elapsedSeconds < 120 ? 'Usually completes in 2-4 min' : 'Almost done...');

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
            {formatElapsed(elapsedSeconds)} elapsed
          </p>
          <span className="text-xs text-text-muted">
            {etaText}
          </span>
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

        {/* Did you know? */}
        <div className="flex items-start gap-2 rounded-lg bg-accent-50 dark:bg-accent-950/30 border border-accent-200 dark:border-accent-800 px-3 py-2.5 mt-4">
          <Lightbulb className="h-4 w-4 text-accent-500 mt-0.5 shrink-0" />
          <p className="text-sm text-accent-700 dark:text-accent-300 transition-opacity duration-500">
            {facts[factIndex]}
          </p>
        </div>

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
