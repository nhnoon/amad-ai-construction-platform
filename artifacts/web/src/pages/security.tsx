import { KeyRound, Laptop, ShieldAlert } from "lucide-react";
import { useListSessions } from "@workspace/api-client-react";
import type { SessionOut } from "@workspace/api-client-react";
import { WorkspaceLayout } from "@/components/workspace-layout";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "../context/AuthContext";
import { apiErrorDetail } from "../lib/apiErrors";

function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "Never";
  return new Date(iso).toLocaleString();
}

function SessionRow({ session }: { session: SessionOut }) {
  return (
    <div className="panel panel-body flex items-start justify-between gap-4">
      <div className="flex items-start gap-3 min-w-0">
        <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
          <Laptop className="w-4 h-4 text-primary" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-foreground truncate">
            {session.device || "Unknown device"}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Signed in {formatDateTime(session.created_at)}
          </p>
          <p className="text-xs text-muted-foreground">
            Last used {formatDateTime(session.last_used_at)}
          </p>
          <p className="text-xs text-muted-foreground">
            Expires {formatDateTime(session.expires_at)}
          </p>
        </div>
      </div>
      {session.remember_me && (
        <Badge variant="secondary" className="shrink-0">
          Remembered
        </Badge>
      )}
    </div>
  );
}

export default function Security() {
  const { toast } = useToast();
  const { logoutAllSessions } = useAuth();
  const { data: sessions, isLoading, isError, refetch } = useListSessions();

  const handleLogoutAll = async () => {
    // A compact, dependency-free confirmation — this revokes every
    // session for this account, including the one currently viewing this
    // page, so it's worth a deliberate second step before firing it.
    if (!window.confirm("Sign out of all devices? You'll need to log in again here too.")) {
      return;
    }
    try {
      await logoutAllSessions();
      // logoutAllSessions() already clears the local session; the app's
      // route guards (ProtectedRoute in App.tsx) pick up the now-null
      // user and redirect to /login on their own.
    } catch (err) {
      toast({
        title: "Could not sign out of all devices",
        description: apiErrorDetail(err),
        variant: "destructive",
      });
    }
  };

  return (
    <WorkspaceLayout
      title="Security"
      subtitle="Manage the devices and sessions currently signed in to your account"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Security" }]}
      toolbar={
        sessions && sessions.length > 0 ? (
          <Button variant="destructive" size="sm" onClick={handleLogoutAll}>
            <ShieldAlert className="w-4 h-4 mr-1.5" />
            Sign out of all devices
          </Button>
        ) : undefined
      }
    >
      {isLoading && (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      )}

      {isError && (
        <ErrorState
          title="Failed to load sessions"
          action={
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              Retry
            </Button>
          }
        />
      )}

      {!isLoading && !isError && sessions && sessions.length === 0 && (
        <EmptyState
          icon={KeyRound}
          title="No active sessions"
          description="Sign in again to start a new session."
        />
      )}

      {!isLoading && !isError && sessions && sessions.length > 0 && (
        <div className="space-y-3">
          {/* Sessions are not individually revocable in this release — the
              backend intentionally exposes no per-session revoke endpoint
              yet (RC1 Phase 1 Sprint 1), and this UI does not fake one.
              "Sign out of all devices" above is the only bulk action; a
              per-device "Sign out" button here would need to be the
              current device's own logout, which the sidebar already
              provides — no safe way exists yet to tell which row IS the
              current device (see Sprint 2 report §7), so no such badge or
              button is rendered here either. */}
          {sessions.map((session) => (
            <SessionRow key={session.id} session={session} />
          ))}
        </div>
      )}
    </WorkspaceLayout>
  );
}
