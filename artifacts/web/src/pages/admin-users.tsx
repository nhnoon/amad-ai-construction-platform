import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  UserPlus, Search, RotateCcw, Shield, CheckCircle2,
  XCircle, Copy, Check, ChevronDown, Users,
} from "lucide-react";
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

const ROLE_COLORS: Record<string, string> = {
  admin:
    "bg-[#0D1F3C]/10 text-[#0D1F3C] dark:bg-[#C8953A]/15 dark:text-[#C8953A] border border-[#0D1F3C]/20 dark:border-[#C8953A]/30",
  executive:
    "bg-purple-50 text-purple-700 border border-purple-200 dark:bg-purple-900/20 dark:text-purple-300 dark:border-purple-700/30",
  project_manager:
    "bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-700/30",
  site_engineer:
    "bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-300 dark:border-emerald-700/30",
  procurement_officer:
    "bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-900/20 dark:text-amber-300 dark:border-amber-700/30",
  safety_quality_officer:
    "bg-red-50 text-red-700 border border-red-200 dark:bg-red-900/20 dark:text-red-300 dark:border-red-700/30",
  viewer:
    "bg-zinc-100 text-zinc-600 border border-zinc-200 dark:bg-zinc-800/50 dark:text-zinc-400 dark:border-zinc-700/30",
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
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${ROLE_COLORS[role] ?? ROLE_COLORS.viewer}`}
    >
      {label}
    </span>
  );
}

function StatusBadge({ active }: { active: boolean }) {
  return active ? (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400">
      <CheckCircle2 className="w-3.5 h-3.5" />
      Active
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-zinc-400">
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
  const { toast } = useToast();
  const [form, setForm] = useState({
    email: "",
    full_name: "",
    role: "site_engineer",
    temporary_password: "Welcome123!",
  });
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: (body: typeof form) =>
      apiFetch<User>("/admin/users", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      toast({ title: "User created", description: `${form.email} was added to the platform.` });
      setForm({ email: "", full_name: "", role: "site_engineer", temporary_password: "Welcome123!" });
      setError("");
      onClose();
    },
    onError: (err: Error) => setError(err.message),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    mutation.mutate(form);
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <UserPlus className="w-5 h-5 text-primary" />
            Create New User
          </DialogTitle>
          <DialogDescription>
            Add a team member to the platform. They'll receive the temporary password you set.
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
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-foreground">Temporary Password *</label>
            <Input
              type="text"
              placeholder="Welcome123!"
              value={form.temporary_password}
              onChange={(e) => setForm({ ...form, temporary_password: e.target.value })}
              required
            />
            <p className="text-xs text-muted-foreground">Minimum 8 characters. Share this securely with the user.</p>
          </div>
          {error && (
            <p className="text-sm text-destructive bg-destructive/5 rounded-md px-3 py-2">{error}</p>
          )}
          <DialogFooter className="pt-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={mutation.isPending}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Creating…" : "Create User"}
            </Button>
          </DialogFooter>
        </form>
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
              <Button size="icon" variant="outline" onClick={handleCopy} className="shrink-0">
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Users className="w-6 h-6 text-primary" />
            {t("User Management")}
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Manage platform users, roles, and access.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)} className="shrink-0">
          <UserPlus className="w-4 h-4 me-2" />
          New User
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: "Total Users", value: stats.total, color: "text-primary" },
          { label: "Active", value: stats.active, color: "text-emerald-600 dark:text-emerald-400" },
          { label: "Administrators", value: stats.admins, color: "text-amber-600 dark:text-amber-400" },
        ].map((s) => (
          <div
            key={s.label}
            className="rounded-xl border border-border bg-card px-5 py-4"
          >
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
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        {filtered.length === 0 ? (
          <div className="p-12 text-center">
            <Users className="w-8 h-8 text-muted-foreground/40 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">
              {search || roleFilter !== "all" ? "No users match your filters." : "No users yet. Create one above."}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/30">
                  <th className="px-4 py-3 text-start font-medium text-muted-foreground">User</th>
                  <th className="px-4 py-3 text-start font-medium text-muted-foreground">Role</th>
                  <th className="px-4 py-3 text-start font-medium text-muted-foreground">Status</th>
                  <th className="px-4 py-3 text-start font-medium text-muted-foreground hidden md:table-cell">
                    Last Login
                  </th>
                  <th className="px-4 py-3 text-start font-medium text-muted-foreground hidden lg:table-cell">
                    Created
                  </th>
                  <th className="px-4 py-3 text-end font-medium text-muted-foreground">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filtered.map((user) => {
                  const initials = (user.full_name ?? user.email)
                    .split(" ")
                    .map((w) => w[0])
                    .slice(0, 2)
                    .join("")
                    .toUpperCase();
                  return (
                    <tr
                      key={user.id}
                      className="hover:bg-muted/20 transition-colors"
                    >
                      <td className="px-4 py-3">
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
                      <td className="px-4 py-3">
                        <RoleBadge role={user.role} />
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge active={user.is_active} />
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground hidden md:table-cell">
                        {formatDate(user.last_login)}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground hidden lg:table-cell">
                        {formatDate(user.created_at)}
                      </td>
                      <td className="px-4 py-3">
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
    </div>
  );
}
