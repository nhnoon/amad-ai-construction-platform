import { Bell } from "lucide-react";
import { RoadmapPlaceholder } from "@/components/roadmap-placeholder";

export default function Notifications() {
  return (
    <RoadmapPlaceholder
      title="Notifications"
      subtitle="Real-time updates on approvals, assignments, and project activity"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Notifications" }]}
      icon={Bell}
      status="in-development"
      phase="Phase 2 · Operational Workflows"
      description="A single notification center for the events that matter — approval decisions, new assignments, status changes, and mentions — replacing ad-hoc chat and email pings."
      capabilities={[
        "Approval & request alerts",
        "Project status changes",
        "Mentions & assignments",
        "Digest & channel preferences",
      ]}
    />
  );
}
