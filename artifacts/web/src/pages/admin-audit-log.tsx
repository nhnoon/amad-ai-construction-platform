import { History } from "lucide-react";
import { RoadmapPlaceholder } from "@/components/roadmap-placeholder";

export default function AdminAuditLog() {
  return (
    <RoadmapPlaceholder
      title="Audit Log"
      subtitle="A complete, unchangeable history of every decision"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Administration" }, { label: "Audit Log" }]}
      icon={History}
      status="in-development"
      phase="Phase 2 · Operational Workflows"
      description="The traceability backbone behind every approval and request — full audit history is a core differentiator of the platform, not an afterthought."
      capabilities={[
        "Full action history",
        "Approval decision trail",
        "User & role activity",
        "Exportable audit records",
      ]}
    />
  );
}
