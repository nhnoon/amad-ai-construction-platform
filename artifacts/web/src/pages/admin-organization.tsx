import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Building2, Plus, Edit2, CheckCircle2, XCircle, Save, X } from "lucide-react";
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
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { getToken } from "../lib/auth";

const API_BASE = "/api/v1";

interface Organization {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string;
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
  return res.json();
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-SA", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function OrgCard({
  org,
  onEdit,
}: {
  org: Organization;
  onEdit: (org: Organization) => void;
}) {
  const qc = useQueryClient();
  const { toast } = useToast();

  const toggleMutation = useMutation({
    mutationFn: (is_active: boolean) =>
      apiFetch<Organization>(`/admin/organizations/${org.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active }),
      }),
    onSuccess: (updated) => {
      qc.invalidateQueries({ queryKey: ["admin-orgs"] });
      toast({
        title: updated.is_active ? "Organization activated" : "Organization deactivated",
        description: updated.name,
      });
    },
    onError: (err: Error) =>
      toast({ title: "Update failed", description: err.message, variant: "destructive" }),
  });

  return (
    <div className="rounded-xl border border-border bg-card p-5 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
            <Building2 className="w-5 h-5 text-primary" />
          </div>
          <div className="min-w-0">
            <h3 className="font-semibold text-foreground text-base leading-tight">{org.name}</h3>
            <p className="text-xs text-muted-foreground mt-0.5 font-mono">/{org.slug}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {org.is_active ? (
            <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Active
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-xs font-medium text-zinc-400">
              <XCircle className="w-3.5 h-3.5" />
              Inactive
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-lg bg-muted/40 px-3 py-2">
          <p className="text-xs text-muted-foreground">Organization ID</p>
          <p className="text-sm font-semibold text-foreground mt-0.5">#{org.id}</p>
        </div>
        <div className="rounded-lg bg-muted/40 px-3 py-2">
          <p className="text-xs text-muted-foreground">Created</p>
          <p className="text-sm font-semibold text-foreground mt-0.5">{formatDate(org.created_at)}</p>
        </div>
      </div>

      <div className="flex gap-2 pt-1">
        <Button
          size="sm"
          variant="outline"
          className="flex-1"
          onClick={() => onEdit(org)}
        >
          <Edit2 className="w-3.5 h-3.5 me-1.5" />
          Edit
        </Button>
        <Button
          size="sm"
          variant="ghost"
          className="flex-1"
          onClick={() => toggleMutation.mutate(!org.is_active)}
          disabled={toggleMutation.isPending}
        >
          {org.is_active ? (
            <>
              <XCircle className="w-3.5 h-3.5 me-1.5 text-muted-foreground" />
              Deactivate
            </>
          ) : (
            <>
              <CheckCircle2 className="w-3.5 h-3.5 me-1.5 text-emerald-500" />
              Activate
            </>
          )}
        </Button>
      </div>
    </div>
  );
}

function EditOrgDialog({
  org,
  onClose,
}: {
  org: Organization | null;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const { toast } = useToast();
  const [form, setForm] = useState({ name: org?.name ?? "", slug: org?.slug ?? "" });
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: (body: { name: string; slug: string }) =>
      apiFetch<Organization>(`/admin/organizations/${org!.id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-orgs"] });
      toast({ title: "Organization updated", description: form.name });
      onClose();
    },
    onError: (err: Error) => setError(err.message),
  });

  if (!org) return null;

  return (
    <Dialog open={!!org} onOpenChange={(v) => { if (!v) { setError(""); onClose(); } }}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Edit2 className="w-5 h-5 text-primary" />
            Edit Organization
          </DialogTitle>
          <DialogDescription>Update the organization name and slug identifier.</DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => { e.preventDefault(); setError(""); mutation.mutate(form); }}
          className="space-y-4 pt-1"
        >
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-foreground">Name *</label>
            <Input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-foreground">Slug *</label>
            <Input
              value={form.slug}
              onChange={(e) =>
                setForm({ ...form, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-") })
              }
              required
              className="font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">
              Lowercase letters, numbers, and hyphens only.
            </p>
          </div>
          {error && (
            <p className="text-sm text-destructive bg-destructive/5 rounded-md px-3 py-2">{error}</p>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={mutation.isPending}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? (
                <>
                  <Save className="w-4 h-4 me-1.5 animate-pulse" />
                  Saving…
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 me-1.5" />
                  Save Changes
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function CreateOrgDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const { toast } = useToast();
  const [form, setForm] = useState({ name: "", slug: "" });
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: (body: { name: string; slug: string }) =>
      apiFetch<Organization>("/admin/organizations", {
        method: "POST",
        body: JSON.stringify({ ...body, is_active: true }),
      }),
    onSuccess: (org) => {
      qc.invalidateQueries({ queryKey: ["admin-orgs"] });
      toast({ title: "Organization created", description: org.name });
      setForm({ name: "", slug: "" });
      setError("");
      onClose();
    },
    onError: (err: Error) => setError(err.message),
  });

  const handleNameChange = (name: string) => {
    const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
    setForm({ name, slug });
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) { setError(""); onClose(); } }}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Plus className="w-5 h-5 text-primary" />
            New Organization
          </DialogTitle>
          <DialogDescription>
            Create a new organization to group users and projects.
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => { e.preventDefault(); setError(""); mutation.mutate(form); }}
          className="space-y-4 pt-1"
        >
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-foreground">Name *</label>
            <Input
              placeholder="Al-Rashid Contracting Co."
              value={form.name}
              onChange={(e) => handleNameChange(e.target.value)}
              required
              autoFocus
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-foreground">Slug *</label>
            <Input
              placeholder="al-rashid-contracting"
              value={form.slug}
              onChange={(e) =>
                setForm({ ...form, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-") })
              }
              required
              className="font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">
              Unique identifier. Auto-generated from name.
            </p>
          </div>
          {error && (
            <p className="text-sm text-destructive bg-destructive/5 rounded-md px-3 py-2">{error}</p>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={mutation.isPending}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Creating…" : "Create Organization"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function AdminOrganization() {
  const { t } = useTranslation();
  const [editTarget, setEditTarget] = useState<Organization | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  const { data: orgs = [], isLoading, isError } = useQuery<Organization[]>({
    queryKey: ["admin-orgs"],
    queryFn: () => apiFetch<Organization[]>("/admin/organizations"),
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-52" />
          <Skeleton className="h-9 w-36" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[0, 1].map((i) => <Skeleton key={i} className="h-44 rounded-xl" />)}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-8 text-center">
        <XCircle className="w-8 h-8 text-destructive mx-auto mb-2" />
        <p className="text-sm text-destructive font-medium">Failed to load organizations</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Building2 className="w-6 h-6 text-primary" />
            Organizations
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Manage tenant organizations for the platform.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)} className="shrink-0">
          <Plus className="w-4 h-4 me-2" />
          New Organization
        </Button>
      </div>

      {/* Summary stat */}
      <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-border bg-card">
        <Building2 className="w-4 h-4 text-primary" />
        <span className="text-sm text-muted-foreground">
          <strong className="text-foreground">{orgs.length}</strong>{" "}
          organization{orgs.length !== 1 ? "s" : ""} registered ·{" "}
          <strong className="text-emerald-600 dark:text-emerald-400">
            {orgs.filter((o) => o.is_active).length} active
          </strong>
        </span>
      </div>

      {/* Org cards */}
      {orgs.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border bg-muted/20 p-12 text-center">
          <Building2 className="w-8 h-8 text-muted-foreground/40 mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">
            No organizations yet. Create one to group your users and projects.
          </p>
          <Button className="mt-4" onClick={() => setCreateOpen(true)}>
            <Plus className="w-4 h-4 me-2" />
            Create First Organization
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {orgs.map((org) => (
            <OrgCard key={org.id} org={org} onEdit={setEditTarget} />
          ))}
        </div>
      )}

      <EditOrgDialog org={editTarget} onClose={() => setEditTarget(null)} />
      <CreateOrgDialog open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
}
