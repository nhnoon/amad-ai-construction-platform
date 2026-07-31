import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

// Shared in-page tab control — one segmented-tab look for the whole app.
// Several pages (Procurement, Safety, Meetings) previously hand-rolled their
// own underlined border-b-2 button tabs, visually distinct from the shadcn
// Tabs/TabsList/TabsTrigger primitive the detail pages already used. This
// wraps that same primitive so every in-page tab strip — record-type
// switchers here, detail-page section tabs elsewhere — looks identical.

export type PageTabItem<T extends string> = { id: T; label: string; count?: number };

export function PageTabs<T extends string>({
  tabs,
  value,
  onChange,
}: {
  tabs: PageTabItem<T>[];
  value: T;
  onChange: (id: T) => void;
}) {
  return (
    <Tabs value={value} onValueChange={(v) => onChange(v as T)}>
      <TabsList>
        {tabs.map((tab) => (
          <TabsTrigger key={tab.id} value={tab.id} data-testid={`tab-${tab.id}`}>
            {tab.label}
            {tab.count !== undefined && (
              <span className="ms-1.5 text-xs text-muted-foreground tabular-nums">{tab.count}</span>
            )}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}
