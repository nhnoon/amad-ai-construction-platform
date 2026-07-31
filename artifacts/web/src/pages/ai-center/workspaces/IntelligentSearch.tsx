import { Search } from "lucide-react";
import { RoadmapPlaceholder } from "@/components/roadmap-placeholder";

export default function IntelligentSearch() {
  return (
    <RoadmapPlaceholder
      title="Intelligent Search"
      subtitle="One search bar across every project, document, and report"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "AI Center", href: "/ai-center" }, { label: "Intelligent Search" }]}
      icon={Search}
      status="in-development"
      phase="Phase 3 · Document Intelligence & AI"
      description="Natural-language search grounded in real platform data, returning source-linked results instead of a generic chat answer."
      capabilities={[
        "Search across projects, documents, reports",
        "Natural-language queries",
        "Source-linked results",
        "Cross-workspace retrieval",
      ]}
    />
  );
}
