import { Routes, Route, Navigate } from "react-router-dom";
import { Header } from "@/components/layout/Header";
import CityCatalog from "@/pages/CityCatalog";
import CityDetail from "@/pages/CityDetail";
import PlanView from "@/pages/PlanView";
import TripWizard from "@/pages/TripWizard";
import JourneyDashboard from "@/pages/JourneyDashboard";
import SavedJourneys from "@/pages/SavedJourneys";
import SharedJourney from "@/pages/SharedJourney";
import { ToastContainer } from "@/components/ui/toast";

export default function App() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Header />
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/cities" replace />} />
          <Route path="/cities" element={<CityCatalog />} />
          <Route path="/cities/:cityId" element={<CityDetail />} />
          <Route path="/cities/:cityId/plans/:variantId" element={<PlanView />} />
          <Route path="/plan" element={<TripWizard />} />
          <Route path="/journeys" element={<SavedJourneys />} />
          <Route path="/journeys/:journeyId" element={<JourneyDashboard />} />
          <Route path="/shared/:token" element={<SharedJourney />} />
        </Routes>
      </main>
      <ToastContainer />
    </div>
  );
}
