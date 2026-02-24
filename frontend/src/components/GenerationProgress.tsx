import { 
  MapPin, 
  Search, 
  Brain, 
  Route, 
  CheckCircle, 
  Loader2, 
  type LucideIcon,
  Telescope,
  Compass,
  ClipboardCheck,
  Wrench,
  Building2,
  Sparkles,
} from 'lucide-react';

export interface ProgressEvent {
  type: 'progress' | 'complete' | 'error';
  phase?: string;
  message?: string;
  progress?: number;
  data?: Record<string, unknown>;
}

interface GenerationProgressProps {
  progress: ProgressEvent | null;
  destinationName?: string;
  mode?: 'journey' | 'day-plans' | 'itinerary';  // What we're generating
}

interface Phase {
  id: string;
  label: string;
  icon: LucideIcon;
  description?: string;
}

// V6 Journey Planning Phases
const JOURNEY_PHASES: Phase[] = [
  { id: 'scout', label: 'Scout', icon: Telescope, description: 'Discovering route & cities' },
  { id: 'enrich', label: 'Enrich', icon: Compass, description: 'Adding real travel data' },
  { id: 'review', label: 'Review', icon: ClipboardCheck, description: 'Checking feasibility' },
  { id: 'planner', label: 'Refine', icon: Wrench, description: 'Optimizing journey' },
  { id: 'complete', label: 'Done', icon: CheckCircle, description: 'Journey ready!' },
];

// Day Plan Generation Phases
const DAY_PLAN_PHASES: Phase[] = [
  { id: 'city_start', label: 'Planning City', icon: Building2, description: 'Finding activities' },
  { id: 'city_complete', label: 'City Complete', icon: CheckCircle, description: 'Activities scheduled' },
  { id: 'complete', label: 'All Done', icon: Sparkles, description: 'Itinerary complete!' },
];

// Single-city itinerary phases (legacy)
const ITINERARY_PHASES: Phase[] = [
  { id: 'geocoding', label: 'Finding destination', icon: MapPin },
  { id: 'discovery', label: 'Discovering places', icon: Search },
  { id: 'planning', label: 'AI planning itinerary', icon: Brain },
  { id: 'validation', label: 'Optimizing plan', icon: CheckCircle },
  { id: 'routing', label: 'Calculating routes', icon: Route },
  { id: 'finalizing', label: 'Finalizing', icon: CheckCircle },
];

// Gradient colors for different modes
const MODE_COLORS = {
  journey: {
    gradient: 'from-violet-600 to-purple-600',
    iconBg: 'bg-violet-100',
    iconText: 'text-violet-600',
    activeBg: 'bg-violet-500',
    completeBg: 'bg-emerald-500',
    progressGradient: 'from-violet-500 to-purple-600',
    ring: 'ring-violet-200',
    border: 'border-violet-200',
    bgActive: 'bg-violet-50'
  },
  'day-plans': {
    gradient: 'from-emerald-600 to-teal-600',
    iconBg: 'bg-emerald-100',
    iconText: 'text-emerald-600',
    activeBg: 'bg-emerald-500',
    completeBg: 'bg-emerald-500',
    progressGradient: 'from-emerald-500 to-teal-600',
    ring: 'ring-emerald-200',
    border: 'border-emerald-200',
    bgActive: 'bg-emerald-50'
  },
  itinerary: {
    gradient: 'from-primary-600 to-purple-600',
    iconBg: 'bg-primary-100',
    iconText: 'text-primary-600',
    activeBg: 'bg-primary-500',
    completeBg: 'bg-green-500',
    progressGradient: 'from-primary-500 to-primary-600',
    ring: 'ring-primary-200',
    border: 'border-primary-200',
    bgActive: 'bg-primary-50'
  },
};

