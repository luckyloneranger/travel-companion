import { useEffect } from "react";
import { Link } from "react-router-dom";
import { useJourneyStore } from "@/stores/journeyStore";
import { Calendar, Trash2, Plane } from "lucide-react";

export default function SavedJourneys() {
  const { journeys, loading, fetchJourneys, removeJourney } = useJourneyStore();

  useEffect(() => {
    fetchJourneys();
  }, [fetchJourneys]);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold">My Trips</h1>
        <Link to="/plan" className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium">
          Plan New Trip
        </Link>
      </div>

      {loading ? (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-24 bg-muted animate-pulse rounded-xl" />
          ))}
        </div>
      ) : journeys.length === 0 ? (
        <div className="text-center py-20">
          <Plane className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
          <h3 className="text-lg font-medium mb-2">No trips yet</h3>
          <p className="text-muted-foreground mb-4">Plan your first adventure</p>
          <Link to="/plan" className="px-6 py-2.5 rounded-lg bg-primary text-primary-foreground font-medium">
            Plan a Trip
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {journeys.map((j, i) => (
            <div key={j.id} className={`flex items-center gap-4 p-5 rounded-xl border bg-card animate-stagger-in stagger-${Math.min(i + 1, 8)}`}>
              <div className="flex-1 min-w-0">
                <Link to={`/journeys/${j.id}`} className="font-semibold hover:text-primary transition-colors">
                  {j.destination}
                </Link>
                <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1">
                  <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" />{j.start_date}</span>
                  <span>{j.total_days} days</span>
                  <span>{j.city_count} cities</span>
                  <span className={`px-1.5 py-0.5 rounded text-xs ${j.status === "complete" ? "bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400" : "bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400"}`}>
                    {j.status}
                  </span>
                </div>
              </div>
              <button
                onClick={() => { if (confirm("Delete this trip?")) removeJourney(j.id); }}
                className="p-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-muted-foreground hover:text-red-500 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
