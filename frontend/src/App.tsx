import { useState, useRef, useCallback } from 'react';
import { Header } from './components/Header';
import { JourneyInputForm } from './components/JourneyInputForm';
import { V6JourneyPlanView } from './components/V6JourneyPlanView';
import { GenerationProgress, type ProgressEvent } from './components/GenerationProgress';
import { planJourneyV6Stream, generateV6DayPlansStream, extractV6JourneyFromEvent } from './services/api';
import type { 
  JourneyRequest, 
  V6JourneyPlan,
  V6ProgressEvent,
  V6DayPlanProgress,
  V6DayPlan,
} from './types';

type JourneyPhase = 'input' | 'planning' | 'preview' | 'day-plans';

function App() {
  // Journey state
  const [journeyPhase, setJourneyPhase] = useState<JourneyPhase>('input');
  const [journeyPlan, setJourneyPlan] = useState<V6JourneyPlan | null>(null);
  const [originalRequest, setOriginalRequest] = useState<JourneyRequest | null>(null);
  const [dayPlans, setDayPlans] = useState<V6DayPlan[] | null>(null);
  
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
    setJourneyPhase('input');
    setError(null);
    setProgress(null);
    setLoading(false);
    setGeneratingDayPlans(false);
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {(loading || generatingDayPlans) ? (
          <GenerationProgress 
            progress={progress} 
            destinationName={destinationName}
            mode={generatingDayPlans ? 'day-plans' : 'journey'}
          />
        ) : journeyPhase === 'preview' && journeyPlan ? (
          <V6JourneyPlanView
            journey={journeyPlan}
            dayPlans={dayPlans}
            onReset={handleReset}
            onGenerateDayPlans={handleGenerateDayPlans}
            loading={loading}
            generatingDayPlans={generatingDayPlans}
          />
        ) : (
          <div className="max-w-2xl mx-auto">
            {/* Hero Section */}
            <div className="text-center mb-10">
              <h1 className="text-4xl font-bold text-gray-900 mb-4">
                Plan Your Dream Journey
              </h1>
              <p className="text-lg text-gray-600 max-w-xl mx-auto">
                Tell us where you want to go and what you love. Our AI will craft 
                the perfect multi-city adventure tailored just for you.
              </p>
            </div>

            {/* Journey Input Form */}
            <JourneyInputForm
              onSubmit={handleJourneySubmit}
              loading={loading}
              error={error}
            />
          </div>
        )}
      </main>

      <footer className="bg-white/50 backdrop-blur border-t mt-auto py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-gray-500 text-sm">
            Powered by Azure OpenAI & Google APIs • V6 Architecture
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
      city_progress: event.city_progress,
      ...event.data,
    },
  };
}

export default App;
