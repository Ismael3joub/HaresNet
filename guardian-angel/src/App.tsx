import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/hooks/useAuth";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import Dashboard from "./pages/Dashboard";
import DevicesPage from "./pages/DevicesPage";
import WiFiPage from "./pages/WiFiPage";
import FirewallPage from "./pages/FirewallPage";
import SchedulesPage from "./pages/SchedulesPage";
import SystemPage from "./pages/SystemPage";
import SpeedTestPage from "./pages/SpeedTestPage";
import NetworkSettings from "./pages/NetworkSettings";
import SettingsPage from "./pages/SettingsPage";
import DNSFilterPage from "./pages/DNSFilterPage";
import LoginPage from "./pages/LoginPage";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const App = () => (
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/devices" element={<ProtectedRoute><DevicesPage /></ProtectedRoute>} />
            <Route path="/wifi" element={<ProtectedRoute><WiFiPage /></ProtectedRoute>} />
            <Route path="/schedules" element={<ProtectedRoute><SchedulesPage /></ProtectedRoute>} />
            <Route path="/system/speedtest" element={<ProtectedRoute><SpeedTestPage /></ProtectedRoute>} />
            <Route path="/system" element={<ProtectedRoute><SystemPage /></ProtectedRoute>} />
            <Route path="/network" element={<ProtectedRoute><NetworkSettings /></ProtectedRoute>} />
            <Route path="/dns-filter" element={<ProtectedRoute><DNSFilterPage /></ProtectedRoute>} />
            <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </AuthProvider>
  </QueryClientProvider>
);

export default App;
