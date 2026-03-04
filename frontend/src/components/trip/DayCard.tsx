import { useState } from 'react';
import { Calendar, MapPin, ChevronDown } from 'lucide-react';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { ActivityCard } from '@/components/trip/ActivityCard';
import type { DayPlan } from '@/types';

interface DayCardProps {
  dayPlan: DayPlan;
}

export function DayCard({ dayPlan }: DayCardProps) {
  const [isOpen, setIsOpen] = useState(true);

  const formatDate = (dateStr: string): string => {
    try {
      const date = new Date(dateStr + 'T00:00:00');
      return date.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <Card>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-3 min-w-0">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary-600 text-sm font-bold text-white shrink-0">
                {dayPlan.day_number}
              </div>
              <div className="min-w-0">
                <CardTitle className="text-base font-display truncate">
                  Day {dayPlan.day_number}: {dayPlan.theme}
                </CardTitle>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="flex items-center gap-1 text-xs text-text-muted">
                    <Calendar className="h-3 w-3" />
                    {formatDate(dayPlan.date)}
                  </span>
                  <Badge variant="secondary" className="text-[10px]">
                    <MapPin className="h-2.5 w-2.5 mr-0.5" />
                    {dayPlan.city_name}
                  </Badge>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
              <span className="text-xs text-text-muted">
                {dayPlan.activities.length}{' '}
                {dayPlan.activities.length === 1 ? 'activity' : 'activities'}
              </span>
              <CollapsibleTrigger asChild>
                <Button variant="ghost" size="icon-xs" aria-label={isOpen ? `Collapse day ${dayPlan.day_number}` : `Expand day ${dayPlan.day_number}`}>
                  <ChevronDown
                    className={`h-4 w-4 text-text-muted transition-transform ${
                      isOpen ? 'rotate-180' : ''
                    }`}
                  />
                </Button>
              </CollapsibleTrigger>
            </div>
          </div>
        </CardHeader>

        <CollapsibleContent>
          <CardContent className="pt-0">
            <div className="space-y-0">
              {dayPlan.activities.map((activity, i) => (
                <ActivityCard key={activity.id} activity={activity} index={i} />
              ))}
            </div>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}
