import { Inbox } from "lucide-react";
import { RoadmapPlaceholder } from "@/components/roadmap-placeholder";

export default function ClientPortalRequests() {
  return (
    <RoadmapPlaceholder
      title="Client Requests"
      subtitle="Requests submitted by clients, with supporting files attached"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Client Portal", href: "/client-portal" }, { label: "Requests" }]}
      icon={Inbox}
      status="planned"
      phase="Phase 4 · Client Collaboration"
      description="Client Request is one of the request types in the platform's approval workflow — planned for the client-facing portal, not yet live."
      capabilities={[
        "Submit a request with attachments",
        "Track approval status",
        "Client Request workflow",
        "Notifications on updates",
      ]}
    />
  );
}
