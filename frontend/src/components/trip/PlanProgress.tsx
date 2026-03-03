import { useUIStore } from '@/stores/uiStore';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2, Search, MapPin, CheckCircle, Wrench, X } from 'lucide-react';

interface PlanProgressProps {
  onCancel: () => void;
  title?: string;
}

const PHASE_CONFIG: Record<string, { icon: typeof Loader2; label: string; color: string }> = {
  scouting: { icon: Search, label: 'Scouting destinations', color: 'text-primary-500' },
  enriching: { icon: MapPin, label: 'Enriching with real data', color: 'text-accent-500' },
  reviewing: { icon: CheckCircle, label: 'Reviewing quality', color: 'text-green-500' },
  improving: { icon: Wrench, label: 'Improving plan', color: 'text-yellow-500' },
  city_start: { icon: MapPin, label: 'Planning city', color: 'text-primary-500' },
  city_complete: { icon: CheckCircle, label: 'City planned', color: 'text-green-500' },
};

export function PlanProgress({ onCancel, title = 'Planning your journey...' }: PlanProgressProps) {
  const { progress } = useUIStore();
  const phase = progress?.phase || 'scouting';
  const config = PHASE_CONFIG[phase] || PHASE_CONFIG.scouting;
  const Icon = config.icon;

  return (
    <Card className="max-w-lg mx-auto mt-12">
      <CardContent className="p-8 text-center space-y-6">
        <h2 className="text-xl font-display font-semibold text-text-primary">{title}</h2>

        <div className="flex items-center justify-center gap-3">
          <Icon className={`h-5 w-5 animate-pulse ${config.color}`} />
          <span className="text-text-secondary">{config.label}</span>
        </div>

        {progress && (
          <>
            <p className="text-sm text-text-muted">{progress.message}</p>

            {/* Progress bar */}
            <div className="w-full bg-surface-muted rounded-full h-2">
              <div
                className="bg-primary-500 h-2 rounded-full transition-all duration-500"
                style={{ width: `${progress.progress}%` }}
              />
            </div>
            <p className="text-xs text-text-muted">{progress.progress}% complete</p>
          </>
        )}

        <Button variant="outline" size="sm" onClick={onCancel}>
          <X className="h-4 w-4 mr-1" />
          Cancel
        </Button>
      </CardContent>
    </Card>
  );
}
