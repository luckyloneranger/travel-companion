import { useState, useEffect, useRef, useMemo } from 'react';
import { useUIStore } from '@/stores/uiStore';
import { Button } from '@/components/ui/button';
import {
  Search, MapPin, CheckCircle, Wrench, X, Clock,
  CalendarDays, Lightbulb, Compass, Globe, Route, Sparkles,
} from 'lucide-react';

interface PlanningDashboardProps {
  onCancel: () => void;
  mode?: 'journey' | 'dayplans';
}

// ── Destination atmosphere colors ─────────────────────────
function getDestinationAtmosphere(destination: string): { from: string; via: string; to: string; darkFrom: string; darkVia: string; darkTo: string } {
  const d = destination.toLowerCase();
  // Tropical / Southeast Asia
  if (d.includes('thailand') || d.includes('bali') || d.includes('vietnam') || d.includes('philippines') || d.includes('hawaii') || d.includes('caribbean'))
    return { from: 'from-emerald-400/20', via: 'via-teal-300/10', to: 'to-cyan-200/5', darkFrom: 'dark:from-emerald-900/30', darkVia: 'dark:via-teal-950/20', darkTo: 'dark:to-cyan-950/10' };
  // Japan / Korea
  if (d.includes('japan') || d.includes('tokyo') || d.includes('kyoto') || d.includes('osaka') || d.includes('korea') || d.includes('seoul'))
    return { from: 'from-rose-400/15', via: 'via-pink-300/10', to: 'to-fuchsia-200/5', darkFrom: 'dark:from-rose-950/25', darkVia: 'dark:via-pink-950/15', darkTo: 'dark:to-fuchsia-950/10' };
  // Mediterranean / Southern Europe
  if (d.includes('italy') || d.includes('spain') || d.includes('greece') || d.includes('portugal') || d.includes('croatia') || d.includes('mediterranean'))
    return { from: 'from-amber-400/15', via: 'via-orange-300/10', to: 'to-yellow-200/5', darkFrom: 'dark:from-amber-950/25', darkVia: 'dark:via-orange-950/15', darkTo: 'dark:to-yellow-950/10' };
  // Northern Europe / Scandinavia
  if (d.includes('iceland') || d.includes('norway') || d.includes('sweden') || d.includes('finland') || d.includes('denmark') || d.includes('scotland'))
    return { from: 'from-sky-400/15', via: 'via-blue-300/10', to: 'to-indigo-200/5', darkFrom: 'dark:from-sky-950/25', darkVia: 'dark:via-blue-950/15', darkTo: 'dark:to-indigo-950/10' };
  // France / UK / Western Europe
  if (d.includes('france') || d.includes('paris') || d.includes('london') || d.includes('england') || d.includes('germany') || d.includes('netherlands'))
    return { from: 'from-violet-400/12', via: 'via-purple-300/8', to: 'to-blue-200/5', darkFrom: 'dark:from-violet-950/20', darkVia: 'dark:via-purple-950/12', darkTo: 'dark:to-blue-950/8' };
  // India / South Asia
  if (d.includes('india') || d.includes('sri lanka') || d.includes('nepal'))
    return { from: 'from-orange-400/15', via: 'via-amber-300/10', to: 'to-red-200/5', darkFrom: 'dark:from-orange-950/25', darkVia: 'dark:via-amber-950/15', darkTo: 'dark:to-red-950/10' };
  // Middle East / North Africa
  if (d.includes('egypt') || d.includes('morocco') || d.includes('dubai') || d.includes('turkey') || d.includes('jordan'))
    return { from: 'from-yellow-400/15', via: 'via-amber-300/10', to: 'to-orange-200/5', darkFrom: 'dark:from-yellow-950/20', darkVia: 'dark:via-amber-950/15', darkTo: 'dark:to-orange-950/10' };
  // Americas
  if (d.includes('new york') || d.includes('usa') || d.includes('canada') || d.includes('mexico') || d.includes('brazil') || d.includes('peru') || d.includes('argentina'))
    return { from: 'from-indigo-400/12', via: 'via-blue-300/8', to: 'to-sky-200/5', darkFrom: 'dark:from-indigo-950/20', darkVia: 'dark:via-blue-950/12', darkTo: 'dark:to-sky-950/8' };
  // Default — atmospheric indigo-teal
  return { from: 'from-primary-400/12', via: 'via-teal-300/8', to: 'to-sky-200/5', darkFrom: 'dark:from-primary-950/20', darkVia: 'dark:via-teal-950/12', darkTo: 'dark:to-sky-950/8' };
}

