import { useCallback } from 'react';
import { Header } from '@/components/layout/Header';
import { PageContainer } from '@/components/layout/PageContainer';
import { InputForm } from '@/components/trip/InputForm';
import { useTripStore } from '@/stores/tripStore';
import { useUIStore } from '@/stores/uiStore';
import type { TripRequest } from '@/types';

function App() {
  const { phase, isLoading } = useUIStore();
  const { journey } = useTripStore();

  // Suppress unused variable warning -- journey will be used in later tasks
  void journey;

  const handleSubmit = useCallback((request: TripRequest) => {
    // Will be connected to streaming in Task 18
    console.log('Planning trip:', request);
  }, []);

  return (
    <div className="min-h-screen bg-surface-dim">
      <Header />
      <PageContainer>
        {phase === 'input' && (
          <InputForm onSubmit={handleSubmit} isLoading={isLoading} />
        )}
        {/* Other phases will be added in later tasks */}
      </PageContainer>
    </div>
  );
}

export default App;
