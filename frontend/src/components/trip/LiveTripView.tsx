import { useMemo } from 'react';
import { MapPin, Clock, Navigation, ArrowRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { DayTimeline } from '@/components/trip/DayTimeline';
import type { DayPlan } from '@/types';

interface LiveTripViewProps {
  dayPlans: DayPlan[];
  tips: Record<string, string>;
  tripStartDate: string;  // ISO date string
  onChatAbout?: (activityName: string, dayNumber: number) => void;
}

export function LiveTripView({ dayPlans, tips, tripStartDate, onChatAbout }: LiveTripViewProps) {
  const today = new Date().toISOString().split('T')[0];

  const todayPlan = useMemo(() => {
    return dayPlans.find(dp => dp.date === today);
  }, [dayPlans, today]);

  const currentActivity = useMemo(() => {
    if (!todayPlan) return null;
    const now = new Date();
    const currentTime = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    // Find the activity that is currently happening or next up
    for (const activity of todayPlan.activities) {
      if (activity.duration_minutes === 0) continue;
      if (activity.time_end > currentTime) return activity;
    }
    return null;
  }, [todayPlan]);

  if (!todayPlan) {
    // Not a trip day — show message
    const startDate = new Date(tripStartDate);
    const todayDate = new Date(today);
    const daysUntil = Math.ceil((startDate.getTime() - todayDate.getTime()) / (1000 * 60 * 60 * 24));

    return (
      <div className="text-center py-12 space-y-3">
        <MapPin className="h-8 w-8 text-text-muted mx-auto" />
        <h3 className="text-lg font-display font-semibold text-text-primary">
          {daysUntil > 0 ? `Trip starts in ${daysUntil} days` : 'Trip has ended'}
        </h3>
        <p className="text-sm text-text-muted">
          {daysUntil > 0
            ? 'Come back on your travel day for live guidance!'
            : 'Hope you had an amazing trip!'}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Current/next activity highlight */}
      {currentActivity && (
        <div className="rounded-lg border-2 border-primary-400 dark:border-primary-600 bg-primary-50 dark:bg-primary-950/30 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Badge variant="default" className="bg-primary-500 text-white">Now</Badge>
            <span className="text-xs text-text-muted flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {currentActivity.time_start} – {currentActivity.time_end}
            </span>
          </div>
          <h3 className="text-base font-semibold text-text-primary">{currentActivity.place.name}</h3>
          {currentActivity.place.address && (
            <p className="text-sm text-text-muted flex items-center gap-1 mt-1">
              <MapPin className="h-3.5 w-3.5" />{currentActivity.place.address}
            </p>
          )}
          {currentActivity.route_to_next && (
            <div className="mt-3 flex items-center gap-2">
              <ArrowRight className="h-4 w-4 text-primary-500" />
              <span className="text-sm text-text-secondary">
                Next: walk/drive to next activity
              </span>
              <a
                href={`https://www.google.com/maps/dir/?api=1&destination=${currentActivity.place.location.lat},${currentActivity.place.location.lng}`}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-auto"
              >
                <Button variant="outline" size="sm">
                  <Navigation className="h-3.5 w-3.5 mr-1" />Navigate
                </Button>
              </a>
            </div>
          )}
        </div>
      )}

      {/* Full day timeline */}
      <div>
        <h3 className="text-sm font-display font-semibold text-text-primary mb-3">
          Day {todayPlan.day_number}: {todayPlan.theme}
        </h3>
        <DayTimeline dayPlan={todayPlan} tips={tips} onChatAbout={onChatAbout} />
      </div>
    </div>
  );
}
