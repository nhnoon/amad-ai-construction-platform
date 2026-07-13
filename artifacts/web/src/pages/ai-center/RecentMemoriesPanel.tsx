import { useQuery } from "@tanstack/react-query";
import { Brain, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { getMemory } from "@/lib/aiCenterClient";

export default function RecentMemoriesPanel({ className }: { className?: string }) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["ai-center-memory"],
    queryFn: getMemory,
  });

  const allItems = data
    ? [...data.groups.meeting, ...data.groups.project, ...data.groups.decision, ...data.groups.supplier].slice(0, 5)
    : [];

  return (
    <Card className={cn("flex flex-col", className)}>
      <CardHeader className="flex flex-row items-center gap-2 space-y-0 shrink-0">
        <Brain className="w-4 h-4 text-primary" />
        <CardTitle className="text-sm">Recent Memories</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto space-y-3">
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-10 w-full rounded-md" />
            <Skeleton className="h-10 w-full rounded-md" />
          </div>
        ) : isError ? (
          <div className="flex items-start gap-2 text-xs text-muted-foreground">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            <span className="flex-1">Unable to load memory right now.</span>
            <Button size="sm" variant="ghost" className="h-6 px-2 text-xs shrink-0" onClick={() => refetch()}>
              Retry
            </Button>
          </div>
        ) : allItems.length === 0 ? (
          <div className="text-center py-6">
            <Brain className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" />
            <p className="text-xs text-muted-foreground">No memories yet. As you use Copilot, remembered context will appear here.</p>
          </div>
        ) : (
          allItems.map((item, i) => (
            <div key={i} className="text-xs border-b border-border last:border-0 pb-2 last:pb-0">
              <p className="font-medium text-foreground truncate">{item.title ?? "Untitled memory note"}</p>
              {item.date && <p className="text-muted-foreground">{item.date}</p>}
              <p className="text-muted-foreground line-clamp-2 mt-0.5">{item.summary}</p>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
