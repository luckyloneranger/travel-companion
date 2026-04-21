import { useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Clock, DollarSign, Star, MapPin, Gauge } from "lucide-react";
import { useCatalogStore } from "@/stores/catalogStore";
import { photoUrl } from "@/lib/api";

export default function CityDetail() {
  const { cityId } = useParams<{ cityId: string }>();
  const { selectedCity: city, loading, fetchCity, clearSelection } = useCatalogStore();

  useEffect(() => {
    if (cityId) fetchCity(cityId);
    return () => clearSelection();
  }, [cityId, fetchCity, clearSelection]);

  if (loading || !city) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-[#0f1219]">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="mb-6 h-5 w-24 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
          <div className="mb-8 h-48 animate-pulse rounded-xl bg-gray-200 dark:bg-gray-800" />
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-64 animate-pulse rounded-xl bg-gray-200 dark:bg-gray-800" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-[#0f1219]">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Back link */}
        <Link
          to="/cities"
          className="mb-6 inline-flex items-center gap-1.5 text-sm font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
        >
          <ArrowLeft className="h-4 w-4" />
          All Cities
        </Link>

        {/* Hero */}
        <div className="mb-10 overflow-hidden rounded-2xl bg-gradient-to-br from-indigo-600 to-purple-700 p-8 text-white shadow-lg sm:p-10">
          <h1 className="text-4xl font-bold tracking-tight font-display">{city.name}</h1>
          <p className="mt-1 text-lg text-white/80">{city.country}</p>
          <div className="mt-4 flex flex-wrap gap-4 text-sm text-white/70">
            {city.timezone && (
              <span className="flex items-center gap-1.5">
                <Clock className="h-4 w-4" />
                {city.timezone}
              </span>
            )}
            {city.currency && (
              <span className="flex items-center gap-1.5">
                <DollarSign className="h-4 w-4" />
                {city.currency}
              </span>
            )}
            {city.region && (
              <span className="rounded-full bg-white/20 px-3 py-0.5 text-xs font-medium">
                {city.region}
              </span>
            )}
          </div>
        </div>

        {/* Landmarks */}
        {city.landmarks.length > 0 && (
          <section className="mb-12">
            <h2 className="mb-6 text-2xl font-bold text-gray-900 dark:text-white font-display">
              Landmarks
            </h2>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 animate-stagger-in">
              {city.landmarks.map((lm, i) => (
                <div
                  key={lm.id}
                  className={`stagger-${Math.min(i + 1, 8)} overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800`}
                >
                  {lm.photo_references.length > 0 && (
                    <img
                      src={photoUrl(lm.photo_references[0], 600)}
                      alt={lm.name}
                      className="h-40 w-full object-cover"
                      loading="lazy"
                    />
                  )}
                  <div className="p-4">
                    <h3 className="font-semibold text-gray-900 dark:text-white">{lm.name}</h3>
                    {lm.editorial_summary && (
                      <p className="mt-1 text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                        {lm.editorial_summary}
                      </p>
                    )}
                    <div className="mt-3 flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                      {lm.rating != null && (
                        <span className="flex items-center gap-1">
                          <Star className="h-3.5 w-3.5 text-amber-500" />
                          {lm.rating.toFixed(1)}
                        </span>
                      )}
                      {lm.address && (
                        <span className="flex items-center gap-1 truncate">
                          <MapPin className="h-3.5 w-3.5" />
                          {lm.address}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Available Plans */}
        {city.available_variants.length > 0 && (
          <section>
            <h2 className="mb-6 text-2xl font-bold text-gray-900 dark:text-white font-display">
              Available Plans
            </h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 animate-stagger-in">
              {city.available_variants.map((v, i) => (
                <Link
                  key={v.id}
                  to={`/cities/${city.id}/plans/${v.id}`}
                  className={`stagger-${Math.min(i + 1, 8)} rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-colors hover:border-indigo-300 hover:shadow-md dark:border-gray-700 dark:bg-gray-800 dark:hover:border-indigo-600`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold capitalize text-gray-900 dark:text-white">
                      {v.pace} / {v.budget}
                    </span>
                    {v.quality_score != null && (
                      <span className="flex items-center gap-1 rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-semibold text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300">
                        <Gauge className="h-3.5 w-3.5" />
                        {v.quality_score}
                      </span>
                    )}
                  </div>
                  <div className="mt-3 flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                    <span>{v.day_count} {v.day_count === 1 ? "day" : "days"}</span>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      v.status === "ready"
                        ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                        : "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                    }`}>
                      {v.status}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
