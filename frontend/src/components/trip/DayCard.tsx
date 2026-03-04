import { Suspense, useState } from 'react';
import { Calendar, MapPin, ChevronDown, Map, Lightbulb, Loader2, Cloud, Sun, CloudRain, Snowflake, Thermometer, DollarSign } from 'lucide-react';
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
import { DayMap } from '@/components/maps';
import { useUIStore } from '@/stores/uiStore';
import { useTripStore } from '@/stores/tripStore';
import type { DayPlan } from '@/types';

interface DayCardProps {
  dayPlan: DayPlan;
}

export function DayCard({ dayPlan }: DayCardProps) {
  const [isOpen, setIsOpen] = useState(true);
  const { dayMapVisible, toggleDayMap } = useUIStore();
  const { tips, tipsLoading, fetchTips } = useTripStore();

  const hasTipsForDay = dayPlan.activities.some((a) => tips[a.place.place_id]);

  const WeatherIcon = dayPlan.weather
    ? dayPlan.weather.condition.toLowerCase().includes('rain')
      ? CloudRain
      : dayPlan.weather.condition.toLowerCase().includes('snow')
        ? Snowflake
        : dayPlan.weather.temperature_high_c >= 30
          ? Thermometer
          : dayPlan.weather.condition.toLowerCase().includes('cloud')
            ? Cloud
            : Sun
    : null;

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
                <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                  <span className="flex items-center gap-1 text-xs text-text-muted">
                    <Calendar className="h-3 w-3" />
                    {formatDate(dayPlan.date)}
                  </span>
                  <Badge variant="secondary" className="text-xs">
                    <MapPin className="h-2.5 w-2.5 mr-0.5" />
                    {dayPlan.city_name}
                  </Badge>
                  {dayPlan.weather && WeatherIcon && (
                    <Badge variant="outline" className="text-xs flex items-center gap-1">
                      <WeatherIcon className="h-3 w-3" />
                      {dayPlan.weather.temperature_low_c.toFixed(0)}–{dayPlan.weather.temperature_high_c.toFixed(0)}°C
                      {dayPlan.weather.precipitation_chance_percent > 0 && (
                        <span className="text-text-muted">
                          · {dayPlan.weather.precipitation_chance_percent}% rain
                        </span>
                      )}
                    </Badge>
                  )}
                  {dayPlan.daily_cost_usd != null && dayPlan.daily_cost_usd > 0 && (
                    <Badge variant="outline" className="text-xs flex items-center gap-1">
                      <DollarSign className="h-3 w-3" />
                      ~${dayPlan.daily_cost_usd.toFixed(0)}/day
                    </Badge>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => fetchTips(dayPlan.activities)}
                disabled={tipsLoading || hasTipsForDay}
                aria-label="Get tips"
                title={hasTipsForDay ? 'Tips loaded' : 'Get insider tips'}
              >
                {tipsLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin text-text-muted" />
                ) : (
                  <Lightbulb className={`h-4 w-4 ${hasTipsForDay ? 'text-amber-500' : 'text-text-muted'}`} />
                )}
              </Button>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => toggleDayMap(dayPlan.day_number)}
                aria-label={dayMapVisible[dayPlan.day_number] ? 'Hide map' : 'Show map'}
                title={dayMapVisible[dayPlan.day_number] ? 'Hide map' : 'Show map'}
              >
                <Map className={`h-4 w-4 ${dayMapVisible[dayPlan.day_number] ? 'text-primary-600' : 'text-text-muted'}`} />
              </Button>
              <span className="text-xs text-text-muted">
                {dayPlan.activities.length}{' '}
                {dayPlan.activities.length === 1 ? 'activity' : 'activities'}
              </span>
              <CollapsibleTrigger asChild>
                <Button variant="ghost" size="icon-sm" aria-label={isOpen ? `Collapse day ${dayPlan.day_number}` : `Expand day ${dayPlan.day_number}`}>
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
            {dayMapVisible[dayPlan.day_number] && (
              <Suspense fallback={<div className="h-64 rounded-lg bg-surface-muted animate-pulse mb-4" />}>
                <div className="h-64 rounded-lg overflow-hidden border border-border-default mb-4">
                  <DayMap dayPlan={dayPlan} />
                </div>
              </Suspense>
            )}
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
