import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useJourneyStore } from "@/stores/journeyStore";
import LoadingScreen from "@/components/LoadingScreen";
import { MapPin, Calendar, Users, Plane } from "lucide-react";

export default function TripWizard() {
  const navigate = useNavigate();
  const { create, pollUntilComplete, creating, jobProgress, error } = useJourneyStore();

  const [form, setForm] = useState({
    destination: "",
    origin: "",
    start_date: "",
    total_days: 5,
    pace: "moderate",
    budget: "moderate",
    adults: 2,
  });

  const [showLoading, setShowLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const result = await create({
        destination: form.destination,
        origin: form.origin || undefined,
        start_date: form.start_date,
        total_days: form.total_days,
        pace: form.pace,
        budget: form.budget,
        travelers: { adults: form.adults },
      });

      if (result.status === "complete") {
        navigate(`/journeys/${result.id}`);
      } else if (result.job_id) {
        setShowLoading(true);
        pollUntilComplete(result.job_id, () => {
          navigate(`/journeys/${result.id}`);
        });
      }
    } catch {
      // error is set in store
    }
  };

  if (showLoading) {
    return <LoadingScreen progress={jobProgress} error={error} />;
  }

  return (
    <div className="max-w-lg mx-auto px-4 py-12">
      <div className="text-center mb-8">
        <Plane className="w-10 h-10 mx-auto mb-3 text-primary" />
        <h1 className="text-2xl font-bold">Plan Your Trip</h1>
        <p className="text-muted-foreground mt-1">We'll assemble the perfect itinerary from our curated plans</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Destination */}
        <div>
          <label className="block text-sm font-medium mb-1.5">Destination</label>
          <div className="relative">
            <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              required
              type="text"
              placeholder="Japan, Italy, Southeast Asia..."
              value={form.destination}
              onChange={(e) => setForm({ ...form, destination: e.target.value })}
              className="w-full pl-10 pr-4 py-2.5 rounded-lg border bg-background"
            />
          </div>
        </div>

        {/* Dates row */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1.5">Start Date</label>
            <div className="relative">
              <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                required
                type="date"
                value={form.start_date}
                onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                className="w-full pl-10 pr-4 py-2.5 rounded-lg border bg-background"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">Days</label>
            <input
              type="number"
              min={1}
              max={30}
              value={form.total_days}
              onChange={(e) => setForm({ ...form, total_days: Number(e.target.value) })}
              className="w-full px-4 py-2.5 rounded-lg border bg-background"
            />
          </div>
        </div>

        {/* Pace */}
        <div>
          <label className="block text-sm font-medium mb-1.5">Pace</label>
          <div className="grid grid-cols-3 gap-2">
            {["relaxed", "moderate", "packed"].map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setForm({ ...form, pace: p })}
                className={`py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  form.pace === p ? "bg-primary text-primary-foreground" : "border hover:bg-muted"
                }`}
              >
                {p.charAt(0).toUpperCase() + p.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Budget */}
        <div>
          <label className="block text-sm font-medium mb-1.5">Budget</label>
          <div className="grid grid-cols-3 gap-2">
            {["budget", "moderate", "luxury"].map((b) => (
              <button
                key={b}
                type="button"
                onClick={() => setForm({ ...form, budget: b })}
                className={`py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  form.budget === b ? "bg-primary text-primary-foreground" : "border hover:bg-muted"
                }`}
              >
                {b.charAt(0).toUpperCase() + b.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Travelers */}
        <div>
          <label className="block text-sm font-medium mb-1.5">Travelers</label>
          <div className="relative">
            <Users className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="number"
              min={1}
              max={20}
              value={form.adults}
              onChange={(e) => setForm({ ...form, adults: Number(e.target.value) })}
              className="w-full pl-10 pr-4 py-2.5 rounded-lg border bg-background"
            />
          </div>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={creating}
          className="w-full py-3 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {creating ? "Creating..." : "Plan My Trip"}
        </button>
      </form>
    </div>
  );
}
