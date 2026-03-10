import { useState } from 'react';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { DayTimeline } from '@/components/trip/DayTimeline';
import type { DayPlan } from '@/types';

interface FullDayViewProps {
  dayPlans: DayPlan[];
  tips: Record<string, string>;
  initialDay?: number;  // day_number to start on
  onClose: () => void;
  onChatAbout?: (activityName: string, dayNumber: number) => void;
}

export function FullDayView({ dayPlans, tips, initialDay, onClose, onChatAbout }: FullDayViewProps) {
  const [currentIndex, setCurrentIndex] = useState(() => {
    if (initialDay) {
      const idx = dayPlans.findIndex(dp => dp.day_number === initialDay);
      return idx >= 0 ? idx : 0;
    }
    return 0;
  });

  const dayPlan = dayPlans[currentIndex];
  if (!dayPlan) return null;

  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex < dayPlans.length - 1;

  const [touchStart, setTouchStart] = useState<number | null>(null);
  const [touchEnd, setTouchEnd] = useState<number | null>(null);
  const minSwipeDistance = 50;

  const onTouchStart = (e: React.TouchEvent) => {
    setTouchEnd(null);
    setTouchStart(e.targetTouches[0].clientX);
  };

  const onTouchMove = (e: React.TouchEvent) => {
    setTouchEnd(e.targetTouches[0].clientX);
  };

  const onTouchEnd = () => {
    if (!touchStart || !touchEnd) return;
    const distance = touchStart - touchEnd;
    const isSwipe = Math.abs(distance) > minSwipeDistance;
    if (isSwipe) {
      if (distance > 0 && hasNext) {
        setCurrentIndex(currentIndex + 1);
      } else if (distance < 0 && hasPrev) {
        setCurrentIndex(currentIndex - 1);
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-surface overflow-y-auto">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-surface/95 backdrop-blur-sm border-b border-border-default">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon-sm" onClick={onClose} aria-label="Close">
              <X className="h-5 w-5" />
            </Button>
            <div>
              <h2 className="text-sm font-display font-semibold text-text-primary">
                Day {dayPlan.day_number} of {dayPlans.length}
              </h2>
              <p className="text-xs text-text-muted">{dayPlan.city_name} — {dayPlan.theme}</p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => setCurrentIndex(i => i - 1)}
              disabled={!hasPrev}
              aria-label="Previous day"
            >
              <ChevronLeft className="h-5 w-5" />
            </Button>
            <span className="text-xs text-text-muted w-12 text-center">
              {currentIndex + 1} / {dayPlans.length}
            </span>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => setCurrentIndex(i => i + 1)}
              disabled={!hasNext}
              aria-label="Next day"
            >
              <ChevronRight className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div
        className="max-w-3xl mx-auto px-4 py-6 space-y-4"
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
      >
        {/* Date + cost summary */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-text-muted">{dayPlan.date}</span>
          {dayPlan.daily_cost_usd != null && dayPlan.daily_cost_usd > 0 && (
            <span className="text-sm font-semibold text-text-primary">~${dayPlan.daily_cost_usd.toFixed(0)}</span>
          )}
        </div>

        {/* Timeline */}
        <DayTimeline dayPlan={dayPlan} tips={tips} onChatAbout={onChatAbout} />

        {currentIndex === 0 && (
          <p className="text-xs text-text-muted text-center mt-2 sm:hidden animate-swipe-hint">
            ← Swipe to navigate between days →
          </p>
        )}
      </div>

      {/* Bottom navigation (mobile-friendly) */}
      <div className="sticky bottom-0 bg-surface/95 backdrop-blur-sm border-t border-border-default py-3 px-4">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentIndex(i => i - 1)}
            disabled={!hasPrev}
          >
            <ChevronLeft className="h-4 w-4 mr-1" />
            {hasPrev && dayPlans[currentIndex - 1].theme.length > 20
              ? 'Previous'
              : hasPrev ? dayPlans[currentIndex - 1].theme : 'Previous'}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentIndex(i => i + 1)}
            disabled={!hasNext}
          >
            {hasNext && dayPlans[currentIndex + 1].theme.length > 20
              ? 'Next'
              : hasNext ? dayPlans[currentIndex + 1].theme : 'Next'}
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        </div>
      </div>
    </div>
  );
}
