import { AlertTriangle } from "lucide-react";
import { RoadmapPlaceholder } from "@/components/roadmap-placeholder";

export default function Risks() {
  return (
    <RoadmapPlaceholder
      title="Risk Register"
      subtitle="Delayed and critical projects, surfaced and tracked in one place"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Operations", href: "/operations" }, { label: "Risk Register" }]}
      icon={AlertTriangle}
      status="in-development"
      phase="Phase 2 · Operational Workflows"
      description="A live risk register — the module behind the executive dashboard's 'Delays & risk' visibility — categorizing and scoring risk across every active project."
      capabilities={[
        "Risk identification & scoring",
        "Category & severity tracking",
        "Linked to projects and site reports",
        "Executive roll-up on the dashboard",
      ]}
    />
  );
}
