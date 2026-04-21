import { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { Search, MapPin, Globe } from "lucide-react";
import { useCatalogStore } from "@/stores/catalogStore";

const REGIONS = [
  "All",
  "East Asia",
  "Southeast Asia",
  "South Asia",
  "Western Europe",
  "Eastern Europe",
  "North America",
  "South America",
  "Middle East",
  "Africa",
  "Oceania",
];

const CITY_GRADIENTS = [
  "from-indigo-500 to-purple-600",
  "from-rose-500 to-orange-500",
  "from-emerald-500 to-teal-600",
  "from-amber-500 to-red-500",
  "from-cyan-500 to-blue-600",
  "from-fuchsia-500 to-pink-600",
  "from-lime-500 to-green-600",
  "from-violet-500 to-indigo-600",
];

function getGradient(index: number) {
  return CITY_GRADIENTS[index % CITY_GRADIENTS.length];
}

export default function CityCatalog() {
  const { cities, loading, fetchCities } = useCatalogStore();
  const [search, setSearch] = useState("");
  const [region, setRegion] = useState("All");

  useEffect(() => {
    fetchCities(region === "All" ? undefined : { region });
  }, [fetchCities, region]);

  const filtered = useMemo(() => {
    if (!search.trim()) return cities;
    const q = search.toLowerCase();
    return cities.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.country.toLowerCase().includes(q)
    );
  }, [cities, search]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-[#0f1219]">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white font-display">
            City Catalog
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Browse pre-planned itineraries for cities around the world
          </p>
        </div>

        {/* Search */}
        <div className="relative mb-6">
          <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search cities or countries..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-gray-200 bg-white py-3 pl-10 pr-4 text-sm text-gray-900 placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-gray-700 dark:bg-gray-800 dark:text-white dark:placeholder-gray-500"
          />
        </div>

        {/* Region filters */}
        <div className="mb-8 flex flex-wrap gap-2">
          {REGIONS.map((r) => (
            <button
              key={r}
              onClick={() => setRegion(r)}
              className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                region === r
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "bg-white text-gray-700 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
              }`}
            >
              {r}
            </button>
          ))}
        </div>

        {/* Loading skeleton */}
        {loading && (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="h-48 animate-pulse rounded-xl bg-gray-200 dark:bg-gray-800"
              />
            ))}
          </div>
        )}

        {/* Empty state */}
        {!loading && filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <Globe className="mb-4 h-16 w-16 text-gray-300 dark:text-gray-600" />
            <h2 className="text-lg font-semibold text-gray-700 dark:text-gray-300">
              No cities found
            </h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {search
                ? "Try a different search term or region filter."
                : "No cities available in this region yet."}
            </p>
          </div>
        )}

        {/* City grid */}
        {!loading && filtered.length > 0 && (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 animate-stagger-in">
            {filtered.map((city, i) => (
              <Link
                key={city.id}
                to={`/cities/${city.id}`}
                className={`stagger-${Math.min(i + 1, 8)} group relative overflow-hidden rounded-xl shadow-md transition-transform hover:-translate-y-1 hover:shadow-lg`}
              >
                <div
                  className={`h-48 bg-gradient-to-br ${getGradient(i)} p-6 flex flex-col justify-end`}
                >
                  <div className="absolute inset-0 bg-black/10 transition-opacity group-hover:bg-black/20" />
                  <div className="relative z-10">
                    <h3 className="text-xl font-bold text-white font-display">
                      {city.name}
                    </h3>
                    <div className="mt-1 flex items-center gap-2 text-sm text-white/80">
                      <MapPin className="h-3.5 w-3.5" />
                      <span>{city.country}</span>
                    </div>
                    {city.region && (
                      <span className="mt-2 inline-block rounded-full bg-white/20 px-2.5 py-0.5 text-xs font-medium text-white">
                        {city.region}
                      </span>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
