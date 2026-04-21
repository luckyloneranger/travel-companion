interface LoadingScreenProps {
  progress: number;
  error?: string | null;
}

export default function LoadingScreen({ progress, error }: LoadingScreenProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
      <div className="text-center">
        {/* Spinner */}
        <div className="w-16 h-16 mx-auto mb-6 border-4 border-muted border-t-primary rounded-full animate-spin" />

        <h2 className="text-xl font-semibold mb-2">Preparing your trip...</h2>
        <p className="text-muted-foreground mb-6">Assembling the perfect itinerary from our curated plans</p>

        {/* Progress bar */}
        <div className="w-64 mx-auto h-2 rounded-full bg-muted overflow-hidden">
          <div
            className="h-full bg-primary rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
        <p className="text-sm text-muted-foreground mt-2">{progress}% complete</p>

        {error && (
          <div className="mt-6 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm max-w-sm">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