// ── Travel facts ───────────────────────────────────────────
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

const PHASE_CONFIG: Record<string, { icon: typeof Search; label: string; description: string; color: string; accent: string }> = {
  scouting: {
    icon: Search,
    label: 'Scouting',
    description: 'Finding the best destinations based on your interests...',
    color: 'text-primary-500',
    accent: 'bg-primary-500',
  },
  enriching: {
    icon: MapPin,
    label: 'Enriching',
    description: 'Verifying with real data — routes, accommodation, transport...',
    color: 'text-accent-500',
    accent: 'bg-accent-500',
  },
  reviewing: {
    icon: CheckCircle,
    label: 'Reviewing',
    description: 'Checking plan quality — timing, routing, balance...',
    color: 'text-green-500',
    accent: 'bg-green-500',
  },
  improving: {
    icon: Wrench,
    label: 'Improving',
    description: 'Fixing issues found during review...',
    color: 'text-yellow-500',
    accent: 'bg-yellow-500',
  },
  city_start: {
    icon: MapPin,
    label: 'Planning City',
    description: 'Discovering places and building itinerary...',
    color: 'text-primary-500',
    accent: 'bg-primary-500',
  },
  city_complete: {
    icon: CheckCircle,
    label: 'City Planned',
    description: 'City itinerary complete!',
    color: 'text-green-500',
    accent: 'bg-green-500',
  },
};

const JOURNEY_STEPS = ['scouting', 'enriching', 'reviewing', 'improving'];

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

