import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Header } from '@/components/layout/Header';
import { PageContainer } from '@/components/layout/PageContainer';
import { CompactCityCard } from '@/components/trip/CompactCityCard';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Sparkles, MapPin, Calendar, Navigation, Loader2, Rocket } from 'lucide-react';
import { api } from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
import type { TripResponse } from '@/types';

export function SharedTrip() {
  const { token } = useParams<{ token: string }>();
  const [trip, setTrip] = useState<TripResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    api.getSharedTrip(token)
      .then(setTrip)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load trip'))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <>
        <Header />
        <PageContainer>
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
          </div>
        </PageContainer>
      </>
    );
  }

  if (error || !trip) {
    return (
      <>
        <Header />
        <PageContainer>
          <div className="max-w-md mx-auto text-center py-20">
            <h2 className="text-lg font-semibold text-text-primary">Trip not found</h2>
            <p className="text-sm text-text-muted mt-2">
              This shared trip link may have been revoked or is invalid.
            </p>
          </div>
        </PageContainer>
      </>
    );
  }

  const j = trip.journey;

  return (
    <>
      <Header />
      <PageContainer>
        <div className="space-y-6 animate-fade-in-up">
          {/* Shared trip banner */}
          <div className="bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 rounded-lg px-4 py-3 text-center">
            <p className="text-sm text-primary-700 dark:text-primary-300">
              You're viewing a shared trip
            </p>
          </div>

          {/* Journey info */}
          <div className="space-y-2">
            <h1 className="text-2xl font-display font-bold text-text-primary flex items-center gap-2 min-w-0">
              <Sparkles className="h-6 w-6 text-primary-500 shrink-0" />
              <span className="break-words">{j.theme}</span>
            </h1>
            <p className="text-sm text-text-secondary leading-relaxed break-words">{j.summary}</p>
            <div className="flex flex-wrap gap-4 text-sm text-text-muted">
              <span className="flex items-center gap-1.5">
                <MapPin className="h-4 w-4" /> {j.cities.length} {j.cities.length === 1 ? 'city' : 'cities'}
              </span>
              <span className="flex items-center gap-1.5">
                <Calendar className="h-4 w-4" /> {j.total_days} days
              </span>
              {j.total_distance_km != null && (
                <span className="flex items-center gap-1.5">
                  <Navigation className="h-4 w-4" /> {j.total_distance_km.toFixed(0)} km
                </span>
              )}
              {j.review_score != null && (
                <Badge variant="default" className="bg-green-600 text-white text-xs">
                  Score: {j.review_score}
                </Badge>
              )}
            </div>
          </div>

          {/* Cities with inline day plans */}
          <div className="space-y-3">
            {j.cities.map((city, i) => {
              const departureLeg = j.travel_legs.find((leg) => leg.from_city === city.name);
              const cityDayPlans = trip.day_plans?.filter(
                (dp) => dp.city_name.toLowerCase() === city.name.toLowerCase(),
              );
              return (
                <CompactCityCard
                  key={`city-${i}`}
                  city={city}
                  index={i}
                  departureLeg={departureLeg}
                  dayPlans={cityDayPlans}
                />
              );
            })}
          </div>

          {/* CTA */}
          <div className="text-center pt-4 border-t border-border-default space-y-3">
            <Link to="/">
              <Button className="bg-primary-600 hover:bg-primary-700 text-white">
                <Rocket className="h-4 w-4" />
                Plan your own trip
              </Button>
            </Link>
            {user && (
              <div>
                <Link to="/" className="text-sm text-primary-600 dark:text-primary-400 hover:underline">
                  Go to My Trips
                </Link>
              </div>
            )}
          </div>
        </div>
      </PageContainer>
    </>
  );
}
