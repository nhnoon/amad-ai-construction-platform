import { useState, useEffect } from "react";
import { X, Zap, Users, FileText, ShoppingCart, Search, MessageSquare, ArrowRight } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface AITool {
  id: string;
  nameKey: string;
  descriptionKey: string;
  icon: React.ReactNode;
  color: string;
}

const AI_HOME_CARDS: AITool[] = [
  {
    id: "meeting-intelligence",
    nameKey: "Meeting Intelligence",
    descriptionKey: "Analyze meetings and extract action items",
    icon: <Users className="w-6 h-6" />,
    color: "from-blue-500/20 to-blue-600/20 border-blue-500/30",
  },
  {
    id: "site-intelligence",
    nameKey: "Site Intelligence",
    descriptionKey: "Review site reports and identify risks",
    icon: <FileText className="w-6 h-6" />,
    color: "from-amber-500/20 to-amber-600/20 border-amber-500/30",
  },
  {
    id: "procurement-intelligence",
    nameKey: "Procurement Intelligence",
    descriptionKey: "Review purchase requests and compliance",
    icon: <ShoppingCart className="w-6 h-6" />,
    color: "from-emerald-500/20 to-emerald-600/20 border-emerald-500/30",
  },
  {
    id: "enterprise-memory",
    nameKey: "Enterprise Memory",
    descriptionKey: "Search organizational knowledge and data",
    icon: <Search className="w-6 h-6" />,
    color: "from-purple-500/20 to-purple-600/20 border-purple-500/30",
  },
  {
    id: "ask-ai",
    nameKey: "Ask Construction AI",
    descriptionKey: "Have a conversation with AI assistant",
    icon: <MessageSquare className="w-6 h-6" />,
    color: "from-pink-500/20 to-pink-600/20 border-pink-500/30",
  },
];

interface AIDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AIDrawer({ isOpen, onClose }: AIDrawerProps) {
  const { t, i18n } = useTranslation();
  const [activeWorkspace, setActiveWorkspace] = useState<string | null>(null);
  const isRtl = i18n.language === "ar";

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  const handleBackToHome = () => {
    setActiveWorkspace(null);
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Overlay backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-45 bg-black/40 backdrop-blur-sm transition-opacity duration-300"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* AI Drawer — Professional Glassmorphism Style */}
      <div
        className={cn(
          "fixed inset-y-0 end-0 z-50",
          "w-full sm:w-[500px] lg:w-[540px]",
          "bg-gradient-to-br from-card/95 via-card/90 to-card/85",
          "border border-border/40 backdrop-blur-xl",
          "shadow-2xl",
          "flex flex-col",
          "transition-transform duration-300 ease-in-out",
          isOpen ? "translate-x-0" : "translate-x-full"
        )}
        role="dialog"
        aria-modal="true"
        aria-label="AMAD AI Assistant"
      >
        {/* Header — Professional Design */}
        <div className="shrink-0 border-b border-border/40 px-6 py-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary/30 to-primary/10 flex items-center justify-center border border-primary/30">
              <Zap className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-foreground">{t("AMAD AI")}</h2>
              <p className="text-xs text-muted-foreground">Enterprise Intelligence</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-muted/50 rounded-lg transition-all duration-200 text-foreground/60 hover:text-foreground"
            aria-label={t("Close")}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto">
          {!activeWorkspace ? (
            // AI Home Screen
            <div className="p-6 space-y-6">
              {/* Welcome Message */}
              <div className="space-y-2">
                <h3 className="text-xl font-semibold text-foreground">Good morning</h3>
                <p className="text-sm text-muted-foreground">How can AMAD AI help you today?</p>
              </div>

              {/* AI Capability Cards */}
              <div className="grid grid-cols-1 gap-3 space-y-3">
                {AI_HOME_CARDS.map((card) => (
                  <button
                    key={card.id}
                    onClick={() => setActiveWorkspace(card.id)}
                    className={cn(
                      "group relative p-4 rounded-xl border",
                      "bg-gradient-to-br transition-all duration-300",
                      "hover:shadow-lg hover:border-primary/50",
                      "text-start overflow-hidden",
                      card.color
                    )}
                  >
                    {/* Background gradient overlay */}
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

                    {/* Content */}
                    <div className="relative flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-2">
                          <div className="flex-shrink-0 text-primary group-hover:scale-110 transition-transform">
                            {card.icon}
                          </div>
                          <h4 className="font-semibold text-foreground text-sm group-hover:text-primary transition-colors">
                            {t(card.nameKey)}
                          </h4>
                        </div>
                        <p className="text-xs text-muted-foreground line-clamp-2">
                          {t(card.descriptionKey)}
                        </p>
                      </div>
                      <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all flex-shrink-0 ms-2 mt-1" />
                    </div>
                  </button>
                ))}
              </div>

              {/* Footer Info */}
              <div className="rounded-lg bg-muted/30 border border-border/40 p-3 mt-6">
                <p className="text-xs text-muted-foreground text-center">
                  {t("AI features are being developed. Click a card to preview the workspace.")}
                </p>
              </div>
            </div>
          ) : (
            // Workspace View (Placeholder)
            <div className="p-6 space-y-6">
              <button
                onClick={handleBackToHome}
                className="text-sm text-primary hover:text-primary/80 font-medium flex items-center gap-2 mb-4"
              >
                ← {t("Back to AMAD AI")}
              </button>

              <div className="space-y-4">
                <h3 className="text-xl font-semibold text-foreground">
                  {t(
                    AI_HOME_CARDS.find((c) => c.id === activeWorkspace)?.nameKey || "Workspace"
                  )}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {t(AI_HOME_CARDS.find((c) => c.id === activeWorkspace)?.descriptionKey || "")}
                </p>
              </div>

              <div className="rounded-lg bg-muted/20 border border-dashed border-border/50 p-8 text-center">
                <MessageSquare className="w-8 h-8 text-muted-foreground/40 mx-auto mb-3" />
                <p className="text-sm text-muted-foreground">
                  Workspace content coming soon...
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
