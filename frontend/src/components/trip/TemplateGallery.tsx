import type { TripRequest } from '@/types';

interface TripTemplate {
  title: string;
  emoji: string;
  subtitle: string;
  gradient: string;
  request: Partial<TripRequest>;
}

const TEMPLATES: TripTemplate[] = [
  {
    title: 'Weekend in Paris',
    emoji: '🗼',
    subtitle: '3 days · 2 adults · food, culture, art',
    gradient: 'from-rose-500/10 to-pink-500/5 dark:from-rose-500/15 dark:to-pink-500/10 hover:from-rose-500/20 hover:to-pink-500/10',
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
    gradient: 'from-red-500/10 to-amber-500/5 dark:from-red-500/15 dark:to-amber-500/10 hover:from-red-500/20 hover:to-amber-500/10',
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
    gradient: 'from-emerald-500/10 to-teal-500/5 dark:from-emerald-500/15 dark:to-teal-500/10 hover:from-emerald-500/20 hover:to-teal-500/10',
    request: {
      destination: 'Southeast Asia',
      total_days: 14,
      interests: ['adventure', 'food', 'nature'],
      pace: 'moderate',
      budget: 'budget',
      travelers: { adults: 3, children: 0, infants: 0 },
    },
  },
  {
    title: 'Italian Family Trip',
    emoji: '🍝',
    subtitle: '7 days · 2 adults, 2 kids · food, culture',
    gradient: 'from-orange-500/10 to-yellow-500/5 dark:from-orange-500/15 dark:to-yellow-500/10 hover:from-orange-500/20 hover:to-yellow-500/10',
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
    gradient: 'from-sky-500/10 to-blue-500/5 dark:from-sky-500/15 dark:to-blue-500/10 hover:from-sky-500/20 hover:to-blue-500/10',
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
    gradient: 'from-slate-500/10 to-zinc-500/5 dark:from-slate-500/15 dark:to-zinc-500/10 hover:from-slate-500/20 hover:to-zinc-500/10',
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
        {TEMPLATES.map((template, i) => (
          <button
            key={template.title}
            type="button"
            onClick={() => onSelectTemplate(template.request)}
            className={`flex flex-col items-start gap-1.5 rounded-xl border border-border-default bg-gradient-to-br ${template.gradient} p-3.5 text-left transition-all hover:shadow-md hover:border-primary-300/50 dark:hover:border-primary-700/50 focus-visible:ring-2 focus-visible:ring-primary-500/50 animate-stagger-in stagger-${Math.min(i + 1, 6)}`}
          >
            <span className="text-2xl" role="img" aria-hidden="true">
              {template.emoji}
            </span>
            <span className="text-sm font-semibold text-text-primary">
              {template.title}
            </span>
            <span className="text-xs text-text-muted leading-relaxed">
              {template.subtitle}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
