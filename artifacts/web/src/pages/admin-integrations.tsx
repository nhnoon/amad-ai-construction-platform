import { Plug } from "lucide-react";
import { RoadmapPlaceholder } from "@/components/roadmap-placeholder";

export default function AdminIntegrations() {
  return (
    <RoadmapPlaceholder
      title="Integrations"
      subtitle="Connect Amad to the tools your teams already use"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Administration" }, { label: "Integrations" }]}
      icon={Plug}
      status="planned"
      phase="Phase 5 · Commercial Scale"
      description="Part of the commercial-scale phase of the roadmap, alongside mobile access and advanced analytics — not yet scheduled for active development."
      capabilities={[
        "Third-party connectors",
        "Webhooks & API keys",
        "Calendar & email sync",
        "ERP / accounting bridges",
      ]}
    />
  );
}
