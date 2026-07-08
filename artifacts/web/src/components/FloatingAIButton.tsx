import { useState } from "react";
import { Zap, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { AIDrawer } from "./AIDrawer";

export function FloatingAIButton() {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  return (
    <>
      {/* Floating AI Button — Professional Glassmorphism */}
      <button
        onClick={() => setIsDrawerOpen(true)}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        className={cn(
          "fixed bottom-6 right-6 z-40",
          "group",
          "transition-all duration-300 ease-out"
        )}
        aria-label="Open AMAD AI Assistant"
        title="AMAD AI Assistant"
      >
        {/* Button background — Glassmorphism effect */}
        <div
          className={cn(
            "absolute inset-0 rounded-full",
            "bg-gradient-to-br from-primary/40 via-primary/30 to-primary/20",
            "backdrop-blur-xl border border-primary/30",
            "shadow-xl shadow-primary/20",
            "group-hover:from-primary/50 group-hover:via-primary/40 group-hover:to-primary/30",
            "group-hover:shadow-2xl group-hover:shadow-primary/30",
            "group-hover:border-primary/50",
            isDrawerOpen ? "scale-95" : "scale-100",
            "transition-all duration-200"
          )}
        />

        {/* Icon wrapper */}
        <div className="relative w-14 h-14 flex items-center justify-center">
          <Zap
            className={cn(
              "w-6 h-6 text-white/90 transition-all duration-300",
              "group-hover:scale-110 group-hover:text-white",
              isDrawerOpen ? "opacity-0" : "opacity-100"
            )}
          />
        </div>

        {/* Subtle pulse animation */}
        <div
          className={cn(
            "absolute inset-0 rounded-full",
            "bg-primary/20 animate-pulse",
            "group-hover:animate-none"
          )}
        />
      </button>

      {/* AI Drawer */}
      <AIDrawer isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)} />
    </>
  );
}
