import { Handshake } from "lucide-react";
import { RoadmapPlaceholder } from "@/components/roadmap-placeholder";

export default function ClientPortalOverview() {
  return (
    <RoadmapPlaceholder
      title="Client Portal"
      subtitle="A transparent, self-service window into a client's project"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Client Portal" }]}
      icon={Handshake}
      status="planned"
      phase="Phase 4 · Client Collaboration"
      description="Planned client experience — not yet live. Authorized, project-scoped clients will be able to follow progress, submit requests, and approve changes without chasing updates by phone or email."
      capabilities={[
        "Access their project",
        "Submit a request",
        "Follow status in real time",
        "Review & approve changes",
        "Stay informed via updates & notifications",
      ]}
    />
  );
}
