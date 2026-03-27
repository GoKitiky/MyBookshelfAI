import { Navigate, Route, Routes } from "react-router-dom";
import { DemoBanner } from "./components/DemoBanner";
import { Nav } from "./components/Nav";
import { ToastProvider } from "./components/Toast";
import { LibraryPage } from "./pages/LibraryPage";
import { ProfilePage } from "./pages/ProfilePage";
import { RecommendationsPage } from "./pages/RecommendationsPage";
import { SettingsPage } from "./pages/SettingsPage";

export function App() {
  return (
    <ToastProvider>
      <DemoBanner />
      <div className="app-layout">
        <Nav />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<LibraryPage />} />
            <Route
              path="/library"
              element={<Navigate to="/" replace />}
            />
            <Route
              path="/recommendations"
              element={<RecommendationsPage />}
            />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </ToastProvider>
  );
}
