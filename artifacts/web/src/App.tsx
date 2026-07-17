import { useEffect, ComponentType, lazy, Suspense } from "react";
import { Switch, Route, Router as WouterRouter, useLocation } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/not-found";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { Layout } from "./components/layout";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { setAuthTokenGetter } from "@workspace/api-client-react";
import { getToken } from "./lib/auth";

import Login from "./pages/login";

// Route-level code splitting — each page (and everything it imports) only
// ships to the browser once its route is actually visited, instead of every
// page shipping in the initial bundle regardless of role or entry route.
const Dashboard = lazy(() => import("./pages/dashboard"));
const Operations = lazy(() => import("./pages/operations"));
const Documents = lazy(() => import("./pages/documents/index"));
const Projects = lazy(() => import("./pages/projects"));
const ProjectDetail = lazy(() => import("./pages/project-detail"));
const Procurement = lazy(() => import("./pages/procurement"));
const Suppliers = lazy(() => import("./pages/suppliers"));
const SiteReports = lazy(() => import("./pages/site-reports"));
const SiteReportDetail = lazy(() => import("./pages/site-report-detail"));
const Safety = lazy(() => import("./pages/safety"));
const Meetings = lazy(() => import("./pages/meetings"));
const MeetingDetail = lazy(() => import("./pages/meeting-detail"));
const RFIs = lazy(() => import("./pages/rfis"));
const ChangeOrders = lazy(() => import("./pages/change-orders"));
const Claims = lazy(() => import("./pages/claims"));
const AdminUsers = lazy(() => import("./pages/admin-users"));
const AdminOrganization = lazy(() => import("./pages/admin-organization"));
const Copilot = lazy(() => import("./pages/copilot"));
const Alerts = lazy(() => import("./pages/alerts"));
const Reports = lazy(() => import("./pages/reports"));
const AICenter = lazy(() => import("./pages/ai-center"));

import "./lib/i18n";

const queryClient = new QueryClient();

setAuthTokenGetter(() => getToken());

function RouteFallback() {
  return (
    <div className="min-h-[50vh] flex items-center justify-center">
      <div className="flex items-center gap-3">
        <div className="w-5 h-5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
        <span className="text-sm text-muted-foreground">Loading…</span>
      </div>
    </div>
  );
}

function ProtectedRoute({ component: Component }: { component: ComponentType<unknown> }) {
  const { user, isLoading } = useAuth();
  const [location, setLocation] = useLocation();

  useEffect(() => {
    if (!isLoading && !user) {
      setLocation("/login");
    }
  }, [isLoading, user, setLocation]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background text-foreground">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          <span className="text-sm text-muted-foreground">Loading…</span>
        </div>
      </div>
    );
  }

  if (!user) return null;

  return (
    <Layout>
      {/* Keyed by route so a crash on one page doesn't stick around after
          navigating away — sidebar/nav (outside this boundary) stay usable
          either way. */}
      <ErrorBoundary key={location} fullPage>
        <Suspense fallback={<RouteFallback />}>
          <Component />
        </Suspense>
      </ErrorBoundary>
    </Layout>
  );
}

function AdminRoute({ component: Component }: { component: ComponentType<unknown> }) {
  const { user, isLoading } = useAuth();
  const [location, setLocation] = useLocation();

  useEffect(() => {
    if (!isLoading && !user) {
      setLocation("/login");
    } else if (!isLoading && user && user.role !== "admin") {
      setLocation("/");
    }
  }, [isLoading, user, setLocation]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background text-foreground">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          <span className="text-sm text-muted-foreground">Loading…</span>
        </div>
      </div>
    );
  }

  if (!user || user.role !== "admin") return null;

  return (
    <Layout>
      <ErrorBoundary key={location} fullPage>
        <Suspense fallback={<RouteFallback />}>
          <Component />
        </Suspense>
      </ErrorBoundary>
    </Layout>
  );
}

function Router() {
  return (
    <Switch>
      <Route path="/login" component={Login} />
      <Route path="/" component={() => <ProtectedRoute component={Dashboard} />} />
      <Route path="/operations" component={() => <ProtectedRoute component={Operations} />} />
      <Route path="/documents" component={() => <ProtectedRoute component={Documents} />} />
      <Route path="/projects" component={() => <ProtectedRoute component={Projects} />} />
      <Route path="/projects/:id" component={() => <ProtectedRoute component={ProjectDetail} />} />
      <Route path="/procurement" component={() => <ProtectedRoute component={Procurement} />} />
      <Route path="/suppliers" component={() => <ProtectedRoute component={Suppliers} />} />
      <Route path="/site-reports" component={() => <ProtectedRoute component={SiteReports} />} />
      <Route path="/projects/:projectId/site-reports/:reportId" component={() => <ProtectedRoute component={SiteReportDetail} />} />
      <Route path="/safety" component={() => <ProtectedRoute component={Safety} />} />
      <Route path="/meetings" component={() => <ProtectedRoute component={Meetings} />} />
      <Route path="/meetings/:projectId/:meetingId" component={() => <ProtectedRoute component={MeetingDetail} />} />
      <Route path="/rfis" component={() => <ProtectedRoute component={RFIs} />} />
      <Route path="/change-orders" component={() => <ProtectedRoute component={ChangeOrders} />} />
      <Route path="/claims" component={() => <ProtectedRoute component={Claims} />} />
      <Route path="/admin/users" component={() => <AdminRoute component={AdminUsers} />} />
      <Route path="/admin/organization" component={() => <AdminRoute component={AdminOrganization} />} />
      <Route path="/admin" component={() => <AdminRoute component={AdminUsers} />} />
      <Route path="/copilot" component={() => <ProtectedRoute component={Copilot} />} />
      <Route path="/ai-center/:workspace?" component={() => <ProtectedRoute component={AICenter} />} />
      <Route path="/alerts" component={() => <ProtectedRoute component={Alerts} />} />
      <Route path="/reports" component={() => <ProtectedRoute component={Reports} />} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <ErrorBoundary fullPage>
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>
          <TooltipProvider>
            <AuthProvider>
              <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
                <Router />
              </WouterRouter>
            </AuthProvider>
            <Toaster />
          </TooltipProvider>
        </QueryClientProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
