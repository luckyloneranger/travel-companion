import { useState } from 'react';
import {
  Utensils, Landmark, Trees, Moon, ShoppingBag, Mountain,
  BookOpen, Palette, Building2, Armchair, Gauge, Footprints,
  ArrowLeft, Plus, X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { Pace } from '@/types';

const INTEREST_OPTIONS = [
  { id: 'food', label: 'Food', icon: Utensils },
  { id: 'culture', label: 'Culture', icon: Landmark },
  { id: 'nature', label: 'Nature', icon: Trees },
  { id: 'nightlife', label: 'Nightlife', icon: Moon },
  { id: 'shopping', label: 'Shopping', icon: ShoppingBag },
  { id: 'adventure', label: 'Adventure', icon: Mountain },
  { id: 'history', label: 'History', icon: BookOpen },
  { id: 'art', label: 'Art', icon: Palette },
  { id: 'architecture', label: 'Architecture', icon: Building2 },
];

const PACE_OPTIONS: { id: Pace; label: string; description: string; icon: typeof Armchair }[] = [
  { id: 'relaxed', label: 'Relaxed', description: '3-5 activities/day — slow, easy-going', icon: Armchair },
  { id: 'moderate', label: 'Moderate', description: '5-7 activities/day — balanced exploration', icon: Footprints },
  { id: 'packed', label: 'Packed', description: '7-10 activities/day — maximize sightseeing', icon: Gauge },
];

interface WizardStepStyleProps {
  interests: string[];
  pace: Pace;
  mustInclude: string[];
  avoid: string[];
  onInterestsChange: (interests: string[]) => void;
  onPaceChange: (pace: Pace) => void;
  onMustIncludeChange: (items: string[]) => void;
  onAvoidChange: (items: string[]) => void;
  onNext: () => void;
  onBack: () => void;
}

function TagInput({
  label,
  placeholder,
  values,
  onChange,
}: {
  label: string;
  placeholder: string;
  values: string[];
  onChange: (values: string[]) => void;
}) {
  const [input, setInput] = useState('');

  const addTag = () => {
    const trimmed = input.trim();
    if (trimmed && !values.includes(trimmed)) {
      onChange([...values, trimmed]);
      setInput('');
    }
  };

  return (
    <div className="space-y-2">
      <span className="text-sm font-medium text-text-muted">{label}</span>
      <div className="flex gap-2">
        <Input
          placeholder={placeholder}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
          className="flex-1"
        />
        <Button type="button" variant="outline" size="icon" onClick={addTag} disabled={!input.trim()}>
          <Plus className="h-4 w-4" />
        </Button>
      </div>
      {values.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {values.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1 rounded-full bg-primary-100 dark:bg-primary-900/30 px-2.5 py-0.5 text-xs font-medium text-primary-700 dark:text-primary-300"
            >
              {tag}
              <button type="button" onClick={() => onChange(values.filter((v) => v !== tag))} className="hover:text-red-500">
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export function WizardStepStyle({
  interests,
  pace,
  mustInclude,
  avoid,
  onInterestsChange,
  onPaceChange,
  onMustIncludeChange,
  onAvoidChange,
  onNext,
  onBack,
}: WizardStepStyleProps) {
  const toggleInterest = (id: string) => {
    onInterestsChange(
      interests.includes(id) ? interests.filter((i) => i !== id) : [...interests, id],
    );
  };

  return (
    <div className="space-y-8 max-w-lg mx-auto">
      <div className="text-center">
        <h2 className="text-2xl font-display font-bold text-text-primary">
          What's your style?
        </h2>
        <p className="text-sm text-text-muted mt-1">
          Pick your interests and travel pace
        </p>
      </div>

      {/* Interests */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-text-primary">Interests</h3>
        <div className="grid grid-cols-3 gap-2">
          {INTEREST_OPTIONS.map((opt) => {
            const Icon = opt.icon;
            const selected = interests.includes(opt.id);
            return (
              <button
                key={opt.id}
                type="button"
                onClick={() => toggleInterest(opt.id)}
                className={`flex flex-col items-center gap-1.5 rounded-xl border p-3 transition-all hover:scale-[1.03] active:scale-[0.98] ${
                  selected
                    ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 ring-1 ring-primary-500 shadow-sm shadow-primary-500/10'
                    : 'border-border-default bg-surface text-text-secondary hover:border-primary-300 hover:bg-primary-50/30 dark:hover:bg-primary-900/10 hover:shadow-sm'
                }`}
              >
                <Icon className="h-5 w-5" />
                <span className="text-sm font-medium">{opt.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Pace */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-text-primary">Pace</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {PACE_OPTIONS.map((opt) => {
            const Icon = opt.icon;
            const selected = pace === opt.id;
            return (
              <button
                key={opt.id}
                type="button"
                onClick={() => onPaceChange(opt.id)}
                className={`flex items-center gap-3 rounded-xl border p-4 text-left transition-all hover:scale-[1.02] active:scale-[0.98] ${
                  selected
                    ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30 ring-1 ring-primary-500 shadow-sm'
                    : 'border-border-default bg-surface hover:border-primary-300 hover:shadow-sm'
                }`}
              >
                <Icon className={`h-6 w-6 shrink-0 ${selected ? 'text-primary-600 dark:text-primary-400' : 'text-text-muted'}`} />
                <div>
                  <span className={`text-sm font-semibold ${selected ? 'text-primary-700 dark:text-primary-300' : 'text-text-primary'}`}>
                    {opt.label}
                  </span>
                  <p className="text-xs text-text-muted mt-0.5">{opt.description}</p>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Must Include / Avoid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <TagInput
          label="Must include (optional)"
          placeholder="e.g. Eiffel Tower"
          values={mustInclude}
          onChange={onMustIncludeChange}
        />
        <TagInput
          label="Avoid (optional)"
          placeholder="e.g. crowded malls"
          values={avoid}
          onChange={onAvoidChange}
        />
      </div>

      <div className="flex gap-3">
        <Button variant="outline" onClick={onBack} className="flex-1">
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>
        <Button
          onClick={onNext}
          className="flex-1 h-12 bg-primary-600 hover:bg-primary-700 text-white text-base font-semibold shadow-sm"
        >
          Continue
        </Button>
      </div>
    </div>
  );
}
