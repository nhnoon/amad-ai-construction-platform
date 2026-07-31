import { Mail } from "lucide-react";
import { RoadmapPlaceholder } from "@/components/roadmap-placeholder";

export default function EmailIntelligence() {
  return (
    <RoadmapPlaceholder
      title="Email Intelligence"
      subtitle="Classify incoming messages and draft grounded responses"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "AI Center", href: "/ai-center" }, { label: "Email Intelligence" }]}
      icon={Mail}
      status="in-development"
      phase="Phase 3 · Document Intelligence & AI"
      description="Classifies and routes incoming messages, and can draft supplier or client responses — every output still requires human review before it's sent."
      capabilities={[
        "Inbound message classification",
        "Routing suggestions",
        "Draft supplier / client responses",
        "Priority flagging",
      ]}
    />
  );
}
