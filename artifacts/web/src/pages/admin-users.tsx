import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  UserPlus, Search, RotateCcw, CheckCircle2,
  XCircle, Copy, Check, Users,
} from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { WorkspaceLayout } from "@/components/workspace-layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { getToken } from "../lib/auth";

const API_BASE = "/api/v1";

const ROLES = [
  { value: "admin", label: "Administrator" },
  { value: "executive", label: "Executive" },
  { value: "project_manager", label: "Project Manager" },
  { value: "site_engineer", label: "Site Engineer" },
  { value: "procurement_officer", label: "Procurement Officer" },
  { value: "safety_quality_officer", label: "Safety Officer" },
  { value: "viewer", label: "Viewer" },
];

const ROLE_BADGE: Record<string, string> = {
  admin: "badge-brand",
  executive: "badge-purple",
  project_manager: "badge-info",
  site_engineer: "badge-success",
  procurement_officer: "badge-gold",
  safety_quality_officer: "badge-danger",
  viewer: "badge-neutral",
};

interface User {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  organization_id: number | null;
  created_at: string;
  last_login: string | null;
  must_change_password: boolean;
}

interface CreateUserResponse {
  user: User;
  temporary_password: string;
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as unknown as T;
  return res.json();
}

function RoleBadge({ role }: { role: string }) {
  const label = ROLES.find((r) => r.value === role)?.label ?? role;
  return <span className={`badge ${ROLE_BADGE[role] ?? "badge-neutral"}`}>{label}</span>;
}

