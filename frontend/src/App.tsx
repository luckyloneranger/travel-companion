import { useCallback } from 'react';
import { Header } from '@/components/layout/Header';
import { PageContainer } from '@/components/layout/PageContainer';
import { ChatPanel } from '@/components/trip/ChatPanel';
import { InputForm } from '@/components/trip/InputForm';
import { PlanProgress } from '@/components/trip/PlanProgress';
import { JourneyPreview } from '@/components/trip/JourneyPreview';
import { DayCard } from '@/components/trip/DayCard';
import { useStreamingPlan } from '@/hooks/useStreamingPlan';
import { useStreamingDayPlans } from '@/hooks/useStreamingDayPlans';
import { useUIStore } from '@/stores/uiStore';
import { useTripStore } from '@/stores/tripStore';
import { Button } from '@/components/ui/button';
import { ArrowLeft, MessageSquare } from 'lucide-react';

function App() {
  const { phase, isLoading, error, setError, setPhase } = useUIStore();
  const { journey, dayPlans } = useTripStore();
  const { startPlanning, cancelPlanning } = useStreamingPlan();
  const { startGenerating, cancelGenerating } = useStreamingDayPlans();

  const handleGenerateDayPlans = useCallback(() => {
    startGenerating();
  }, [startGenerating]);

  const handleOpenChat = useCallback(() => {
    useUIStore.getState().openChat('journey');
  }, []);

  const handleOpenDayPlanChat = useCallback(() => {
    useUIStore.getState().openChat('day_plans');
  }, []);

  const handleBackToPreview = useCallback(() => {
    setPhase('preview');
  }, [setPhase]);

  // Determine which cancel handler to use based on context
  const handleCancelPlanning = useCallback(() => {
    // If we came from preview (day plan generation), go back to preview
    if (journey) {
      cancelGenerating();
    } else {
      cancelPlanning();
    }
  }, [journey, cancelGenerating, cancelPlanning]);

  // Group day plans by city
  const dayPlansByCity = dayPlans
    ? dayPlans.reduce<Record<string, typeof dayPlans>>((acc, plan) => {
        const city = plan.city_name;
        if (!acc[city]) acc[city] = [];
        acc[city].push(plan);
        return acc;
      }, {})
    : {};

  return (
    <div className="min-h-screen bg-surface-dim">
      <Header />
      <PageContainer>
        {error && (
          <div className="max-w-lg mx-auto mb-4">
            <div role="alert" className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center justify-between">
              <p className="text-sm">{error}</p>
              <button
                onClick={() => setError(null)}
                className="text-red-500 hover:text-red-700 font-bold text-lg leading-none"
                aria-label="Dismiss error"
              >
                &times;
              </button>
            </div>
          </div>
        )}

        {phase === 'input' && (
          <InputForm onSubmit={startPlanning} isLoading={isLoading} />
        )}

        {phase === 'planning' && (
          <PlanProgress onCancel={handleCancelPlanning} />
        )}

        {phase === 'preview' && journey && (
          <JourneyPreview
            onGenerateDayPlans={handleGenerateDayPlans}
            onOpenChat={handleOpenChat}
          />
        )}

        {phase === 'day-plans' && dayPlans && dayPlans.length > 0 && (
          <div className="space-y-6">
            {/* Day plans header */}
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleBackToPreview}
                >
                  <ArrowLeft className="h-4 w-4" />
                  Back to Overview
                </Button>
                <h2 className="text-lg font-display font-bold text-text-primary">
                  Day Plans
                </h2>
              </div>
              <Button variant="outline" size="sm" onClick={handleOpenDayPlanChat}>
                <MessageSquare className="h-4 w-4" />
                Edit via Chat
              </Button>
            </div>

            {/* Day plans grouped by city */}
            {Object.entries(dayPlansByCity).map(([cityName, plans]) => (
              <div key={cityName} className="space-y-3">
                <h3 className="text-sm font-semibold text-text-muted uppercase tracking-wider px-1">
                  {cityName}
                </h3>
                <div className="space-y-4">
                  {plans.map((plan) => (
                    <DayCard key={plan.day_number} dayPlan={plan} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </PageContainer>

      <ChatPanel />
    </div>
  );
}

export default App;