// ── Immersive Route Map SVG ─────────────────────────────────
function RouteMapAnimation({ phase }: { phase: string }) {
  const cityCount = phase === 'scouting' ? 1 : phase === 'enriching' ? 2 : 3;
  const showPath = phase !== 'scouting';
  const showPlane = phase === 'reviewing' || phase === 'improving';
  const stepIdx = JOURNEY_STEPS.indexOf(phase);

  return (
    <div className="relative flex items-center justify-center">
      {/* Decorative radial glow behind the SVG */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none" aria-hidden="true">
        <div className="w-48 h-48 rounded-full bg-primary-500/5 dark:bg-primary-400/5 blur-3xl animate-pulse" style={{ animationDuration: '4s' }} />
      </div>

      <svg viewBox="0 0 340 120" className="w-full max-w-md h-32 sm:h-40 relative" fill="none">
        {/* Grid lines for atmosphere */}
        <defs>
          <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="currentColor" strokeWidth="0.3" opacity="0.08" />
          </pattern>
        </defs>
        <rect width="340" height="120" fill="url(#grid)" className="text-text-muted" />

        {/* Curved route path */}
        {showPath && (
          <>
            {/* Shadow/glow path */}
            <path
              d="M 60 60 C 110 20, 160 20, 170 60 C 180 100, 230 100, 280 60"
              stroke="currentColor"
              strokeWidth="6"
              strokeLinecap="round"
              className="text-primary-200/30 dark:text-primary-700/20"
            />
            {/* Main animated path */}
            <path
              d="M 60 60 C 110 20, 160 20, 170 60 C 180 100, 230 100, 280 60"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeDasharray="300"
              strokeDashoffset="300"
              className="text-primary-400 dark:text-primary-500 animate-draw-path"
            />
          </>
        )}

        {/* City nodes */}
        {[60, 170, 280].slice(0, cityCount).map((cx, i) => {
          const cy = i === 1 ? 60 : 60;
          return (
            <g key={i}>
              {/* Pulse ring */}
              <circle
                cx={cx} cy={cy} r={18}
                className="fill-none stroke-primary-300 dark:stroke-primary-600"
                strokeWidth="1"
                opacity={0}
              >
                <animate attributeName="r" values="12;22" dur="2s" repeatCount="indefinite" />
                <animate attributeName="opacity" values="0.6;0" dur="2s" repeatCount="indefinite" />
              </circle>
              {/* Outer ring */}
              <circle
                cx={cx} cy={cy} r={14}
                className="fill-none stroke-primary-300/40 dark:stroke-primary-600/40"
                strokeWidth="1"
                style={{ animation: `city-pop 0.5s ease-out ${i * 0.4}s both` }}
              />
              {/* Inner fill */}
              <circle
                cx={cx} cy={cy} r={8}
                className="fill-primary-500 dark:fill-primary-400"
                style={{ animation: `city-pop 0.5s ease-out ${i * 0.4}s both` }}
              />
              {/* White dot center */}
              <circle
                cx={cx} cy={cy} r={3}
                className="fill-white dark:fill-white"
                opacity={0.9}
                style={{ animation: `city-pop 0.5s ease-out ${i * 0.4 + 0.2}s both` }}
              />
            </g>
          );
        })}

        {/* Animated plane along path */}
        {showPlane && (
          <g
            style={{
              offsetPath: 'path("M 60 60 C 110 20, 160 20, 170 60 C 180 100, 230 100, 280 60")',
              animation: 'plane-fly 4s ease-in-out infinite',
            }}
          >
            <circle r="4" className="fill-accent-500" />
            <text fontSize="12" textAnchor="middle" dy="-8" className="fill-text-primary">
              ✈
            </text>
          </g>
        )}

        {/* Step connector fills — lines between completed cities */}
        {stepIdx >= 1 && (
          <line x1="74" y1="60" x2="156" y2="60" stroke="currentColor" strokeWidth="2" strokeDasharray="4 4" className="text-green-400 dark:text-green-500" opacity={0.5}>
            <animate attributeName="opacity" values="0;0.5" dur="0.5s" fill="freeze" />
          </line>
        )}
        {stepIdx >= 2 && (
          <line x1="184" y1="60" x2="266" y2="60" stroke="currentColor" strokeWidth="2" strokeDasharray="4 4" className="text-green-400 dark:text-green-500" opacity={0.5}>
            <animate attributeName="opacity" values="0;0.5" dur="0.5s" fill="freeze" />
          </line>
        )}
      </svg>
    </div>
  );
}

// ── Animated fact card with slide transition ─────────────────
function FactCard({ fact, factKey }: { fact: string; factKey: number }) {
  return (
    <div
      key={factKey}
      className="flex items-start gap-3 rounded-xl bg-gradient-to-r from-accent-50/80 to-amber-50/50 dark:from-accent-950/40 dark:to-amber-950/20 border border-accent-200/60 dark:border-accent-800/40 px-4 py-3 animate-fact-slide"
    >
      <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-accent-100 dark:bg-accent-900/40 shrink-0 mt-0.5">
        <Lightbulb className="h-4 w-4 text-accent-500" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[10px] font-medium text-accent-500 dark:text-accent-400 uppercase tracking-wider mb-0.5">Did you know?</p>
        <p className="text-sm text-accent-700 dark:text-accent-300 leading-relaxed">{fact}</p>
      </div>
    </div>
  );
}

// ── Pipeline stepper with celebration ─────────────────────────
function PipelineStepper({ phase, previousPhase }: { phase: string; previousPhase: string | null }) {
  const currentStepIdx = JOURNEY_STEPS.indexOf(phase);
  const prevStepIdx = previousPhase ? JOURNEY_STEPS.indexOf(previousPhase) : -1;

  return (
    <div className="flex items-center gap-0">
      {JOURNEY_STEPS.map((step, idx) => {
        const stepConfig = PHASE_CONFIG[step];
        const StepIcon = stepConfig.icon;
        const isDone = idx < currentStepIdx;
        const isActive = step === phase;
        const justCompleted = isDone && idx === prevStepIdx;

        return (
          <div key={step} className="flex items-center flex-1">
            {/* Step node */}
            <div className="flex flex-col items-center gap-1.5 flex-1">
              <div
                className={`relative flex h-10 w-10 items-center justify-center rounded-full text-xs transition-all duration-500 ${
                  isDone
                    ? 'bg-green-500 text-white shadow-sm shadow-green-500/30'
                    : isActive
                      ? `bg-primary-100 dark:bg-primary-900/40 ${stepConfig.color} ring-2 ring-primary-300/50 dark:ring-primary-600/50 shadow-sm`
                      : 'bg-surface-muted text-text-muted'
                }`}
              >
                {isDone ? (
                  <CheckCircle className={`h-5 w-5 ${justCompleted ? 'animate-step-complete' : ''}`} />
                ) : isActive ? (
                  <StepIcon className="h-5 w-5 animate-spin-slow" />
                ) : (
                  <StepIcon className="h-5 w-5" />
                )}
                {/* Celebration burst on completion */}
                {justCompleted && (
                  <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
                    {[0, 60, 120, 180, 240, 300].map((deg) => (
                      <div
                        key={deg}
                        className="absolute left-1/2 top-1/2 w-1 h-1 rounded-full bg-green-400"
                        style={{
                          animation: `step-burst 0.6s ease-out forwards`,
                          transform: `rotate(${deg}deg) translateY(-8px)`,
                        }}
                      />
                    ))}
                  </div>
                )}
              </div>
              <span className={`text-xs transition-colors ${isActive ? 'font-semibold text-text-primary' : isDone ? 'font-medium text-green-600 dark:text-green-400' : 'text-text-muted'}`}>
                {stepConfig.label}
              </span>
            </div>
            {/* Connector line */}
            {idx < JOURNEY_STEPS.length - 1 && (
              <div className="h-0.5 flex-1 -mx-1 mt-[-18px]">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${
                    idx < currentStepIdx ? 'bg-green-400 dark:bg-green-500' : 'bg-surface-muted'
                  }`}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────
export function PlanningDashboard({ onCancel, mode = 'journey' }: PlanningDashboardProps) {
  const { progress } = useUIStore();
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [activityLog, setActivityLog] = useState<string[]>([]);
  const [completedCities, setCompletedCities] = useState<string[]>([]);
  const [currentCity, setCurrentCity] = useState<string | null>(null);
  const [factIndex, setFactIndex] = useState(0);
  const [previousPhase, setPreviousPhase] = useState<string | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);
  const prevMessageRef = useRef<string>('');
  const prevPhaseRef = useRef<string>('');

  const isDayPlans = mode === 'dayplans';

  const destination = useMemo(() => {
    try {
      const raw = sessionStorage.getItem('tc_wizard');
      return raw ? (JSON.parse(raw).destination as string) || '' : '';
    } catch { return ''; }
  }, []);
  const facts = useMemo(() => getTravelFacts(destination), [destination]);
  const atmosphere = useMemo(() => getDestinationAtmosphere(destination), [destination]);

  // Elapsed timer
  useEffect(() => {
    const interval = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
    return () => clearInterval(interval);
  }, []);

  // Rotate travel facts
  useEffect(() => {
    const timer = setInterval(() => {
      setFactIndex((prev) => (prev + 1) % facts.length);
    }, 7000);
    return () => clearInterval(timer);
  }, [facts.length]);

  // Track phase transitions for celebration
  const phase = progress?.phase || (isDayPlans ? 'city_start' : 'scouting');
  useEffect(() => {
    if (phase !== prevPhaseRef.current) {
      setPreviousPhase(prevPhaseRef.current || null);
      prevPhaseRef.current = phase;
      // Clear previous phase indicator after animation
      const timer = setTimeout(() => setPreviousPhase(null), 1000);
      return () => clearTimeout(timer);
    }
  }, [phase]);

  // Append progress messages + track cities
  useEffect(() => {
    if (!progress) return;
    if (progress.message && progress.message !== prevMessageRef.current) {
      prevMessageRef.current = progress.message;
      setActivityLog((prev) => {
        if (prev.length > 0 && prev[prev.length - 1] === progress.message) return prev;
        return [...prev, progress.message];
      });
    }
    if (isDayPlans && progress.data) {
      const data = progress.data as Record<string, unknown>;
      const cityName = data.city as string | undefined;
      if (progress.phase === 'city_start' && cityName) setCurrentCity(cityName);
      if (progress.phase === 'city_complete' && cityName) {
        setCompletedCities((prev) => prev.includes(cityName) ? prev : [...prev, cityName]);
        setCurrentCity(null);
      }
    }
  }, [progress, isDayPlans]);

  // Scroll log to bottom
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activityLog]);

  const config = PHASE_CONFIG[phase] || PHASE_CONFIG[isDayPlans ? 'city_start' : 'scouting'];
  const Icon = config.icon;

  const etaText = isDayPlans
    ? (elapsedSeconds < 60 ? 'Usually completes in 1-3 min' : 'Almost done...')
    : (elapsedSeconds < 120 ? 'Usually completes in 2-4 min' : 'Almost done...');

  // Destination display name
  const displayDestination = destination || 'your trip';

  return (
    <div className="max-w-2xl mx-auto mt-4 sm:mt-8 animate-fade-in-up">
      {/* Atmospheric background wrapper */}
      <div className={`relative rounded-2xl overflow-hidden bg-gradient-to-br ${atmosphere.from} ${atmosphere.via} ${atmosphere.to} ${atmosphere.darkFrom} ${atmosphere.darkVia} ${atmosphere.darkTo} border border-border-default shadow-sm`}>
        {/* Decorative floating elements */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden" aria-hidden="true">
          <Compass className="absolute top-6 right-6 h-16 w-16 text-text-muted/[0.03] dark:text-text-muted/[0.05] animate-spin-slow" />
          <Globe className="absolute bottom-8 left-6 h-12 w-12 text-text-muted/[0.03] dark:text-text-muted/[0.05]" />
          <Route className="absolute top-1/2 right-12 h-10 w-10 text-text-muted/[0.03] dark:text-text-muted/[0.05] -translate-y-1/2" />
        </div>

        <div className="relative p-5 sm:p-8 space-y-6">
          {/* ── Destination Hero Typography ───────────────── */}
          <div className="text-center space-y-3">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface/60 dark:bg-surface/30 backdrop-blur-sm text-xs text-text-muted border border-border-default/50">
              <Clock className="h-3 w-3" />
              {formatElapsed(elapsedSeconds)} elapsed · {etaText}
            </div>

            <h2 className="text-2xl sm:text-3xl font-display font-extrabold text-text-primary tracking-tight">
              {isDayPlans ? (
                <>Crafting your days in <span className="bg-gradient-to-r from-primary-600 to-teal-500 dark:from-primary-400 dark:to-teal-400 bg-clip-text text-transparent">{displayDestination}</span></>
              ) : (
                <>Your <span className="bg-gradient-to-r from-primary-600 to-teal-500 dark:from-primary-400 dark:to-teal-400 bg-clip-text text-transparent">{displayDestination}</span> adventure</>
              )}
            </h2>
            <p className="text-sm text-text-muted max-w-sm mx-auto">
              {isDayPlans ? 'Building detailed day-by-day itineraries with weather, routes, and scheduling...' : 'AI is scouting destinations, finding routes, and building your personalized itinerary...'}
            </p>
          </div>

          {/* ── Route Map Animation (journey mode) ──────── */}
          {!isDayPlans && <RouteMapAnimation phase={phase} />}

          {/* ── Pipeline Stepper (journey mode) ─────────── */}
          {!isDayPlans && (
            <PipelineStepper phase={phase} previousPhase={previousPhase} />
          )}

          {/* ── City Progress (day plans mode) ──────────── */}
          {isDayPlans && (completedCities.length > 0 || currentCity) && (
            <div className="space-y-2">
              <h3 className="text-xs font-medium text-text-muted">City Progress</h3>
              <div className="flex flex-wrap gap-2">
                {completedCities.map((city) => (
                  <span
                    key={city}
                    className="inline-flex items-center gap-1 rounded-full bg-green-100 dark:bg-green-900/30 px-2.5 py-1 text-xs font-medium text-green-700 dark:text-green-300 animate-step-complete"
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

          {/* ── Current Phase Status ────────────────────── */}
          <div className="flex items-center justify-center gap-3 py-2">
            <div className={`flex items-center justify-center w-9 h-9 rounded-xl ${config.accent}/10 dark:${config.accent}/20`}>
              <Icon className={`h-5 w-5 ${config.color} animate-pulse`} />
            </div>
            <div>
              <p className="text-sm font-semibold text-text-primary">{config.label}</p>
              <p className="text-xs text-text-muted">{config.description}</p>
            </div>
          </div>

          {/* ── Progress Bar ────────────────────────────── */}
          {progress && (
            <div className="space-y-1.5">
              <div
                className="w-full bg-surface-muted/80 rounded-full h-2.5 overflow-hidden backdrop-blur-sm"
                role="progressbar"
                aria-valuenow={progress.progress}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${isDayPlans ? 'Day plan' : 'Planning'} progress: ${progress.progress}% complete`}
              >
                <div
                  className="h-full rounded-full transition-all duration-700 ease-out bg-gradient-to-r from-primary-500 via-primary-400 to-teal-400"
                  style={{ width: `${progress.progress}%` }}
                />
              </div>
              <div className="flex items-center justify-between text-xs text-text-muted">
                <span>{progress.progress}% complete</span>
                <span className="flex items-center gap-1">
                  <Sparkles className="h-3 w-3" />
                  {progress.progress < 30 ? 'Getting started...' : progress.progress < 60 ? 'Making progress...' : progress.progress < 90 ? 'Almost there...' : 'Finishing up...'}
                </span>
              </div>
            </div>
          )}

          {/* ── Travel Fact Card (animated) ─────────────── */}
          <FactCard fact={facts[factIndex]} factKey={factIndex} />

          {/* ── Activity Log ────────────────────────────── */}
          {activityLog.length > 0 && (
            <div className="rounded-xl border border-border-default/60 bg-surface/50 dark:bg-surface/30 backdrop-blur-sm p-3 max-h-28 overflow-y-auto">
              <h3 className="text-[10px] font-semibold text-text-muted uppercase tracking-wider mb-2">Activity Log</h3>
              <div className="space-y-1">
                {activityLog.map((msg, i) => (
                  <p key={i} className={`text-xs text-text-secondary flex items-start gap-1.5 ${i === activityLog.length - 1 ? 'animate-fade-in-up' : ''}`}>
                    <CheckCircle className="h-3 w-3 text-green-500 mt-0.5 shrink-0" />
                    {msg}
                  </p>
                ))}
                <div ref={logEndRef} />
              </div>
            </div>
          )}

          {/* ── Cancel ──────────────────────────────────── */}
          <div className="text-center pt-2">
            <Button variant="outline" size="sm" onClick={onCancel} className="bg-surface/50 dark:bg-surface/30 backdrop-blur-sm">
              <X className="h-4 w-4" />
              Cancel and start over
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
