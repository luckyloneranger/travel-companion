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
import { useState, useEffect, useRef } from 'react';

export interface ProgressEvent {
  type: 'progress' | 'complete' | 'error';
  phase?: string;
  message?: string;
  progress?: number;
  data?: Record<string, unknown>;
}

// Track city progress for dynamic cards
interface CityProgressState {
  name: string;
  index: number;
  days: number;
  progress: number;
  status: 'pending' | 'in-progress' | 'complete' | 'error';
}

interface GenerationProgressProps {
  progress: ProgressEvent | null;
  destinationName?: string;
  mode?: 'journey' | 'day-plans' | 'itinerary';
  onCancel?: () => void;
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

// Earth-tone colors for different modes
const MODE_COLORS = {
  journey: {
    gradient: 'from-[#C97B5A] to-[#D4956F]',
    iconBg: 'bg-primary-50',
    iconText: 'text-[#C97B5A]',
    activeBg: 'bg-[#C97B5A]',
    completeBg: 'bg-[#8B9E6B]',
    progressGradient: 'from-[#C97B5A] to-[#D4956F]',
    ring: 'ring-[#E8E0D4]',
    border: 'border-[#E8E0D4]',
    bgActive: 'bg-primary-50'
  },
  'day-plans': {
    gradient: 'from-[#8B9E6B] to-[#A3B584]',
    iconBg: 'bg-[#F5F7F0]',
    iconText: 'text-[#728556]',
    activeBg: 'bg-[#8B9E6B]',
    completeBg: 'bg-[#8B9E6B]',
    progressGradient: 'from-[#8B9E6B] to-[#A3B584]',
    ring: 'ring-[#D4DFC4]',
    border: 'border-[#D4DFC4]',
    bgActive: 'bg-[#F5F7F0]'
  },
  itinerary: {
    gradient: 'from-[#8E8478] to-[#A39A8F]',
    iconBg: 'bg-[#F7F5F2]',
    iconText: 'text-[#6E655B]',
    activeBg: 'bg-[#8E8478]',
    completeBg: 'bg-[#8B9E6B]',
    progressGradient: 'from-[#C97B5A] to-[#D4956F]',
    ring: 'ring-[#E8E0D4]',
    border: 'border-[#E8E0D4]',
    bgActive: 'bg-[#F7F5F2]'
  },
};

export function GenerationProgress({ progress, destinationName, mode = 'journey', onCancel }: GenerationProgressProps) {
  // Track city progress history for day-plans mode
  const [cityStates, setCityStates] = useState<CityProgressState[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  
  // Detect mode from phase if not explicitly set
  const detectedMode = progress?.phase?.includes('city_') ? 'day-plans' : 
    ['scout', 'enrich', 'review', 'planner'].includes(progress?.phase || '') ? 'journey' : mode;
  
  const phases = detectedMode === 'day-plans' ? DAY_PLAN_PHASES : 
    detectedMode === 'journey' ? JOURNEY_PHASES : ITINERARY_PHASES;
  
  const colors = MODE_COLORS[detectedMode];
  
  // Find current phase
  const currentPhase = progress?.phase || '';
  const currentPhaseIndex = phases.findIndex(p => currentPhase.startsWith(p.id));
  
  // For day plans, extract city info from progress
  const cityName = progress?.data?.city_name as string | undefined;
  const cityIndex = progress?.data?.city_index as number | undefined;
  const totalCities = progress?.data?.total_cities as number | undefined;
  const cityProgress = progress?.data?.city_progress as number | undefined;
  const cityDays = progress?.data?.city_days as number | undefined;
  
  // Update city states when progress changes (day-plans mode)
  useEffect(() => {
    if (detectedMode !== 'day-plans' || !cityName || cityIndex === undefined) return;
    
    setCityStates(prev => {
      // Create a copy to work with
      const updated = [...prev];
      
      // Find if this city already exists
      const existingIdx = updated.findIndex(c => c.index === cityIndex);
      
      const newState: CityProgressState = {
        name: cityName,
        index: cityIndex,
        days: cityDays || 0,
        progress: cityProgress || 0,
        status: currentPhase === 'city_complete' ? 'complete' : 
                currentPhase === 'city_error' ? 'error' : 'in-progress',
      };
      
      if (existingIdx >= 0) {
        // Update existing city
        updated[existingIdx] = newState;
      } else {
        // Add new city - insert at correct position based on index
        updated.push(newState);
        // Sort by index to maintain order
        updated.sort((a, b) => a.index - b.index);
      }
      
      // When a new city starts, mark all previous (lower index) cities as complete
      // This handles cases where city_complete events might be missed due to rapid updates
      if (currentPhase === 'city_start') {
        for (let i = 0; i < updated.length; i++) {
          if (updated[i].index < cityIndex && updated[i].status === 'in-progress') {
            updated[i] = { ...updated[i], status: 'complete', progress: 100 };
          }
        }
      }
      
      return updated;
    });
  }, [detectedMode, cityName, cityIndex, cityDays, cityProgress, currentPhase]);
  
  // Reset city states when starting fresh (only on actual reset, not on 0%)
  useEffect(() => {
    if (!progress) {
      setCityStates([]);
    }
  }, [progress]);
  
  // Auto-scroll to latest city
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [cityStates]);

  // Title based on mode
  const titles = {
    journey: 'Crafting Your Journey',
    'day-plans': 'Creating Day Plans',
    itinerary: 'Creating Your Itinerary',
  };

  return (
    <div className="rounded-2xl shadow-xl overflow-hidden max-w-lg mx-auto bg-white border border-gray-100/40">
      {/* Header with gradient */}
      <div className={`bg-gradient-to-r ${colors.gradient} p-6 text-white`}>
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-xl bg-white/20 flex items-center justify-center shadow-lg">
            <Loader2 className="w-7 h-7 animate-spin" />
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-display font-bold">{titles[detectedMode]}</h2>
            {destinationName && (
              <p className="text-white/80 text-sm mt-0.5">
                {destinationName}
              </p>
            )}
          </div>
          {onCancel && (
            <button
              onClick={onCancel}
              className="bg-white border border-[#E8E0D4] text-[#3D3229] hover:bg-[#F5F0E8] rounded-xl px-4 py-2 text-sm font-medium transition-colors"
              aria-label="Cancel generation"
            >
              Cancel
            </button>
          )}
        </div>
      </div>

      <div className="p-6">
        {/* Progress Bar */}
        <div className="mb-6">
          <div className="flex justify-between text-sm mb-2" role="status" aria-live="polite">
            <span className="text-gray-700 font-display font-medium">{progress?.message || 'Starting...'}</span>
            <span className="text-gray-500 font-display font-semibold">{progress?.progress || 0}%</span>
          </div>
          <div className="h-1 bg-gray-100/80 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500 ease-out bg-[#C97B5A]"
              style={{ width: `${progress?.progress || 0}%` }}
            />
          </div>
        </div>

        {/* City Progress for day-plans mode - Dynamic Cards */}
        {detectedMode === 'day-plans' && totalCities && (
          <div 
            ref={scrollRef}
            className="mb-6 space-y-3"
          >
            {cityStates.map((city) => {
              const isActive = city.status === 'in-progress';
              const isComplete = city.status === 'complete';
              const isError = city.status === 'error';
              
              return (
                <div 
                  key={city.index}
                  className={`p-4 rounded-xl transition-all duration-300 ${
                    isActive
                      ? 'bg-[#F5F0E8] border border-[#D4DFC4] shadow-sm scale-[1.02]'
                      : isComplete
                      ? 'bg-[#F5F7F0] border border-[#E8E0D4]'
                      : isError
                      ? 'bg-red-50 border border-red-100'
                      : 'bg-gray-50 border border-gray-100'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-display font-bold shadow-md flex-shrink-0 ${
                      isComplete
                        ? 'bg-[#8B9E6B] text-white'
                        : isError
                        ? 'bg-red-500 text-white'
                        : isActive
                        ? 'bg-[#8B9E6B] text-white'
                        : 'bg-gray-300 text-white'
                    }`}>
                      {isComplete ? (
                        <CheckCircle className="w-5 h-5" />
                      ) : isActive ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        city.index
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className={`font-display font-semibold truncate ${
                        isComplete ? 'text-[#728556]' : isActive ? 'text-gray-900' : 'text-gray-500'
                      }`}>
                        {city.name}
                      </div>
                      <div className="text-xs text-gray-500">
                        {city.days} {city.days === 1 ? 'day' : 'days'} • City {city.index} of {totalCities}
                      </div>
                    </div>
                    <div className="text-right flex-shrink-0">
                      {isComplete ? (
                        <div className="text-[#728556] text-sm font-semibold flex items-center gap-1">
                          <CheckCircle className="w-4 h-4" />
                          Done
                        </div>
                      ) : isActive ? (
                        <>
                          <div className="text-lg font-bold text-[#728556] flex items-center gap-1">
                            <Loader2 className="w-4 h-4 animate-spin" />
                          </div>
                          <div className="text-xs text-gray-500">Planning</div>
                        </>
                      ) : isError ? (
                        <div className="text-red-600 text-sm font-semibold">Error</div>
                      ) : (
                        <div className="text-gray-400 text-sm">Waiting</div>
                      )}
                    </div>
                  </div>
                  {/* Animated progress bar for active city */}
                  {isActive && (
                    <div className="mt-3 h-1.5 bg-[#E8E0D4] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[#8B9E6B] rounded-full animate-pulse"
                        style={{ width: '100%', opacity: 0.6 }}
                      />
                    </div>
                  )}
                </div>
              );
            })}
            
            {/* Empty state before any cities start */}
            {cityStates.length === 0 && (
              <div className="p-4 rounded-xl bg-gray-50 border border-gray-100 text-center text-gray-500 text-sm">
                Preparing to generate day plans...
              </div>
            )}
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
                      ? 'bg-[#F5F7F0]'
                      : 'bg-gray-50'
                  }`}
                >
                  <div
                    className={`flex items-center justify-center w-9 h-9 rounded-xl shadow-sm ${
                      isCurrent
                        ? `${colors.activeBg} text-white`
                        : isCompleted
                        ? 'bg-[#8B9E6B] text-white'
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
                      className={`text-sm font-display font-semibold ${
                        isCurrent
                          ? colors.iconText.replace('text-', 'text-')
                          : isCompleted
                          ? 'text-[#728556]'
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
