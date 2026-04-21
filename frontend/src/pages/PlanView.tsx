import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useCatalogStore } from "@/stores/catalogStore";
import { type ActivityResponse } from "@/lib/api";
import { ArrowLeft, Clock, Star, Utensils, ChevronLeft, ChevronRight } from "lucide-react";

export default function PlanView() {
  const { cityId, variantId } = useParams<{ cityId: string; variantId: string }>();
  const { selectedVariant, loading, fetchVariant } = useCatalogStore();
  const [activeDay, setActiveDay] = useState(1);

  useEffect(() => {
    if (cityId && variantId) fetchVariant(cityId, variantId);
  }, [cityId, variantId, fetchVariant]);

  if (loading || !selectedVariant) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="h-8 w-48 bg-muted animate-pulse rounded mb-6" />
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-24 bg-muted animate-pulse rounded-xl mb-4" />
        ))}
      </div>
    );
  }

  const variant = selectedVariant;
  const currentDay = variant.day_plans.find((d) => d.day_number === activeDay);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Back */}
      <Link to={`/cities/${cityId}`} className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-6">
        <ArrowLeft className="w-4 h-4" /> Back to city
      </Link>

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold">{variant.city_name || "City Plan"}</h1>
        <p className="text-muted-foreground">
          {variant.day_count} days · {variant.pace} pace · {variant.budget} budget
          {variant.quality_score && ` · Score: ${variant.quality_score}`}
        </p>
      </div>

      {/* Day tabs */}
      <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-2">
        <button
          onClick={() => setActiveDay(Math.max(1, activeDay - 1))}
          disabled={activeDay === 1}
          className="p-1.5 rounded-lg hover:bg-muted disabled:opacity-30"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        {variant.day_plans.map((day) => (
          <button
            key={day.day_number}
            onClick={() => setActiveDay(day.day_number)}
            className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
              activeDay === day.day_number
                ? "bg-primary text-primary-foreground"
                : "bg-muted hover:bg-muted/80"
            }`}
          >
            Day {day.day_number}
          </button>
        ))}
        <button
          onClick={() => setActiveDay(Math.min(variant.day_count, activeDay + 1))}
          disabled={activeDay === variant.day_count}
          className="p-1.5 rounded-lg hover:bg-muted disabled:opacity-30"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Day content */}
      {currentDay && (
        <div>
          <div className="mb-4">
            <h2 className="text-lg font-semibold">{currentDay.theme}</h2>
            {currentDay.theme_description && (
              <p className="text-sm text-muted-foreground">{currentDay.theme_description}</p>
            )}
          </div>

          {/* Timeline */}
          <div className="space-y-4">
            {currentDay.activities.map((activity, i) => (
              <ActivityCard key={activity.id} activity={activity} index={i} />
            ))}
          </div>
        </div>
      )}

      {/* Cost breakdown */}
      {variant.cost_breakdown && (
        <div className="mt-10 p-5 rounded-xl border bg-card">
          <h3 className="font-semibold mb-3">Cost Breakdown</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            {Object.entries(variant.cost_breakdown)
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
            <span className="font-bold text-lg">
              ${((variant.cost_breakdown as Record<string, number>).total)?.toFixed(0) || 0}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function ActivityCard({ activity, index }: { activity: ActivityResponse; index: number }) {
  return (
    <div className={`flex gap-4 p-4 rounded-xl border bg-card animate-stagger-in stagger-${Math.min(index + 1, 8)}`}>
      {/* Photo */}
      {activity.place_photo_url && (
        <img
          src={activity.place_photo_url}
          alt={activity.place_name}
          className="w-20 h-20 rounded-lg object-cover flex-shrink-0"
        />
      )}
      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-medium">{activity.place_name}</h3>
          <span className="text-xs text-muted-foreground whitespace-nowrap">
            {activity.start_time?.slice(0, 5)} – {activity.end_time?.slice(0, 5)}
          </span>
        </div>
        {activity.description && (
          <p className="text-sm text-muted-foreground mt-0.5 line-clamp-2">{activity.description}</p>
        )}
        <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {activity.duration_minutes}min
          </span>
          {activity.place_rating && (
            <span className="flex items-center gap-1">
              <Star className="w-3 h-3 text-amber-500" />
              {activity.place_rating.toFixed(1)}
            </span>
          )}
          {activity.is_meal && (
            <span className="flex items-center gap-1">
              <Utensils className="w-3 h-3" />
              {activity.meal_type}
            </span>
          )}
          {activity.estimated_cost_usd != null && activity.estimated_cost_usd > 0 && (
            <span>${activity.estimated_cost_usd.toFixed(0)}</span>
          )}
          <span className="px-1.5 py-0.5 rounded-full bg-muted text-[10px]">{activity.category}</span>
        </div>
      </div>
    </div>
  );
}
