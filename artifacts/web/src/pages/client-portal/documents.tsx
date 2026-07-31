import { FolderOpen } from "lucide-react";
import { RoadmapPlaceholder } from "@/components/roadmap-placeholder";

export default function ClientPortalDocuments() {
  return (
    <RoadmapPlaceholder
      title="Client Documents"
      subtitle="Shared, approved project records visible to the client"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Client Portal", href: "/client-portal" }, { label: "Documents" }]}
      icon={FolderOpen}
      status="planned"
      phase="Phase 4 · Client Collaboration"
      description="A client-scoped view of the document center — shared, approved records only, planned for the client-facing portal."
      capabilities={[
        "Shared project documents",
        "Approved record access",
        "Document-linked communication",
        "Download & view history",
      ]}
    />
  );
}
