import { Header } from '@/components/layout/Header';
import { PageContainer } from '@/components/layout/PageContainer';
import { InputForm } from '@/components/trip/InputForm';
import { PlanProgress } from '@/components/trip/PlanProgress';
import { useStreamingPlan } from '@/hooks/useStreamingPlan';
import { useUIStore } from '@/stores/uiStore';
import { useTripStore } from '@/stores/tripStore';

function App() {
  const { phase, isLoading, error, setError } = useUIStore();
  const { journey } = useTripStore();
  const { startPlanning, cancelPlanning } = useStreamingPlan();

  // Suppress unused variable warning -- journey will be used in later tasks
  void journey;

  return (
    <div className="min-h-screen bg-surface-dim">
      <Header />
      <PageContainer>
        {error && (
          <div className="max-w-lg mx-auto mb-4">
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center justify-between">
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
          <PlanProgress onCancel={cancelPlanning} />
        )}

        {/* Other phases will be added in later tasks */}
      </PageContainer>
    </div>
  );
}

export default App;
