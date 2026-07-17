import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Search, Plus, RotateCcw, Trash2, Pencil, Loader2, AlertTriangle, LayoutGrid, ListTree, Brain,
  ChevronDown, ChevronRight,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  getMemory, deleteMemoryRecord, type StructuredMemory,
} from "@/lib/aiCenterClient";
import {
  BUCKET_META, BUCKET_ORDER, PRIORITY_TONE, bucketFor, matchesSearch, type MemoryBucket,
} from "./memoryTaxonomy";
import { MemoryFormDialog } from "./MemoryFormDialog";

type ViewMode = "grid" | "timeline";
type PriorityFilter = "all" | "High" | "Medium" | "Low";

function MemoryCard({
  item, onEdit, onDelete, deleting,
}: {
  item: StructuredMemory;
  onEdit: (item: StructuredMemory) => void;
  onDelete: (id: number) => void;
  deleting: boolean;
}) {
  const bucket = bucketFor(item.source, item.category);
  const Icon = BUCKET_META[bucket].icon;
  return (
    <div className="rounded-xl border border-border bg-card p-4 space-y-2.5 hover:border-primary/30 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
            <Icon className="w-4 h-4 text-primary" />
          </div>
          <div className="min-w-0">
            <h4 className="font-semibold text-foreground text-sm leading-snug">{item.title}</h4>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              {BUCKET_META[bucket].label} &middot; {new Date(item.created_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}
            </p>
          </div>
        </div>
        {(item.can_edit || item.can_delete) && (
          <div className="flex items-center gap-0.5 shrink-0">
            {item.can_edit && (
              <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground" onClick={() => onEdit(item)} aria-label="Edit memory">
                <Pencil className="h-3.5 w-3.5" />
              </Button>
            )}
            {item.can_delete && (
              <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive" onClick={() => onDelete(item.id)} disabled={deleting} aria-label="Delete memory">
                {deleting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
              </Button>
            )}
          </div>
        )}
      </div>

      <p className="text-sm text-muted-foreground leading-relaxed line-clamp-3">{item.summary}</p>

      <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
        <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${PRIORITY_TONE[item.priority] ?? PRIORITY_TONE.Low}`}>
          {item.priority} priority
        </span>
        {item.project_code && <Badge variant="outline" className="text-[10px]">{item.project_code}</Badge>}
        {item.citation && item.citation !== item.project_code && (
          <Badge variant="outline" className="text-[10px] font-mono">{item.citation}</Badge>
        )}
        <Badge variant="secondary" className="text-[10px] capitalize">{item.source.replace(/_/g, " ")}</Badge>
      </div>
    </div>
  );
}

function MemoryCenterSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-10 w-full rounded-lg" />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {[0, 1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-40 w-full rounded-xl" />)}
      </div>
    </div>
  );
}

export default function MemoryCenter({ projectCodeFilter }: { projectCodeFilter?: string } = {}) {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [bucketFilter, setBucketFilter] = useState<MemoryBucket | "all">("all");
  const [priorityFilter, setPriorityFilter] = useState<PriorityFilter>("all");
  const [view, setView] = useState<ViewMode>("grid");
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<StructuredMemory | null>(null);
  const [legacyOpen, setLegacyOpen] = useState(false);

  const { data, isLoading, isError, refetch, isRefetching } = useQuery({
    queryKey: ["ai-center-memory"],
    queryFn: getMemory,
  });

  const allRecords = data?.structured_memories ?? [];
  const scopedRecords = projectCodeFilter
    ? allRecords.filter((r) => r.project_code === projectCodeFilter)
    : allRecords;

  const bucketCounts = useMemo(() => {
    const counts: Partial<Record<MemoryBucket, number>> = {};
    for (const r of scopedRecords) {
      const b = bucketFor(r.source, r.category);
      counts[b] = (counts[b] ?? 0) + 1;
    }
    return counts;
  }, [scopedRecords]);

  const filtered = scopedRecords.filter((r) => {
    if (bucketFilter !== "all" && bucketFor(r.source, r.category) !== bucketFilter) return false;
    if (priorityFilter !== "all" && r.priority !== priorityFilter) return false;
    if (!matchesSearch(r, search)) return false;
    return true;
  });

  const sorted = [...filtered].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  const timelineGroups = useMemo(() => {
    const groups = new Map<string, StructuredMemory[]>();
    for (const item of sorted) {
      const label = new Date(item.created_at).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
      const list = groups.get(label) ?? [];
      list.push(item);
      groups.set(label, list);
    }
    return Array.from(groups.entries());
  }, [sorted]);

  const handleDelete = async (id: number) => {
    setDeletingId(id);
    setActionError(null);
    try {
      await deleteMemoryRecord(id);
      await queryClient.invalidateQueries({ queryKey: ["ai-center-memory"] });
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to delete memory.");
    } finally {
      setDeletingId(null);
    }
  };

  const openAdd = () => { setEditingRecord(null); setFormOpen(true); };
  const openEdit = (item: StructuredMemory) => { setEditingRecord(item); setFormOpen(true); };

  if (isLoading) return <MemoryCenterSkeleton />;

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription className="flex items-center justify-between gap-3">
          <span>Unable to load memory right now.</span>
          <Button size="sm" variant="outline" onClick={() => refetch()} disabled={isRefetching} className="gap-1.5">
            <RotateCcw className={isRefetching ? "w-3.5 h-3.5 animate-spin" : "w-3.5 h-3.5"} />
            Retry
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Memory Center</h2>
          <p className="text-sm text-muted-foreground">
            {scopedRecords.length} saved {scopedRecords.length === 1 ? "memory" : "memories"} across {Object.keys(bucketCounts).length} categor{Object.keys(bucketCounts).length === 1 ? "y" : "ies"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={() => refetch()} disabled={isRefetching} className="gap-1.5">
            <RotateCcw className={isRefetching ? "w-3.5 h-3.5 animate-spin" : "w-3.5 h-3.5"} />
            Refresh
          </Button>
          <Button size="sm" onClick={openAdd} className="gap-1.5">
            <Plus className="w-3.5 h-3.5" />
            Add Memory
          </Button>
        </div>
      </div>

      {actionError && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{actionError}</AlertDescription>
        </Alert>
      )}

      {/* Category quick-filter chips */}
      <div className="flex flex-wrap gap-1.5">
        <button
          onClick={() => setBucketFilter("all")}
          className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
            bucketFilter === "all" ? "bg-primary text-primary-foreground border-primary" : "border-border text-muted-foreground hover:text-foreground hover:border-primary/40"
          }`}
        >
          All ({scopedRecords.length})
        </button>
        {BUCKET_ORDER.filter((b) => (bucketCounts[b] ?? 0) > 0).map((b) => {
          const Icon = BUCKET_META[b].icon;
          return (
            <button
              key={b}
              onClick={() => setBucketFilter(bucketFilter === b ? "all" : b)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                bucketFilter === b ? "bg-primary text-primary-foreground border-primary" : "border-border text-muted-foreground hover:text-foreground hover:border-primary/40"
              }`}
            >
              <Icon className="w-3 h-3" />
              {BUCKET_META[b].label} ({bucketCounts[b]})
            </button>
          );
        })}
      </div>

      {/* Search + filters + view toggle */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search memory by title, content, or project..."
            className="pl-9 h-9"
          />
        </div>
        <Select value={priorityFilter} onValueChange={(v) => setPriorityFilter(v as PriorityFilter)}>
          <SelectTrigger className="w-36 h-9"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All priorities</SelectItem>
            <SelectItem value="High">High priority</SelectItem>
            <SelectItem value="Medium">Medium priority</SelectItem>
            <SelectItem value="Low">Low priority</SelectItem>
          </SelectContent>
        </Select>
        <div className="flex items-center rounded-lg border border-border p-0.5">
          <button
            onClick={() => setView("grid")}
            className={`p-1.5 rounded-md transition-colors ${view === "grid" ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground"}`}
            aria-label="Grid view"
            title="Grid view"
          >
            <LayoutGrid className="w-4 h-4" />
          </button>
          <button
            onClick={() => setView("timeline")}
            className={`p-1.5 rounded-md transition-colors ${view === "timeline" ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground"}`}
            aria-label="Timeline view"
            title="Timeline view"
          >
            <ListTree className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Content */}
      {sorted.length === 0 ? (
        <Card>
          <CardContent className="py-4">
            <EmptyState
              icon={Brain}
              title={scopedRecords.length === 0 ? "Nothing saved yet" : "No memories match your filters"}
              description={
                scopedRecords.length === 0
                  ? "Add a memory, or let it build automatically from meetings, site report analyses, and contract extractions."
                  : "Try a different search term, category, or priority."
              }
              action={scopedRecords.length === 0 ? (
                <Button size="sm" onClick={openAdd} className="gap-1.5"><Plus className="w-3.5 h-3.5" />Add Memory</Button>
              ) : undefined}
            />
          </CardContent>
        </Card>
      ) : view === "grid" ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {sorted.map((item) => (
            <MemoryCard key={item.id} item={item} onEdit={openEdit} onDelete={handleDelete} deleting={deletingId === item.id} />
          ))}
        </div>
      ) : (
        <div className="space-y-6">
          {timelineGroups.map(([dateLabel, items]) => (
            <div key={dateLabel} className="relative ps-6 border-s-2 border-border">
              <div className="absolute -start-[7px] top-0.5 w-3 h-3 rounded-full bg-primary" />
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">{dateLabel}</p>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {items.map((item) => (
                  <MemoryCard key={item.id} item={item} onEdit={openEdit} onDelete={handleDelete} deleting={deletingId === item.id} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Legacy note-blob memory — the original bounded per-user text
          store (app/ai/memory.py), kept visible rather than removed so
          nothing that used to be shown disappears (Phase 1 constraint:
          "Do not remove existing capabilities"). Superseded going forward
          by the structured records above. */}
      {data && (() => {
        const legacyGroups = [
          { key: "meeting", label: "Meeting", items: data.groups.meeting },
          { key: "project", label: "Project", items: data.groups.project },
          { key: "decision", label: "Decision", items: data.groups.decision },
          { key: "supplier", label: "Supplier", items: data.groups.supplier },
          { key: "other", label: "Other", items: data.groups.other },
        ].filter((g) => g.items.length > 0);
        if (legacyGroups.length === 0) return null;
        return (
          <div className="pt-3 border-t border-border">
            <button
              onClick={() => setLegacyOpen((p) => !p)}
              className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              {legacyOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
              Legacy note memory ({legacyGroups.reduce((n, g) => n + g.items.length, 0)})
            </button>
            {legacyOpen && (
              <div className="mt-3 space-y-4">
                {legacyGroups.map((g) => (
                  <div key={g.key}>
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">{g.label}</p>
                    <div className="grid gap-2 sm:grid-cols-2">
                      {g.items.map((item, i) => (
                        <div key={i} className="rounded-lg border border-border/60 p-3 text-xs text-muted-foreground">
                          {item.title && <p className="font-medium text-foreground mb-0.5">{item.title}</p>}
                          <p className="line-clamp-2">{item.summary}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })()}

      <MemoryFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        editingRecord={editingRecord}
        defaultProjectCode={projectCodeFilter}
        onSaved={() => queryClient.invalidateQueries({ queryKey: ["ai-center-memory"] })}
      />
    </div>
  );
}
