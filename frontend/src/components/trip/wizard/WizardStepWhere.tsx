import { useState } from 'react';
import { MapPin, Navigation, LocateFixed, Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { TemplateGallery } from '@/components/trip/TemplateGallery';
import { showToast } from '@/components/ui/toast';
import { api } from '@/services/api';
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
  const [locating, setLocating] = useState(false);

  const handleLocateMe = async () => {
    if (!navigator.geolocation) return;
    setLocating(true);
    try {
      const pos = await new Promise<GeolocationPosition>((resolve, reject) =>
        navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000 })
      );
      const results = await api.searchPlaces(
        'city',
        pos.coords.latitude,
        pos.coords.longitude,
      );
      if (results.length > 0) {
        onOriginChange(results[0].name);
      }
    } catch {
      showToast('Location access denied — enter your city manually', 'error');
    } finally {
      setLocating(false);
    }
  };

  return (
    <div className="space-y-8 max-w-lg mx-auto">
      <div className="text-center">
        <h2 className="text-2xl font-display font-bold text-text-primary">
          Where do you want to go?
        </h2>
        <p className="text-sm text-text-muted mt-1">
          A city, country, or entire region — we'll handle the rest
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
            className="text-base h-11 shadow-sm"
            autoFocus
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="wiz-origin" className="text-sm font-medium text-text-muted flex items-center gap-1.5">
            <Navigation className="h-4 w-4" />
            Starting from <span className="text-xs">(optional)</span>
          </label>
          <div className="relative">
            <Input
              id="wiz-origin"
              placeholder="e.g. London, New York"
              value={origin}
              onChange={(e) => onOriginChange(e.target.value)}
              className="pr-10"
            />
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              onClick={handleLocateMe}
              disabled={locating}
              className="absolute right-1 top-1/2 -translate-y-1/2 text-text-muted hover:text-primary-600"
              title="Use my location"
            >
              {locating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <LocateFixed className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </div>

      <Button
        onClick={onNext}
        disabled={!destination.trim()}
        className="w-full h-12 bg-primary-600 hover:bg-primary-700 text-white text-base font-semibold shadow-sm"
      >
        Continue
      </Button>
      {!destination && (
        <p className="text-xs text-text-muted mt-1">Enter a destination to continue</p>
      )}

      <div className="border-t border-border-default pt-6">
        <TemplateGallery onSelectTemplate={onSelectTemplate} />
      </div>
    </div>
  );
}
