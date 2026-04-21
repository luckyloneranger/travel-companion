import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getSharedJourney, type JourneyResponse } from "@/lib/api";
import { Calendar, Clock } from "lucide-react";

export default function SharedJourney() {
  const { token } = useParams<{ token: string }>();
  const [journey, setJourney] = useState<JourneyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    getSharedJourney(token)
      .then(setJourney)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-8 h-8 border-4 border-muted border-t-primary rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !journey) {
    return (
      <div className="text-center py-20">
        <h2 className="text-lg font-medium">Journey not found</h2>
        <p className="text-muted-foreground mt-2">This shared link may have expired</p>
      </div>
    );
  }

  const cities = (journey.city_sequence ?? []) as unknown as { city_name: string; day_count: number }[];
  const costs = journey.cost_breakdown as Record<string, number> | null;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-8">
        <div className="text-sm text-muted-foreground mb-2">Shared Trip</div>
        <h1 className="text-2xl font-bold">{journey.destination}</h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1">
          <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" />{journey.start_date}</span>
          <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5" />{journey.total_days} days</span>
        </div>
      </div>

      <div className="space-y-3">
        {cities.map((city, i) => (
          <div key={i} className="p-5 rounded-xl border bg-card">
            <h3 className="font-semibold">{city.city_name}</h3>
            <p className="text-sm text-muted-foreground">{city.day_count} days</p>
          </div>
        ))}
      </div>

      {costs && (
        <div className="mt-8 p-5 rounded-xl border bg-card">
          <h3 className="font-semibold mb-2">Estimated Cost</h3>
          <p className="text-2xl font-bold">${costs.total?.toFixed(0) || 0}</p>
        </div>
      )}
    </div>
  );
}
