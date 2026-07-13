import { Sparkles, Bot, Brain } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import CopilotPage from "@/pages/copilot";
import RecentMemoriesPanel from "./RecentMemoriesPanel";
import MemoryTab from "./MemoryTab";

// AI Center — the AI workspace only (Product Polish phase). Document
// Intelligence moved to Documents (pages/documents/) and the Executive
// Reports placeholder was removed — a real, fully-working Executive Report
// already existed at /reports, so that tab was pure duplication. See the
// Phase 5 implementation report for the full rationale, including why
// "AI Chat" / "Knowledge Assistant" are treated as the same feature as
// Copilot rather than duplicated as separate tabs, and why "Cross-document
// AI Search" isn't a tab here (no backend capability exists for it yet).

export default function AICenter() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground flex items-center gap-2">
          <Sparkles className="w-7 h-7 text-primary" />
          AI Center
        </h1>
        <p className="text-muted-foreground mt-1">
          Copilot and remembered context — the AI workspace.
        </p>
      </div>

      <Tabs defaultValue="copilot" className="space-y-4">
        <TabsList>
          <TabsTrigger value="copilot" className="gap-1.5">
            <Bot className="w-4 h-4" />
            Copilot
          </TabsTrigger>
          <TabsTrigger value="memory" className="gap-1.5">
            <Brain className="w-4 h-4" />
            Memory Viewer
          </TabsTrigger>
        </TabsList>

        <TabsContent value="copilot">
          <div className="flex flex-col lg:flex-row gap-4">
            <div className="flex-1 min-w-0">
              <CopilotPage compact />
            </div>
            <RecentMemoriesPanel className="w-full lg:w-80 shrink-0 h-[75vh] min-h-[480px]" />
          </div>
        </TabsContent>

        <TabsContent value="memory">
          <MemoryTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
