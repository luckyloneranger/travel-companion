import { useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { useJourneyStore } from "@/stores/journeyStore";
import { ArrowLeft, Clock, ArrowRight, Calendar } from "lucide-react";

export default function JourneyDashboard() {
  const { journeyId } = useParams<{ journeyId: string }>();
  const { currentJourney, loading, fetchJourney } = useJourneyStore();

  useEffect(() => {
    if (journeyId) fetchJourney(journeyId);
  }, [journeyId, fetchJourney]);

  if (loading || !currentJourney) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="h-8 w-64 bg-muted animate-pulse rounded mb-6" />
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-32 bg-muted animate-pulse rounded-xl mb-4" />
        ))}
      </div>
    );
  }

  const journey = currentJourney;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <Link to="/journeys" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-6">
        <ArrowLeft className="w-4 h-4" /> My Trips
      </Link>

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold">{journey.destination}</h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1">
          <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" />{journey.start_date}</span>
          <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5" />{journey.total_days} days</span>
          <span className="capitalize">{journey.pace} &middot; {journey.budget}</span>
        </div>
      </div>

      {/* City sequence */}
      <div className="space-y-3">
        {journey.city_sequence?.map((city, i) => (
          <div key={i}>
            {/* City card */}
            <div className="p-5 rounded-xl border bg-card">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-lg">{city.city_name}</h3>
                  <div className="flex items-center gap-3 text-sm text-muted-foreground mt-1">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      {city.day_count} days
                    </span>
                    <span>Days {city.start_day}&ndash;{city.start_day + city.day_count - 1}</span>
                  </div>
                </div>
                {city.variant_id && (
                  <Link
                    to={`/cities/${city.city_id}/plans/${city.variant_id}`}
                    className="px-4 py-2 rounded-lg bg-primary/10 text-primary text-sm font-medium hover:bg-primary/20 transition-colors"
                  >
                    View Plan
                  </Link>
                )}
              </div>
            </div>

            {/* Transport leg */}
            {journey.transport_legs && i < journey.transport_legs.length && (
              <div className="flex items-center justify-center py-2 text-sm text-muted-foreground">
                <div className="flex items-center gap-2">
                  <ArrowRight className="w-4 h-4" />
                  <span>{journey.transport_legs[i].mode}</span>
                  {journey.transport_legs[i].fare && (
                    <span>&middot; {journey.transport_legs[i].fare}</span>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Cost */}
      {journey.cost_breakdown && (
        <div className="mt-8 p-5 rounded-xl border bg-card">
          <h3 className="font-semibold mb-3">Trip Cost</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            {Object.entries(journey.cost_breakdown)
              .filter(([key]) => key !== "per_day" && key !== "total")
              .map(([key, value]) => (
                <div key={key}>
                  <div className="text-muted-foreground capitalize">{key}</div>
                  <div className="font-medium">${(value as number)?.toFixed(0) || 0}</div>
                </div>
              ))}
          </div>
          <div className="mt-3 pt-3 border-t flex justify-between">
            <span className="font-medium">Total</span>
            <span className="font-bold text-lg">${journey.cost_breakdown.total?.toFixed(0) || 0}</span>
          </div>
        </div>
      )}
    </div>
  );
}
