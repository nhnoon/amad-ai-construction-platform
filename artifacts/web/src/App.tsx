import { useEffect, ComponentType } from "react";
import { Switch, Route, Router as WouterRouter, useLocation } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/not-found";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { Layout } from "./components/layout";
import { setAuthTokenGetter } from "@workspace/api-client-react";
import { getToken } from "./lib/auth";

import Login from "./pages/login";
import Dashboard from "./pages/dashboard";
import Operations from "./pages/operations";
import Documents from "./pages/documents";
import Projects from "./pages/projects";
import ProjectDetail from "./pages/project-detail";
import Procurement from "./pages/procurement";
import Suppliers from "./pages/suppliers";
import SiteReports from "./pages/site-reports";
import SiteReportDetail from "./pages/site-report-detail";
import Safety from "./pages/safety";
import Meetings from "./pages/meetings";
import MeetingDetail from "./pages/meeting-detail";
import RFIs from "./pages/rfis";
import ChangeOrders from "./pages/change-orders";
import Claims from "./pages/claims";
import AdminUsers from "./pages/admin-users";
import AdminOrganization from "./pages/admin-organization";
import Copilot from "./pages/copilot";
import Alerts from "./pages/alerts";
import Reports from "./pages/reports";

import "./lib/i18n";

const queryClient = new QueryClient();

setAuthTokenGetter(() => getToken());

function ProtectedRoute({ component: Component }: { component: ComponentType<unknown> }) {
  const { user, isLoading } = useAuth();
  const [, setLocation] = useLocation();

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
      <Component />
    </Layout>
  );
}

function AdminRoute({ component: Component }: { component: ComponentType<unknown> }) {
  const { user, isLoading } = useAuth();
  const [, setLocation] = useLocation();

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
      <Component />
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
      <Route path="/alerts" component={() => <ProtectedRoute component={Alerts} />} />
      <Route path="/reports" component={() => <ProtectedRoute component={Reports} />} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
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
  );
}

export default App;
