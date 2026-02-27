import { useState, useRef, useCallback } from 'react';
import { Header } from './components/Header';
import { JourneyInputForm } from './components/JourneyInputForm';
import { ItineraryInputForm } from './components/ItineraryInputForm';
import { V6JourneyPlanView } from './components/V6JourneyPlanView';
import { ItineraryView } from './components/ItineraryView';
import { GenerationProgress, type ProgressEvent } from './components/GenerationProgress';
import { JourneyChat } from './components/JourneyChat';
import { planJourneyV6Stream, generateV6DayPlansStream, extractV6JourneyFromEvent, generateItineraryStream } from './services/api';
import { headerGradients } from '@/styles';
import type { 
  JourneyRequest, 
  V6JourneyPlan,
  V6ProgressEvent,
  V6DayPlanProgress,
  V6DayPlan,
} from './types';
import type { ItineraryRequest, ItineraryResponse, ItineraryProgressEvent } from './types/itinerary';

type JourneyPhase = 'input' | 'planning' | 'preview' | 'day-plans';
type AppMode = 'journey' | 'itinerary';

function App() {
  // App mode
  const [appMode, setAppMode] = useState<AppMode>('journey');
  
  // Journey state
  const [journeyPhase, setJourneyPhase] = useState<JourneyPhase>('input');
  const [journeyPlan, setJourneyPlan] = useState<V6JourneyPlan | null>(null);
  const [originalRequest, setOriginalRequest] = useState<JourneyRequest | null>(null);
  const [dayPlans, setDayPlans] = useState<V6DayPlan[] | null>(null);
  
  // Itinerary state
  const [itinerary, setItinerary] = useState<ItineraryResponse | null>(null);
  
  // UI state
  const [loading, setLoading] = useState(false);
  const [generatingDayPlans, setGeneratingDayPlans] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<ProgressEvent | null>(null);
  const [destinationName, setDestinationName] = useState<string>('');
  
  // Abort controller for cancelling in-flight requests
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleJourneySubmit = useCallback(async (request: JourneyRequest) => {
    // Cancel any existing request
    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();
    
    setLoading(true);
    setError(null);
    setProgress(null);
    setJourneyPhase('planning');
    setOriginalRequest(request);
    
    const displayName = request.region || request.destinations?.[0] || 'Your Journey';
    setDestinationName(displayName);

    try {
      // Use V6 LLM-first workflow with Scout → Enrich → Review → Planner loop
      const generator = planJourneyV6Stream(request, abortControllerRef.current.signal);
      let finalPlan: V6JourneyPlan | null = null;
      
      for await (const event of generator) {
        // Map V6 events to progress display
        const progressEvent = mapV6EventToProgress(event);
        setProgress(progressEvent);
        
        // Update destination name from route
        if (event.data?.route) {
          const cities = (event.data.route as string).split(' → ');
          if (cities.length > 1) {
            setDestinationName(cities.slice(1).join(' → '));
          }
        }
        
        // Capture final plan on complete (uses shared extraction function)
        if (event.phase === 'complete' && event.data) {
          finalPlan = extractV6JourneyFromEvent(event);
        }
      }
      
      if (!finalPlan) {
        throw new Error('No journey plan received');
      }
      
      setJourneyPlan(finalPlan);
      setJourneyPhase('preview');
    } catch (err) {
      // Don't show error if request was cancelled
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }
      const message = err instanceof Error ? err.message : 'An unexpected error occurred';
      setError(message);
      setJourneyPhase('input');
    } finally {
      setLoading(false);
      setProgress(null);
      abortControllerRef.current = null;
    }
  }, []);

  const handleReset = useCallback(() => {
    // Cancel any in-flight request
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    
    setJourneyPlan(null);
    setOriginalRequest(null);
    setDayPlans(null);
    setItinerary(null);
    setJourneyPhase('input');
    setError(null);
    setProgress(null);
    setLoading(false);
    setGeneratingDayPlans(false);
  }, []);

  const handleItinerarySubmit = useCallback(async (request: ItineraryRequest) => {
    // Cancel any existing request
    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();
    
    setLoading(true);
    setError(null);
    setProgress(null);
    setJourneyPhase('planning');
    setDestinationName(request.destination);

    try {
      const generator = generateItineraryStream(request, abortControllerRef.current.signal);
      let finalItinerary: ItineraryResponse | null = null;
      
      for await (const event of generator) {
        // Map itinerary events to progress display
        const progressEvent = mapItineraryEventToProgress(event);
        setProgress(progressEvent);
        
        // Capture final itinerary on complete
        if (event.type === 'complete' && event.result) {
          finalItinerary = event.result;
        }
      }
      
      if (!finalItinerary) {
        throw new Error('No itinerary received');
      }
      
      setItinerary(finalItinerary);
      setJourneyPhase('preview');
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }
      const message = err instanceof Error ? err.message : 'An unexpected error occurred';
      setError(message);
      setJourneyPhase('input');
    } finally {
      setLoading(false);
      setProgress(null);
      abortControllerRef.current = null;
    }
  }, []);

  const handleGenerateDayPlans = useCallback(async () => {
    if (!journeyPlan || !originalRequest) return;
    
    // Cancel any existing request
    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();
    
    setGeneratingDayPlans(true);
    setError(null);
    setProgress(null);
    setJourneyPhase('day-plans');
    setDestinationName(`Day plans for ${journeyPlan.route}`);

    try {
      // Generate day plans using fast itinerary generator for each city
      const generator = generateV6DayPlansStream(
        {
          journey: journeyPlan,
          start_date: originalRequest.start_date,
          interests: originalRequest.interests,
          pace: originalRequest.pace,
          travel_mode: 'WALK',  // Default to walking for sightseeing
        },
        abortControllerRef.current.signal
      );

      for await (const event of generator) {
        // Map day plan events to progress display
        const progressEvent = mapDayPlanEventToProgress(event);
        setProgress(progressEvent);

        // On complete, capture the day plans and return to preview
        if (event.phase === 'complete' && event.data?.all_day_plans) {
          setDayPlans(event.data.all_day_plans);
          setJourneyPhase('preview');
        }
      }
    } catch (err) {
      // Don't show error if request was cancelled
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }
      const message = err instanceof Error ? err.message : 'Failed to generate day plans';
      setError(message);
      setJourneyPhase('preview');
    } finally {
      setGeneratingDayPlans(false);
      setProgress(null);
      abortControllerRef.current = null;
    }
  }, [journeyPlan, originalRequest]);

  // Handler for updating journey via chat edits
  const handleJourneyUpdate = useCallback((updatedJourney: V6JourneyPlan) => {
    setJourneyPlan(updatedJourney);
    // Clear day plans since they're now stale
    setDayPlans(null);
  }, []);

  // Handler for updating day plans via chat edits
  const handleDayPlansUpdate = useCallback((updatedDayPlans: V6DayPlan[]) => {
    setDayPlans(updatedDayPlans);
  }, []);

  return (
    <div className="min-h-screen bg-mesh flex flex-col">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1">
        {/* Show full-screen progress only for journey planning, not day plans */}
        {loading && !generatingDayPlans ? (
          <GenerationProgress 
            progress={progress} 
            destinationName={destinationName}
            mode={appMode === 'itinerary' ? 'itinerary' : 'journey'}
          />
        ) : journeyPhase === 'preview' && appMode === 'itinerary' && itinerary ? (
          <ItineraryView
            itinerary={itinerary}
            onReset={handleReset}
            loading={loading}
          />
        ) : (journeyPhase === 'preview' || journeyPhase === 'day-plans') && journeyPlan ? (
          <>
            <V6JourneyPlanView
              journey={journeyPlan}
              dayPlans={dayPlans}
              startDate={originalRequest?.start_date}
              onReset={handleReset}
              onGenerateDayPlans={handleGenerateDayPlans}
              loading={loading}
              generatingDayPlans={generatingDayPlans}
            />
            {/* Chat for editing - switches mode based on whether day plans exist */}
            {dayPlans && dayPlans.length > 0 ? (
              <JourneyChat
                mode="dayplan"
                dayPlans={dayPlans}
                onDayPlansUpdate={handleDayPlansUpdate}
                context={originalRequest ? {
                  interests: originalRequest.interests,
                  pace: originalRequest.pace,
                } : undefined}
              />
            ) : (
              <JourneyChat
                mode="journey"
                journey={journeyPlan}
                onJourneyUpdate={handleJourneyUpdate}
                context={originalRequest ? {
                  origin: originalRequest.origin,
                  region: originalRequest.region,
                  interests: originalRequest.interests,
                  pace: originalRequest.pace,
                } : undefined}
              />
            )}
          </>
        ) : (
          <div className="max-w-2xl mx-auto">
            {/* Hero Section */}
            <div className="text-center mb-8">
              <h1 className="text-4xl font-display font-extrabold text-gray-900 mb-4 tracking-tight">
                Plan Your Dream {appMode === 'journey' ? 'Journey' : 'Trip'}
              </h1>
              <p className="text-lg text-gray-600 max-w-xl mx-auto">
                {appMode === 'journey' 
                  ? 'Tell us where you want to go and what you love. Our AI will craft the perfect multi-city adventure tailored just for you.'
                  : 'Create a detailed day-by-day itinerary for your single-city adventure with AI-powered recommendations.'
                }
              </p>
            </div>

            {/* Mode Toggle */}
            <div className="flex justify-center mb-8">
              <div className="glass-strong rounded-2xl p-1.5 shadow-lg border border-white/60 inline-flex">
                <button
                  onClick={() => setAppMode('journey')}
                  className={`px-6 py-2.5 rounded-xl font-display font-semibold text-sm transition-all duration-300 ${
                    appMode === 'journey'
                      ? 'text-white shadow-md'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'
                  }`}
                  style={appMode === 'journey' ? { background: `linear-gradient(135deg, ${headerGradients.journey.from}, ${headerGradients.journey.to})` } : {}}
                >
                  Multi-City Journey
                </button>
                <button
                  onClick={() => setAppMode('itinerary')}
                  className={`px-6 py-2.5 rounded-xl font-display font-semibold text-sm transition-all duration-300 ${
                    appMode === 'itinerary'
                      ? 'text-white shadow-md'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'
                  }`}
                  style={appMode === 'itinerary' ? { background: `linear-gradient(135deg, ${headerGradients.stats.from}, ${headerGradients.stats.to})` } : {}}
                >
                  Single-City Itinerary
                </button>
              </div>
            </div>

            {/* Form based on mode */}
            {appMode === 'journey' ? (
              <JourneyInputForm
                onSubmit={handleJourneySubmit}
                loading={loading}
                error={error}
              />
            ) : (
              <ItineraryInputForm
                onSubmit={handleItinerarySubmit}
                loading={loading}
                error={error}
              />
            )}
          </div>
        )}
      </main>

      {/* Day Plan Generation Side Panel - Slides in from right */}
      {generatingDayPlans && (
        <div className="fixed right-0 top-0 h-full w-full sm:w-96 bg-white/95 backdrop-blur-xl shadow-2xl z-50 flex flex-col transform transition-transform duration-300 ease-out border-l border-white/60">
          {/* Panel Header */}
          <div className="bg-gradient-to-r from-emerald-600 to-teal-600 p-4 text-white flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-white/20 flex items-center justify-center">
                <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
              </div>
              <div>
                <h3 className="font-display font-bold">Creating Day Plans</h3>
                <p className="text-sm text-white/80 truncate max-w-[200px]">{destinationName}</p>
              </div>
            </div>
          </div>
          
          {/* Panel Content */}
          <div className="flex-1 overflow-y-auto p-4">
            <GenerationProgress 
              progress={progress} 
              destinationName={destinationName}
              mode="day-plans"
            />
          </div>
        </div>
      )}

      {/* Backdrop for mobile */}
      {generatingDayPlans && (
        <div className="fixed inset-0 bg-black/20 z-40 sm:hidden" />
      )}

      <footer className="glass border-t border-white/40 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-gray-400 text-sm font-medium">
            Powered by Azure OpenAI & Google APIs
          </p>
        </div>
      </footer>
    </div>
  );
}

