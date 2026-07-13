import { useQuery } from "@tanstack/react-query";
import { CalendarDays, Users, Building2, Truck, Gavel, Brain, AlertTriangle, RotateCcw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { getMemory, MemoryGroupItem, MemoryGroups } from "@/lib/aiCenterClient";

// Memory Viewer — reads GET /api/v1/ai/memory, which groups the caller's
// own bounded memory server-side (app/ai/memory_reader.py::
// group_memory_notes, deterministic, no LLM). Loading / error / success
// (with or without records) are mutually exclusive render branches — never
// show the error banner and the empty-state cards at the same time.

type MemoryCategory = keyof Omit<MemoryGroups, "other">;

const CATEGORY_CONFIG: Record<MemoryCategory, { label: string; icon: typeof Users }> = {
  meeting: { label: "Meeting Memory", icon: CalendarDays },
  project: { label: "Project Memory", icon: Building2 },
  decision: { label: "Decision Memory", icon: Gavel },
  supplier: { label: "Supplier Memory", icon: Truck },
};

function MemoryCard({ item }: { item: MemoryGroupItem }) {
  return (
    <div className="rounded-lg border border-border p-4 space-y-2">
      <div className="flex items-start justify-between gap-3">
        <h4 className="font-medium text-foreground text-sm">{item.title ?? "Untitled memory note"}</h4>
        <Badge variant="outline" className="shrink-0 text-muted-foreground">
          Importance: {item.importance ?? "Not rated"}
        </Badge>
      </div>
      {item.date && <p className="text-xs text-muted-foreground">{item.date}</p>}
      <p className="text-sm text-muted-foreground line-clamp-3">{item.summary}</p>
    </div>
  );
}

function EmptyCategory() {
  return (
    <p className="text-sm text-muted-foreground italic py-4 text-center">
      No memory available yet.
    </p>
  );
}

function MemoryTabSkeleton() {
  return (
    <div className="space-y-6">
      {[0, 1, 2, 3].map((i) => (
        <Card key={i}>
          <CardHeader className="flex flex-row items-center gap-2 space-y-0">
            <Skeleton className="h-4 w-4 rounded-full" />
            <Skeleton className="h-4 w-32" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-16 w-full rounded-lg" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export default function MemoryTab() {
  const { data, isLoading, isError, refetch, isRefetching } = useQuery({
    queryKey: ["ai-center-memory"],
    queryFn: getMemory,
  });

  if (isLoading) {
    return <MemoryTabSkeleton />;
  }

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

  if (!data) {
    // Not loading, not errored, but no data yet — treat like loading rather
    // than crashing or silently rendering nothing.
    return <MemoryTabSkeleton />;
  }

  const groups = data.groups;

  return (
    <div className="space-y-6">
      {(Object.keys(CATEGORY_CONFIG) as MemoryCategory[]).map((category) => {
        const config = CATEGORY_CONFIG[category];
        const Icon = config.icon;
        const items = groups[category];
        return (
          <Card key={category}>
            <CardHeader className="flex flex-row items-center gap-2 space-y-0">
              <Icon className="w-4 h-4 text-primary" />
              <CardTitle className="text-base">{config.label}</CardTitle>
            </CardHeader>
            <CardContent>
              {items.length === 0 ? (
                <EmptyCategory />
              ) : (
                <div className="grid gap-3 sm:grid-cols-2">
                  {items.map((item, i) => <MemoryCard key={i} item={item} />)}
                </div>
              )}
            </CardContent>
          </Card>
        );
      })}

      {groups.other.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center gap-2 space-y-0">
            <Brain className="w-4 h-4 text-primary" />
            <CardTitle className="text-base">Other Memory Notes</CardTitle>
            <CardDescription className="ms-2">Not tied to a specific category</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {groups.other.map((item, i) => (
              <p key={i} className="text-sm text-muted-foreground border-b border-border last:border-0 pb-2 last:pb-0">
                {item.summary}
              </p>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
