import { ListChecks } from "lucide-react";
import { RoadmapPlaceholder } from "@/components/roadmap-placeholder";

export default function Tasks() {
  return (
    <RoadmapPlaceholder
      title="Tasks"
      subtitle="Assigned work, deadlines, and accountability for project teams"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Tasks" }]}
      icon={ListChecks}
      status="in-development"
      phase="Phase 2 · Operational Workflows"
      description="A personal task list linking every assignment back to its project — part of the Employee & Project Workspace described in the product roadmap."
      capabilities={[
        "Access assigned projects",
        "Manage responsibilities",
        "Follow tasks & deadlines",
        "View project members",
        "Submit site reports",
        "Maintain accountability",
      ]}
    />
  );
}