/**
 * Map V6 progress events to GenerationProgress component format
 */
function mapV6EventToProgress(event: V6ProgressEvent): ProgressEvent {
  const phaseEmojis: Record<string, string> = {
    scout: '🔭',
    enrich: '🗺️',
    review: '🔍',
    planner: '🛠️',
    complete: '🎉',
    error: '❌',
  };

  const stepMessages: Record<string, Record<string, string>> = {
    scout: {
      start: 'Scout is generating initial journey plan...',
      complete: 'Scout found the perfect route!',
    },
    enrich: {
      start: 'Enriching plan with real transport data...',
      complete: 'Transport data enriched!',
    },
    review: {
      start: 'Reviewing journey feasibility...',
      complete: 'Review complete!',
    },
    planner: {
      start: 'Planner is fixing issues...',
      complete: 'Plan revised!',
    },
  };

  const emoji = phaseEmojis[event.phase] || '📍';
  let message = event.message;
  
  // Use more descriptive message if available
  if (!message && stepMessages[event.phase]?.[event.step]) {
    message = stepMessages[event.phase][event.step];
  }
  
  // Add iteration info for multiple iterations
  if (event.iteration > 1) {
    message = `[Iteration ${event.iteration}] ${message}`;
  }

  return {
    type: 'progress',
    phase: event.phase,
    message: `${emoji} ${message}`,
    progress: event.progress,
    data: {
      destination: event.data?.route as string,
      ...event.data,
    },
  };
}

