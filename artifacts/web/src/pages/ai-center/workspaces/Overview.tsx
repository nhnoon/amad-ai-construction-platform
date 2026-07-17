import { Link } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { useListProjects } from "@workspace/api-client-react";
import {
  Bot, Brain, Building2, ClipboardList, CalendarDays, FileSignature, LineChart, ArrowRight,
} from "lucide-react";
import { getMemory } from "@/lib/aiCenterClient";
import { useExecutive } from "@/lib/useExecutive";
import { bucketFor } from "../memoryTaxonomy";

// AI Workspace overview — the landing grid that replaces the old
// single-chat-window AI Center (Product UX Phase 1 §1). Each card links
// into its own real workspace instead of everything happening inside one
// chat. Stats shown are drawn from data other workspaces already fetch
// (memory, projects, executive intelligence) rather than new endpoints.

export default function Overview() {
  const { data: memory } = useQuery({ queryKey: ["ai-center-memory"], queryFn: getMemory });
  const { data: projects } = useListProjects({ limit: 100 });
  const { data: exec } = useExecutive();

  const contractCount = (memory?.structured_memories ?? []).filter(
    (m) => bucketFor(m.source, m.category) === "contract",
  ).length;
  const meetingCount = (memory?.structured_memories ?? []).filter(
    (m) => bucketFor(m.source, m.category) === "meeting",
  ).length;
  const siteReportCount = (memory?.structured_memories ?? []).filter(
    (m) => bucketFor(m.source, m.category) === "site_report",
  ).length;

  const cards = [
    {
      key: "copilot", href: "/ai-center/copilot", icon: Bot, tone: "text-blue-500 bg-blue-500/10",
      title: "AI Copilot", description: "Ask multi-turn questions across projects, procurement, safety, and reports.",
      stat: "Read-only · grounded in platform data",
    },
    {
      key: "memory", href: "/ai-center/memory", icon: Brain, tone: "text-violet-500 bg-violet-500/10",
      title: "Memory Center", description: "Add, edit, search, and review everything the AI remembers across conversations.",
      stat: memory ? `${memory.structured_memories.length} saved memories` : undefined,
    },
    {
      key: "projects", href: "/ai-center/projects", icon: Building2, tone: "text-emerald-500 bg-emerald-500/10",
      title: "Project Intelligence", description: "Health score, AI summary, and Ask Hermes for every project.",
      stat: projects ? `${projects.length} projects` : undefined,
    },
    {
      key: "site-reports", href: "/ai-center/site-reports", icon: ClipboardList, tone: "text-amber-500 bg-amber-500/10",
      title: "Site Report Intelligence", description: "Evidence-grounded analysis, risk scoring, and AI reasoning per report.",
      stat: siteReportCount ? `${siteReportCount} analyzed reports in memory` : undefined,
    },
    {
      key: "meetings", href: "/ai-center/meetings", icon: CalendarDays, tone: "text-sky-500 bg-sky-500/10",
      title: "Meeting Intelligence", description: "Recent meetings, extracted decisions, and open action items.",
      stat: meetingCount ? `${meetingCount} meetings in memory` : undefined,
    },
    {
      key: "contracts", href: "/ai-center/contracts", icon: FileSignature, tone: "text-rose-500 bg-rose-500/10",
      title: "Contract Intelligence", description: "Completed contract extractions — value, obligations, flagged risks.",
      stat: contractCount ? `${contractCount} contracts analyzed` : undefined,
    },
    {
      key: "executive", href: "/ai-center/executive", icon: LineChart, tone: "text-orange-500 bg-orange-500/10",
      title: "Executive Intelligence", description: "Critical projects, top risks, procurement issues, suggested actions.",
      stat: exec ? `Portfolio score ${exec.portfolio_score}/100` : undefined,
    },
  ];

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-foreground">AI Workspace</h2>
        <p className="text-sm text-muted-foreground">Seven focused workspaces, each grounded in real platform data — pick where to start.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {cards.map((c) => {
          const Icon = c.icon;
          return (
            <Link
              key={c.key}
              href={c.href}
              className="rounded-xl border border-border bg-card p-5 space-y-3 hover:border-primary/30 hover:shadow-md transition-all group"
            >
              <div className="flex items-center justify-between">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${c.tone}`}>
                  <Icon className="w-5 h-5" />
                </div>
                <ArrowRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground">{c.title}</h3>
                <p className="text-sm text-muted-foreground mt-1 leading-relaxed">{c.description}</p>
              </div>
              {c.stat && (
                <p className="text-xs font-medium text-primary pt-1 border-t border-border/50">{c.stat}</p>
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
