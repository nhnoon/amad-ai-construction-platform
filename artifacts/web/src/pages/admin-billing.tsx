import { CreditCard } from "lucide-react";
import { RoadmapPlaceholder } from "@/components/roadmap-placeholder";

export default function AdminBilling() {
  return (
    <RoadmapPlaceholder
      title="Billing & Subscription"
      subtitle="Plan, seats, and usage for your organization"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Administration" }, { label: "Billing & Subscription" }]}
      icon={CreditCard}
      status="planned"
      phase="Phase 5 · Commercial Scale"
      description="Subscription plans are part of the commercial-scale phase of the roadmap — this organization is not yet on a paid plan."
      capabilities={[
        "Subscription plan management",
        "Usage & seat tracking",
        "Invoices & payment methods",
        "Plan upgrades",
      ]}
    />
  );
}
