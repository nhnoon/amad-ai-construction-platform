import { ReactNode, useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { Link, useLocation } from "wouter";
import { LogoMark } from "./LogoMark";
import { FloatingAIButton } from "./FloatingAIButton";
import { ErrorBoundary } from "./ErrorBoundary";
import {
  LayoutDashboard,
  Briefcase,
  ShoppingCart,
  Users,
  ClipboardCheck,
  ShieldAlert,
  CalendarDays,
  LogOut,
  Globe,
  Sun,
  Moon,
  Menu,
  X,
  UserCog,
  Building2,
  Bell,
  FileText,
  Folder,
  BarChart3,
  Settings,
  Sparkles,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { getToken } from "../lib/auth";

// Main sidebar navigation - Professional Enterprise Layout
const NAV_ITEMS = [
  { key: "Dashboard", href: "/", icon: LayoutDashboard, label: "Dashboard" },
  { key: "Operations", href: "/operations", icon: Briefcase, label: "Operations" },
  { key: "Documents", href: "/documents", icon: Folder, label: "Documents" },
  { key: "AI Center", href: "/ai-center", icon: Sparkles, label: "AI Center" },
  { key: "Reports", href: "/reports", icon: BarChart3, label: "Reports" },
];

const ADMIN_NAV_ITEMS = [
  { key: "Administration", href: "/admin", icon: Settings, label: "Administration" },
];

const ROLE_LABELS: Record<string, string> = {
  admin: "Administrator",
  executive: "Executive",
  project_manager: "Project Manager",
  site_engineer: "Site Engineer",
  procurement_officer: "Procurement Officer",
  safety_quality_officer: "Safety Officer",
  viewer: "Viewer",
};

const ROLE_LABELS_AR: Record<string, string> = {
  admin: "مدير النظام",
  executive: "مسؤول تنفيذي",
  project_manager: "مدير مشروع",
  site_engineer: "مهندس موقع",
  procurement_officer: "مسؤول المشتريات",
  safety_quality_officer: "مسؤول السلامة",
  viewer: "مراقب",
};

function getRoleLabel(role: string | undefined, lang: string): string {
  if (!role) return "";
  return lang === "ar"
    ? (ROLE_LABELS_AR[role] ?? role)
    : (ROLE_LABELS[role] ?? role);
}

function getPageTitle(
  location: string,
  t: (k: string) => string
): string {
  if (location === "/") return t("Dashboard");
  const all = [...NAV_ITEMS, ...ADMIN_NAV_ITEMS];
  const item = all.find(
    (n) => n.href !== "/" && location.startsWith(n.href)
  );
  return item ? t(item.key) : "";
}

export function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [location] = useLocation();
  const { t, i18n } = useTranslation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const token = getToken();
  const { data: alertsSummary } = useQuery({
    queryKey: ["alerts-summary-badge"],
    queryFn: async () => {
      const resp = await fetch("/api/v1/alerts/summary", {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!resp.ok) return null;
      return resp.json() as Promise<{ critical: number; high: number }>;
    },
    enabled: !!token,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
  const alertBadgeCount = (alertsSummary?.critical ?? 0) + (alertsSummary?.high ?? 0);

  const isRtl = i18n.language === "ar";
  const isAdmin = user?.role === "admin";

  const toggleLanguage = () => {
    const newLang = i18n.language === "en" ? "ar" : "en";
    i18n.changeLanguage(newLang);
    document.documentElement.dir = newLang === "ar" ? "rtl" : "ltr";
    document.documentElement.lang = newLang;
    localStorage.setItem("language", newLang);
  };

  useEffect(() => {
    document.documentElement.dir = isRtl ? "rtl" : "ltr";
    document.documentElement.lang = i18n.language;
  }, [i18n.language, isRtl]);

  // Close sidebar when navigating (mobile)
  useEffect(() => {
    setSidebarOpen(false);
  }, [location]);

  const pageTitle = getPageTitle(location, t);

  // Keep the browser tab title in sync with the current section so users
  // with several tabs open (or browsing history) can tell pages apart.
  // Routes not covered by the sidebar nav (detail pages, admin sub-pages,
  // etc.) fall back to the static app title set in index.html.
  useEffect(() => {
    document.title = pageTitle ? `${pageTitle} · Amad` : "Amad — Construction Intelligence";
  }, [pageTitle]);

  const roleLabel = getRoleLabel(user?.role, i18n.language);
  const initials = (user?.full_name ?? user?.email ?? "U")
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  // In RTL the sidebar is on the right — slide out direction is reversed
  const sidebarHiddenClass = isRtl ? "translate-x-full" : "-translate-x-full";

  return (
    <div className="min-h-screen flex w-full bg-background">

      {/* Mobile backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* ── Sidebar ─────────────────────────────────────────── */}
      <aside
        className={`
          fixed inset-y-0 start-0 z-50 w-64
          bg-sidebar text-sidebar-foreground flex flex-col
          border-e border-sidebar-border shadow-2xl
          transition-transform duration-300 ease-in-out
          md:relative md:translate-x-0 md:shrink-0
          ${sidebarOpen ? "translate-x-0" : sidebarHiddenClass}
        `}
        aria-label="Navigation sidebar"
      >
        {/* Brand */}
        <div className="px-5 py-5 border-b border-sidebar-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-sidebar-primary flex items-center justify-center shrink-0 shadow-inner">
              <LogoMark className="w-6 h-6 text-sidebar-primary-foreground" />
            </div>
            <div className="min-w-0">
              <p className="font-bold text-sidebar-foreground text-base leading-tight tracking-wide">
                Amad
              </p>
              <p className="text-[10px] text-sidebar-foreground/50 uppercase tracking-[0.15em] leading-tight mt-0.5 truncate">
                {t("Command Center")}
              </p>
            </div>
          </div>
        </div>

        {/* Nav — Professional Enterprise Layout */}
        <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {/* Main navigation items */}
          {NAV_ITEMS.map((item) => {
            const isActive =
              location === item.href ||
              (item.href !== "/" && location.startsWith(item.href));
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group
                  ${
                    isActive
                      ? "bg-sidebar-primary/15 text-sidebar-primary border-s-2 border-sidebar-primary ps-[10px]"
                      : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground border-s-2 border-transparent ps-[10px]"
                  }`}
                data-testid={`nav-${item.key.toLowerCase().replace(/[^a-z0-9]/g, "-")}`}
              >
                <Icon
                  className={`w-5 h-5 shrink-0 transition-colors ${isActive ? "text-sidebar-primary" : "text-sidebar-foreground/50 group-hover:text-sidebar-accent-foreground"}`}
                />
                <span className="flex-1">{t(item.key)}</span>
              </Link>
            );
          })}

          {/* Admin section — visible to admin role only */}
          {isAdmin && (
            <>
              <div className="pt-3 pb-2 px-3 mt-2 border-t border-sidebar-border/50">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-sidebar-foreground/40">
                  {t("Settings")}
                </p>
              </div>
              {ADMIN_NAV_ITEMS.map((item) => {
                const isActive = location.startsWith(item.href);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group
                      ${
                        isActive
                          ? "bg-sidebar-primary/15 text-sidebar-primary border-s-2 border-sidebar-primary ps-[10px]"
                          : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground border-s-2 border-transparent ps-[10px]"
                      }`}
                    data-testid={`nav-${item.key.toLowerCase().replace(/[^a-z0-9]/g, "-")}`}
                  >
                    <Icon
                      className={`w-5 h-5 shrink-0 transition-colors ${isActive ? "text-sidebar-primary" : "text-sidebar-foreground/50 group-hover:text-sidebar-accent-foreground"}`}
                    />
                    <span className="flex-1">{t(item.key)}</span>
                  </Link>
                );
              })}
            </>
          )}
        </nav>

        {/* Bottom: user + controls */}
        <div className="p-3 border-t border-sidebar-border space-y-1">
          {/* User row */}
          <div className="flex items-center gap-3 px-2 py-2 rounded-lg bg-sidebar-accent/40">
            <div className="w-8 h-8 rounded-full bg-sidebar-primary flex items-center justify-center text-sidebar-primary-foreground font-bold text-xs shrink-0">
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-sidebar-foreground truncate leading-tight">
                {user?.full_name || user?.email}
              </p>
              <p className="text-[11px] text-sidebar-foreground/50 truncate leading-tight mt-0.5">
                {roleLabel}
              </p>
            </div>
          </div>

          {/* Controls row */}
          <div className="flex gap-1 pt-1">
            {/* Theme toggle */}
            <button
              onClick={toggleTheme}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium text-sidebar-foreground/60 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground transition-colors"
              data-testid="button-theme-toggle"
              aria-label={theme === "dark" ? t("Light Mode") : t("Dark Mode")}
              title={theme === "dark" ? t("Light Mode") : t("Dark Mode")}
            >
              {theme === "dark" ? (
                <Sun className="w-4 h-4" />
              ) : (
                <Moon className="w-4 h-4" />
              )}
              <span>{theme === "dark" ? t("Light Mode") : t("Dark Mode")}</span>
            </button>

            {/* Language toggle */}
            <button
              onClick={toggleLanguage}
              className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium text-sidebar-foreground/60 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground transition-colors"
              data-testid="button-language-toggle"
              aria-label="Switch language"
            >
              <Globe className="w-4 h-4" />
              <span>{i18n.language === "en" ? "AR" : "EN"}</span>
            </button>
          </div>

          {/* Sign out */}
          <button
            onClick={() => logout()}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium text-sidebar-foreground/50 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground transition-colors"
            data-testid="button-logout"
          >
            <LogOut className="w-4 h-4" />
            <span>{t("Sign Out")}</span>
          </button>
        </div>
      </aside>

      {/* ── Main area ────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar */}
        <header className="h-14 shrink-0 bg-card/80 border-b border-border backdrop-blur-sm flex items-center justify-between px-4 md:px-6 sticky top-0 z-10">
          <div className="flex items-center gap-3 min-w-0">
            {/* Hamburger — mobile only */}
            <button
              className="md:hidden flex items-center justify-center w-9 h-9 rounded-lg hover:bg-muted transition-colors shrink-0"
              onClick={() => setSidebarOpen((prev) => !prev)}
              aria-label="Toggle navigation menu"
              aria-expanded={sidebarOpen}
            >
              {sidebarOpen ? (
                <X className="w-5 h-5 text-foreground" />
              ) : (
                <Menu className="w-5 h-5 text-foreground" />
              )}
            </button>

            {pageTitle && (
              <h2 className="text-sm font-semibold text-foreground truncate">
                {pageTitle}
              </h2>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {isAdmin && (
              <span className="hidden sm:inline text-xs font-medium px-2.5 py-1 rounded-full bg-[#C8953A]/10 text-[#C8953A] border border-[#C8953A]/20">
                Admin
              </span>
            )}
            <span className="hidden sm:inline text-xs font-medium px-2.5 py-1 rounded-full bg-accent/15 text-accent">
              {roleLabel}
            </span>
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground font-bold text-xs">
              {initials}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto">
          <div className="p-4 md:p-6 lg:p-8 max-w-screen-2xl mx-auto">
            {children}
          </div>
        </main>
      </div>

      {/* Floating AI Button — appears on all authenticated pages. Isolated in
          its own boundary so a crash inside the drawer can never take down
          the sidebar or main content; falls back to "not rendered" rather
          than an error card since it's a fixed-position overlay, not
          in-flow content, and Copilot is still reachable via the sidebar
          and /copilot directly if this fails. */}
      <ErrorBoundary silent>
        <FloatingAIButton />
      </ErrorBoundary>
    </div>
  );
}