function StatusBadge({ active }: { active: boolean }) {
  return active ? (
    <span className="badge badge-success gap-1">
      <CheckCircle2 className="w-3.5 h-3.5" />
      Active
    </span>
  ) : (
    <span className="badge badge-neutral gap-1">
      <XCircle className="w-3.5 h-3.5" />
      Inactive
    </span>
  );
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-SA", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function CreateUserDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    email: "",
    full_name: "",
    role: "site_engineer",
  });
  const [error, setError] = useState("");
  const [created, setCreated] = useState<CreateUserResponse | null>(null);
  const [copied, setCopied] = useState(false);

  const mutation = useMutation({
    mutationFn: (body: typeof form) =>
      apiFetch<CreateUserResponse>("/admin/users", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      setCreated(data);
      setError("");
    },
    onError: (err: Error) => setError(err.message),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    mutation.mutate(form);
  };

  const handleClose = () => {
    setForm({ email: "", full_name: "", role: "site_engineer" });
    setCreated(null);
    setCopied(false);
    onClose();
  };

  const handleCopy = () => {
    if (created) {
      navigator.clipboard.writeText(created.temporary_password);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) handleClose(); }}>
      <DialogContent className="sm:max-w-md">
        {created ? (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                User Created
              </DialogTitle>
              <DialogDescription>
                Temporary password for <strong>{created.user.email}</strong>. They'll be required
                to set their own password the first time they sign in.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <code className="flex-1 px-3 py-2 rounded-md bg-muted text-sm font-mono font-semibold tracking-wider break-all">
                  {created.temporary_password}
                </code>
                <Button
                  size="icon"
                  variant="outline"
                  onClick={handleCopy}
                  className="shrink-0"
                  aria-label={copied ? "Password copied" : "Copy temporary password"}
                >
                  {copied ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">Share this password securely. It won't be shown again.</p>
              <DialogFooter>
                <Button onClick={handleClose}>Done</Button>
              </DialogFooter>
            </div>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-primary" />
                Create New User
              </DialogTitle>
              <DialogDescription>
                Add a team member to the platform. A secure temporary password is generated
                automatically — you'll see it once, to share with them.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4 pt-1">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-foreground">Email *</label>
                <Input
                  type="email"
                  placeholder="user@company.com"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  required
                  autoFocus
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-foreground">Full Name</label>
                <Input
                  placeholder="Ahmed Al-Rashidi"
                  value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-foreground">Role *</label>
                <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ROLES.map((r) => (
                      <SelectItem key={r.value} value={r.value}>
                        {r.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {error && (
                <p className="text-sm text-destructive bg-destructive/5 rounded-md px-3 py-2">{error}</p>
              )}
              <DialogFooter className="pt-2">
                <Button type="button" variant="outline" onClick={handleClose} disabled={mutation.isPending}>
                  Cancel
                </Button>
                <Button type="submit" disabled={mutation.isPending}>
                  {mutation.isPending ? "Creating…" : "Create User"}
                </Button>
              </DialogFooter>
            </form>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

function ResetPasswordDialog({
  user,
  onClose,
}: {
  user: User | null;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const { toast } = useToast();
  const [result, setResult] = useState<{ temporary_password: string } | null>(null);
  const [copied, setCopied] = useState(false);

  const mutation = useMutation({
    mutationFn: () =>
      apiFetch<{ message: string; temporary_password: string }>(
        `/admin/users/${user!.id}/reset-password`,
        { method: "POST" }
      ),
    onSuccess: (data) => {
      setResult(data);
      qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (err: Error) =>
      toast({ title: "Reset failed", description: err.message, variant: "destructive" }),
  });

  const handleCopy = () => {
    if (result) {
      navigator.clipboard.writeText(result.temporary_password);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <Dialog
      open={!!user}
      onOpenChange={(v) => {
        if (!v) {
          setResult(null);
          setCopied(false);
          onClose();
        }
      }}
    >
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <RotateCcw className="w-5 h-5 text-amber-500" />
            Reset Password
          </DialogTitle>
          {!result && (
            <DialogDescription>
              Generate a new temporary password for <strong>{user?.email}</strong>. The old
              password will be immediately invalidated.
            </DialogDescription>
          )}
        </DialogHeader>
        {result ? (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              New temporary password for <strong>{user?.email}</strong>:
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 px-3 py-2 rounded-md bg-muted text-sm font-mono font-semibold tracking-wider">
                {result.temporary_password}
              </code>
              <Button
                size="icon"
                variant="outline"
                onClick={handleCopy}
                className="shrink-0"
                aria-label={copied ? "Password copied" : "Copy temporary password"}
              >
                {copied ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">Share this password securely. It won't be shown again.</p>
            <DialogFooter>
              <Button onClick={() => { setResult(null); onClose(); }}>Done</Button>
            </DialogFooter>
          </div>
        ) : (
          <DialogFooter className="pt-2">
            <Button variant="outline" onClick={onClose} disabled={mutation.isPending}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
            >
              {mutation.isPending ? "Resetting…" : "Reset Password"}
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default function AdminUsers() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { toast } = useToast();
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [createOpen, setCreateOpen] = useState(false);
  const [resetTarget, setResetTarget] = useState<User | null>(null);

  const { data: users = [], isLoading, isError } = useQuery<User[]>({
    queryKey: ["admin-users"],
    queryFn: () => apiFetch<User[]>("/admin/users"),
  });

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      apiFetch<User>(`/admin/users/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active }),
      }),
    onSuccess: (updated) => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      toast({
        title: updated.is_active ? "User activated" : "User deactivated",
        description: updated.email,
        variant: "success",
      });
    },
    onError: (err: Error) =>
      toast({ title: "Update failed", description: err.message, variant: "destructive" }),
  });

  const filtered = users.filter((u) => {
    const matchesSearch =
      !search ||
      u.email.toLowerCase().includes(search.toLowerCase()) ||
      (u.full_name ?? "").toLowerCase().includes(search.toLowerCase());
    const matchesRole = roleFilter === "all" || u.role === roleFilter;
    return matchesSearch && matchesRole;
  });

  const stats = {
    total: users.length,
    active: users.filter((u) => u.is_active).length,
    admins: users.filter((u) => u.role === "admin").length,
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-40" />
          <Skeleton className="h-9 w-28" />
        </div>
        <div className="grid grid-cols-3 gap-4">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-20 rounded-xl" />)}
        </div>
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-8 text-center">
        <XCircle className="w-8 h-8 text-destructive mx-auto mb-2" />
        <p className="text-sm text-destructive font-medium">Failed to load users</p>
      </div>
    );
  }

  return (
    <WorkspaceLayout
        title={t("User Management")}
        subtitle="Manage platform users, roles, and access."
        backLabel="Back to Dashboard"
        backHref="/"
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Administration" },
          { label: "Users" },
        ]}
        toolbar={
          <Button onClick={() => setCreateOpen(true)} className="shrink-0">
            <UserPlus className="w-4 h-4 me-2" />
            New User
          </Button>
        }
      >

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: "Total Users", value: stats.total, color: "text-primary" },
          { label: "Active", value: stats.active, color: "text-emerald-600 dark:text-emerald-400" },
          { label: "Administrators", value: stats.admins, color: "text-amber-600 dark:text-amber-400" },
        ].map((s) => (
          <div key={s.label} className="panel panel-body">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{s.label}</p>
            <p className={`text-3xl font-bold mt-1 ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute start-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search by name or email…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="ps-9"
          />
        </div>
        <Select value={roleFilter} onValueChange={setRoleFilter}>
          <SelectTrigger className="w-full sm:w-48">
            <SelectValue placeholder="All Roles" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Roles</SelectItem>
            {ROLES.map((r) => (
              <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="panel overflow-hidden">
        {filtered.length === 0 ? (
          <EmptyState
            icon={Users}
            title={search || roleFilter !== "all" ? "No users match your filters" : "No users yet"}
            description={search || roleFilter !== "all" ? "Try adjusting your search or role filter." : "Create your first user to get started."}
            action={
              !(search || roleFilter !== "all") && (
                <Button size="sm" onClick={() => setCreateOpen(true)} className="gap-1.5">
                  <UserPlus className="w-3.5 h-3.5" />
                  New User
                </Button>
              )
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th className="hidden md:table-cell">
                    Last Login
                  </th>
                  <th className="hidden lg:table-cell">
                    Created
                  </th>
                  <th className="text-end">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((user) => {
                  const initials = (user.full_name ?? user.email)
                    .split(" ")
                    .map((w) => w[0])
                    .slice(0, 2)
                    .join("")
                    .toUpperCase();
                  return (
                    <tr key={user.id}>
                      <td>
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-xs shrink-0">
                            {initials}
                          </div>
                          <div className="min-w-0">
                            <p className="font-medium text-foreground truncate">
                              {user.full_name || <span className="text-muted-foreground italic">No name</span>}
                            </p>
                            <p className="text-xs text-muted-foreground truncate">{user.email}</p>
                          </div>
                        </div>
                      </td>
                      <td>
                        <RoleBadge role={user.role} />
                      </td>
                      <td>
                        <StatusBadge active={user.is_active} />
                      </td>
                      <td className="text-xs text-muted-foreground hidden md:table-cell">
                        {formatDate(user.last_login)}
                      </td>
                      <td className="text-xs text-muted-foreground hidden lg:table-cell">
                        {formatDate(user.created_at)}
                      </td>
                      <td>
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 px-2 text-xs"
                            onClick={() =>
                              toggleActiveMutation.mutate({
                                id: user.id,
                                is_active: !user.is_active,
                              })
                            }
                            title={user.is_active ? "Deactivate user" : "Activate user"}
                            aria-label={user.is_active ? `Deactivate ${user.email}` : `Activate ${user.email}`}
                          >
                            {user.is_active ? (
                              <XCircle className="w-3.5 h-3.5 text-muted-foreground" />
                            ) : (
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                            )}
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 px-2 text-xs"
                            onClick={() => setResetTarget(user)}
                            title="Reset password"
                            aria-label={`Reset password for ${user.email}`}
                          >
                            <RotateCcw className="w-3.5 h-3.5 text-muted-foreground" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <p className="text-xs text-muted-foreground text-end">
        Showing {filtered.length} of {users.length} user{users.length !== 1 ? "s" : ""}
      </p>

      <CreateUserDialog open={createOpen} onClose={() => setCreateOpen(false)} />
      <ResetPasswordDialog user={resetTarget} onClose={() => setResetTarget(null)} />
    </WorkspaceLayout>
  );
}