export function GenerationProgress({ progress, destinationName, mode = 'journey' }: GenerationProgressProps) {
  // Detect mode from phase if not explicitly set
  const detectedMode = progress?.phase?.includes('city_') ? 'day-plans' : 
    ['scout', 'enrich', 'review', 'planner'].includes(progress?.phase || '') ? 'journey' : mode;
  
  const phases = detectedMode === 'day-plans' ? DAY_PLAN_PHASES : 
    detectedMode === 'journey' ? JOURNEY_PHASES : ITINERARY_PHASES;
  
  const colors = MODE_COLORS[detectedMode];
  
  // Find current phase
  const currentPhase = progress?.phase || '';
  const currentPhaseIndex = phases.findIndex(p => currentPhase.startsWith(p.id));
  
  // For day plans, we show city progress differently
  const cityName = progress?.data?.city_name as string | undefined;
  const cityIndex = progress?.data?.city_index as number | undefined;
  const totalCities = progress?.data?.total_cities as number | undefined;
  const cityProgress = progress?.data?.city_progress as number | undefined;

  // Title based on mode
  const titles = {
    journey: 'Crafting Your Journey',
    'day-plans': 'Creating Day Plans',
    itinerary: 'Creating Your Itinerary',
  };

  return (
    <div className="rounded-2xl shadow-xl overflow-hidden max-w-lg mx-auto bg-white">
      {/* Header with gradient */}
      <div className={`bg-gradient-to-r ${colors.gradient} p-6 text-white`}>
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-xl bg-white/20 backdrop-blur flex items-center justify-center">
            <Loader2 className="w-7 h-7 animate-spin" />
          </div>
          <div>
            <h2 className="text-xl font-bold">{titles[detectedMode]}</h2>
            {destinationName && (
              <p className="text-white/80 text-sm mt-0.5">
                {destinationName}
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="p-6">
        {/* Progress Bar */}
        <div className="mb-6">
          <div className="flex justify-between text-sm mb-2">
            <span className="text-gray-700 font-medium">{progress?.message || 'Starting...'}</span>
            <span className="text-gray-500 font-semibold">{progress?.progress || 0}%</span>
          </div>
          <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ease-out bg-gradient-to-r ${colors.progressGradient}`}
              style={{ width: `${progress?.progress || 0}%` }}
            />
          </div>
        </div>

        {/* City Progress for day-plans mode */}
        {detectedMode === 'day-plans' && cityName && totalCities && (
          <div className="mb-6 p-4 rounded-xl bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-100">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center text-white font-bold shadow-md">
                {cityIndex}
              </div>
              <div className="flex-1">
                <div className="font-semibold text-gray-900">{cityName}</div>
                <div className="text-xs text-gray-500">City {cityIndex} of {totalCities}</div>
              </div>
              {cityProgress !== undefined && (
                <div className="text-right">
                  <div className="text-lg font-bold text-emerald-600">{cityProgress}%</div>
                  <div className="text-xs text-gray-500">City progress</div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Phase Steps for journey mode */}
        {detectedMode === 'journey' && (
          <div className="space-y-2">
            {phases.slice(0, -1).map((phase, index) => {  {/* Exclude 'complete' from visible steps */}
              const Icon = phase.icon;
              const isCompleted = currentPhaseIndex > index;
              const isCurrent = currentPhaseIndex === index && currentPhase !== 'complete';

              return (
                <div
                  key={phase.id}
                  className={`flex items-center gap-3 p-3 rounded-xl transition-all ${
                    isCurrent
                      ? `${colors.bgActive} border ${colors.border}`
                      : isCompleted
                      ? 'bg-emerald-50'
                      : 'bg-gray-50'
                  }`}
                >
                  <div
                    className={`flex items-center justify-center w-9 h-9 rounded-lg shadow-sm ${
                      isCurrent
                        ? `${colors.activeBg} text-white`
                        : isCompleted
                        ? 'bg-emerald-500 text-white'
                        : 'bg-gray-200 text-gray-400'
                    }`}
                  >
                    {isCurrent ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : isCompleted ? (
                      <CheckCircle className="w-4 h-4" />
                    ) : (
                      <Icon className="w-4 h-4" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <span
                      className={`text-sm font-semibold ${
                        isCurrent
                          ? colors.iconText.replace('text-', 'text-')
                          : isCompleted
                          ? 'text-emerald-700'
                          : 'text-gray-400'
                      }`}
                    >
                      {phase.label}
                    </span>
                    {phase.description && (
                      <span className={`text-xs ml-2 ${isCurrent ? 'text-gray-600' : 'text-gray-400'}`}>
                        {phase.description}
                      </span>
                    )}
                  </div>
                  {isCurrent && (
                    <span className={`text-xs font-medium animate-pulse ${colors.iconText}`}>
                      Working...
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}

        <p className="text-center text-sm text-gray-500 mt-6">
          {detectedMode === 'journey' 
            ? 'Planning multi-city routes takes 1-2 minutes'
            : detectedMode === 'day-plans'
            ? 'Creating detailed plans for each city...'
            : 'This usually takes 30-60 seconds'}
        </p>
      </div>
    </div>
  );
}
