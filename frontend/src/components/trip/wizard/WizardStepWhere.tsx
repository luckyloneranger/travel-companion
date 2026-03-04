import { MapPin, Navigation } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { TemplateGallery } from '@/components/trip/TemplateGallery';
import type { TripRequest } from '@/types';

interface WizardStepWhereProps {
  destination: string;
  origin: string;
  onDestinationChange: (value: string) => void;
  onOriginChange: (value: string) => void;
  onSelectTemplate: (template: Partial<TripRequest>) => void;
  onNext: () => void;
}

export function WizardStepWhere({
  destination,
  origin,
  onDestinationChange,
  onOriginChange,
  onSelectTemplate,
  onNext,
}: WizardStepWhereProps) {
  return (
    <div className="space-y-8 max-w-lg mx-auto">
      <div className="text-center">
        <h2 className="text-2xl font-display font-bold text-text-primary">
          Where do you want to go?
        </h2>
        <p className="text-sm text-text-muted mt-1">
          Enter a city, country, or region
        </p>
      </div>

      <div className="space-y-4">
        <div className="space-y-2">
          <label htmlFor="wiz-destination" className="text-sm font-medium text-text-primary flex items-center gap-1.5">
            <MapPin className="h-4 w-4 text-primary-500" />
            Destination
          </label>
          <Input
            id="wiz-destination"
            placeholder="e.g. Japan, Paris, Southeast Asia"
            value={destination}
            onChange={(e) => onDestinationChange(e.target.value)}
            className="text-base h-12"
            autoFocus
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="wiz-origin" className="text-sm font-medium text-text-muted flex items-center gap-1.5">
            <Navigation className="h-4 w-4" />
            Starting from <span className="text-xs">(optional)</span>
          </label>
          <Input
            id="wiz-origin"
            placeholder="e.g. London, New York"
            value={origin}
            onChange={(e) => onOriginChange(e.target.value)}
          />
        </div>
      </div>

      <Button
        onClick={onNext}
        disabled={!destination.trim()}
        className="w-full h-11 bg-primary-600 hover:bg-primary-700 text-white"
      >
        Next
      </Button>

      <div className="border-t border-border-default pt-6">
        <TemplateGallery onSelectTemplate={onSelectTemplate} />
      </div>
    </div>
  );
}