/**
 * Map day plan progress events to GenerationProgress component format
 */
function mapDayPlanEventToProgress(event: V6DayPlanProgress): ProgressEvent {
  const phaseEmojis: Record<string, string> = {
    city_start: '🏙️',
    city_complete: '✅',
    city_error: '⚠️',
    complete: '🎉',
    error: '❌',
  };

  const emoji = phaseEmojis[event.phase] || '📍';
  const cityInfo = event.city_name ? ` - ${event.city_name}` : '';
  const progressInfo = event.total_cities > 0 
    ? ` (${event.city_index + 1}/${event.total_cities})`
    : '';

  return {
    type: 'progress',
    phase: event.phase,
    message: `${emoji} ${event.message}${cityInfo}${progressInfo}`,
    progress: event.progress,
    data: {
      city_name: event.city_name,
      city_index: event.city_index,
      total_cities: event.total_cities,
      city_days: event.city_days,
      city_progress: event.city_progress,
      ...event.data,
    },
  };
}

/**
 * Map itinerary progress events to GenerationProgress component format
 */
function mapItineraryEventToProgress(event: ItineraryProgressEvent): ProgressEvent {
  const phaseEmojis: Record<string, string> = {
    geocoding: '📍',
    discovering: '🔍',
    planning: '🧠',
    optimizing: '🗺️',
    scheduling: '📅',
    validating: '✅',
    complete: '🎉',
    error: '❌',
  };

  const emoji = phaseEmojis[event.phase || ''] || '📍';
  
  return {
    type: event.type,
    phase: event.phase || '',
    message: `${emoji} ${event.message || 'Processing...'}`,
    progress: event.progress || 0,
    data: {},
  };
}

export default App;
