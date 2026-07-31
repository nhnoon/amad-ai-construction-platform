import { FileCheck2 } from "lucide-react";
import { RoadmapPlaceholder } from "@/components/roadmap-placeholder";

export default function Requests() {
  return (
    <RoadmapPlaceholder
      title="Requests & Approvals"
      subtitle="A structured, auditable path for every internal request"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Requests & Approvals" }]}
      icon={FileCheck2}
      status="in-development"
      phase="Phase 2 · Operational Workflows"
      description="Every request moves through the same lifecycle — submitted, assigned, reviewed, impact assessed, approved or rejected, action completed — with a complete, unchangeable audit record."
      capabilities={[
        "Change Request",
        "Document Approval",
        "Purchase Request",
        "Project Issue",
        "Extension Request",
        "Corrective Action",
      ]}
    />
  );
}
