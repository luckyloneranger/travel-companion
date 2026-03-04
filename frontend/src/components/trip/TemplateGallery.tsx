import type { TripRequest } from '@/types';

interface TripTemplate {
  title: string;
  emoji: string;
  subtitle: string;
  request: Partial<TripRequest>;
}

const TEMPLATES: TripTemplate[] = [
  {
    title: 'Weekend in Paris',
    emoji: '🗼',
    subtitle: '3 days · 2 adults · food, culture, art',
    request: {
      destination: 'Paris, France',
      total_days: 3,
      interests: ['food', 'culture', 'art'],
      pace: 'moderate',
      budget: 'moderate',
      travelers: { adults: 2, children: 0, infants: 0 },
    },
  },
  {
    title: '10 Days in Japan',
    emoji: '🏯',
    subtitle: '10 days · solo · food, culture, nature',
    request: {
      destination: 'Japan',
      total_days: 10,
      interests: ['food', 'culture', 'nature'],
      pace: 'moderate',
      budget: 'moderate',
      travelers: { adults: 1, children: 0, infants: 0 },
    },
  },
  {
    title: 'SE Asia Backpacking',
    emoji: '🎒',
    subtitle: '14 days · 3 friends · adventure, food',
    request: {
      destination: 'Southeast Asia',
      total_days: 14,
      interests: ['adventure', 'food', 'nature'],
      pace: 'packed',
      budget: 'budget',
      travelers: { adults: 3, children: 0, infants: 0 },
    },
  },
  {
    title: 'Italian Family Trip',
    emoji: '🍝',
    subtitle: '7 days · 2 adults, 2 kids · food, culture',
    request: {
      destination: 'Italy',
      total_days: 7,
      interests: ['food', 'culture', 'history'],
      pace: 'relaxed',
      budget: 'moderate',
      travelers: { adults: 2, children: 2, infants: 0 },
    },
  },
  {
    title: 'Greek Honeymoon',
    emoji: '🏖️',
    subtitle: '10 days · couple · beach, nature, food',
    request: {
      destination: 'Greek Islands',
      total_days: 10,
      interests: ['beach', 'nature', 'food'],
      pace: 'relaxed',
      budget: 'luxury',
      travelers: { adults: 2, children: 0, infants: 0 },
    },
  },
  {
    title: 'NYC City Break',
    emoji: '🗽',
    subtitle: '4 days · 4 adults · food, culture, nightlife',
    request: {
      destination: 'New York City',
      total_days: 4,
      interests: ['food', 'culture', 'shopping', 'nightlife'],
      pace: 'packed',
      budget: 'moderate',
      travelers: { adults: 4, children: 0, infants: 0 },
    },
  },
];

interface TemplateGalleryProps {
  onSelectTemplate: (template: Partial<TripRequest>) => void;
}

export function TemplateGallery({ onSelectTemplate }: TemplateGalleryProps) {
  return (
    <div>
      <h3 className="text-sm font-medium text-text-muted mb-3">Quick Start</h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {TEMPLATES.map((template) => (
          <button
            key={template.title}
            type="button"
            onClick={() => onSelectTemplate(template.request)}
            className="flex flex-col items-start gap-1 rounded-lg border border-border-default bg-surface p-3 text-left transition-all hover:border-primary-300 hover:bg-primary-50/50 dark:hover:border-primary-700 dark:hover:bg-primary-900/20 hover:shadow-sm"
          >
            <span className="text-2xl" role="img" aria-hidden="true">
              {template.emoji}
            </span>
            <span className="text-sm font-medium text-text-primary">
              {template.title}
            </span>
            <span className="text-xs text-text-muted">
              {template.subtitle}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
