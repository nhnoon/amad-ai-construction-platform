import { ReactNode, useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { useLocation } from "wouter";
import { LogoMark } from "./LogoMark";
import { FloatingAIButton } from "./FloatingAIButton";
import { ErrorBoundary } from "./ErrorBoundary";
import { SidebarItem } from "./sidebar-item";
import {
  LayoutDashboard,
  Briefcase,
  ShoppingCart,
  ClipboardCheck,
  CalendarDays,
  HelpCircle,
  AlertCircle,
  TrendingUp,
  ShieldAlert,
  Users,
  LogOut,
  Globe,
  Sun,
  Moon,
  Menu,
  X,
  UserCog,
  Folder,
  BarChart3,
  Settings,
  Bot,
  Brain,
  Building2,
  ClipboardList,
  FileSignature,
  LineChart,
  LayoutGrid,
  PanelLeftClose,
  PanelLeftOpen,
  ListChecks,
  FileCheck2,
  Bell,
  BellRing,
  AlertTriangle,
  Search,
  Mail,
  History,
  Plug,
  CreditCard,
  Handshake,
  Inbox,
  FolderOpen,
  Network,
  Gauge,
  Truck,
  Boxes,
  BookOpen,
  Crown,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { useGetNotificationsSummary } from "@workspace/api-client-react";
import { getToken } from "../lib/auth";

// ── Enterprise SaaS navigation (GitHub / Azure DevOps / Jira / Linear /
// Notion / Monday.com style): one collapsible left sidebar, sectioned as an
// accordion — only one group open at a time, so the list stays short and
// scannable instead of showing every destination in every group at once.
// Section headers are toggles; opening a group auto-collapses the others,
// and navigating into a group's page auto-opens it and closes the rest.
// "Operations" and "AI Center" are workspace groups; selecting a child
// routes straight to its real dedicated page — the sidebar is the only
// navigation surface in the app (no duplicate menus inside page content).

type NavItem = {
  key: string;
  href: string;
  icon: typeof LayoutDashboard;
  label: string;
  /** Presentational-only sub-cluster label within a large section (e.g. AI
   * Center's 16 items) — purely visual grouping to aid scanning, not a
   * route or a new collapsible state. Rendered as a small divider label
   * whenever it differs from the previous item's subgroup. */
  subgroup?: string;
};
// `icon` is required on titled (expandable) sections — the group header row
// renders through the same SidebarItem as every link, so it needs an icon
// just like any other nav row does.
type NavSection = { title: string | null; icon?: typeof LayoutDashboard; items: NavItem[] };

// Top, unlabeled — mirrors the ticket's own example ("Overview" sits alone
// before the first divider). Kept as "Dashboard" (not renamed to
// "Overview") since that's the app's own consistent, already-established
// name for this page everywhere else (page title, breadcrumbs, h1).
const NAV_SECTIONS: NavSection[] = [
  {
    title: null,
    items: [
      { key: "Dashboard", href: "/", icon: LayoutDashboard, label: "Dashboard" },
      { key: "Documents", href: "/documents", icon: Folder, label: "Documents" },
    ],
  },
  {
    title: "My Workspace",
    icon: Inbox,
    items: [
      // Employee & Project Workspace (product vision, Phase 2) — personal,
      // cross-project surfaces rather than the project-catalog views that
      // live under "Operations" below.
      { key: "Tasks", href: "/tasks", icon: ListChecks, label: "Tasks" },
      { key: "Requests & Approvals", href: "/requests", icon: FileCheck2, label: "Requests & Approvals" },
      // Alerts is a real, working page (see alerts.tsx / /api/v1/alerts) —
      // it previously had a live route with no sidebar entry pointing at
      // it, making it unreachable from navigation.
      { key: "Alerts", href: "/alerts", icon: Bell, label: "Alerts" },
      { key: "Notifications", href: "/notifications", icon: BellRing, label: "Notifications" },
    ],
  },
  {
    title: "Operations",
    icon: Building2,
    items: [
      // "Overview" first, mirroring AI Center's own pattern below — without
      // it, /operations (a real route rendering a real workspace) had no
      // link pointing at it anywhere in the sidebar and was unreachable.
      { key: "Operations Overview", href: "/operations", icon: LayoutGrid, label: "Overview" },
      { key: "Projects", href: "/projects", icon: Briefcase, label: "Projects" },
      { key: "Procurement", href: "/procurement", icon: ShoppingCart, label: "Procurement" },
      { key: "Site Reports", href: "/site-reports", icon: ClipboardCheck, label: "Site Reports" },
      { key: "Meetings", href: "/meetings", icon: CalendarDays, label: "Meetings" },
      { key: "RFIs", href: "/rfis", icon: HelpCircle, label: "RFIs" },
      { key: "Change Orders", href: "/change-orders", icon: AlertCircle, label: "Change Orders" },
      { key: "Claims", href: "/claims", icon: TrendingUp, label: "Claims" },
      { key: "Suppliers", href: "/suppliers", icon: Users, label: "Suppliers" },
      { key: "Safety", href: "/safety", icon: ShieldAlert, label: "Safety" },
      { key: "Risk Register", href: "/risks", icon: AlertTriangle, label: "Risk Register" },
    ],
  },
  {
    title: "AI Center",
    icon: Bot,
    items: [
      // "Overview" kept in addition to the ticket's own 7-item example —
      // it's a real, useful landing page from the Phase 1 workspace build;
      // dropping it would remove working navigation, not add it.
      { key: "AI Overview", href: "/ai-center", icon: LayoutGrid, label: "Overview", subgroup: "Workspace" },
      { key: "AI Copilot", href: "/ai-center/copilot", icon: Bot, label: "AI Copilot", subgroup: "Workspace" },
      { key: "Memory Center", href: "/ai-center/memory", icon: Brain, label: "Memory Center", subgroup: "Workspace" },
      { key: "Project Intelligence", href: "/ai-center/projects", icon: Building2, label: "Project Intelligence", subgroup: "Per-Entity Intelligence" },
      { key: "Site Report Intelligence", href: "/ai-center/site-reports", icon: ClipboardList, label: "Site Report Intelligence", subgroup: "Per-Entity Intelligence" },
      { key: "Meeting Intelligence", href: "/ai-center/meetings", icon: CalendarDays, label: "Meeting Intelligence", subgroup: "Per-Entity Intelligence" },
      { key: "Contract Intelligence", href: "/ai-center/contracts", icon: FileSignature, label: "Contract Intelligence", subgroup: "Per-Entity Intelligence" },
      { key: "Executive Intelligence", href: "/ai-center/executive", icon: LineChart, label: "Executive Intelligence", subgroup: "Per-Entity Intelligence" },
      { key: "Intelligent Search", href: "/ai-center/search", icon: Search, label: "Intelligent Search", subgroup: "Per-Entity Intelligence" },
      { key: "Email Intelligence", href: "/ai-center/email", icon: Mail, label: "Email Intelligence", subgroup: "Per-Entity Intelligence" },
      { key: "Project Memory", href: "/ai-center/project-memory", icon: Network, label: "Project Memory", subgroup: "Flagship Modules" },
      { key: "Predictive Intelligence", href: "/ai-center/predictive-intelligence", icon: Gauge, label: "Predictive Intelligence", subgroup: "Flagship Modules" },
      { key: "Supplier Risk Intelligence", href: "/ai-center/supplier-risk", icon: Truck, label: "Supplier Risk Intelligence", subgroup: "Flagship Modules" },
      { key: "Material Intelligence", href: "/ai-center/material-intelligence", icon: Boxes, label: "Material Intelligence", subgroup: "Flagship Modules" },
      { key: "Cross-Project Learning", href: "/ai-center/cross-project-learning", icon: BookOpen, label: "Cross-Project Learning", subgroup: "Flagship Modules" },
      { key: "Executive Decision Center", href: "/ai-center/executive-decision-center", icon: Crown, label: "Executive Decision Center", subgroup: "Flagship Modules" },
    ],
  },
  {
    title: "Analytics",
    icon: BarChart3,
    items: [
      { key: "Reports", href: "/reports", icon: BarChart3, label: "Reports" },
      // Cross-listed, not duplicated: Insights points at the real
      // Executive Intelligence workspace, which has genuinely distinct
      // content (risk/insight cards) from anything else already in this
      // group — a second, sensible entry point, not a dead or fake link.
      { key: "Insights", href: "/ai-center/executive", icon: LineChart, label: "Insights" },
    ],
  },
  {
    title: "Client Portal",
    icon: Handshake,
    items: [
      // Product vision "Future Client Portal" (Phase 4, planned) — every
      // page here is a roadmap placeholder, not live client-facing
      // functionality; kept as its own group so the planned surface area
      // is visible in navigation rather than only in a slide deck.
      { key: "Client Portal Overview", href: "/client-portal", icon: LayoutGrid, label: "Overview" },
      { key: "Client Requests", href: "/client-portal/requests", icon: Inbox, label: "Requests" },
      { key: "Client Documents", href: "/client-portal/documents", icon: FolderOpen, label: "Documents" },
    ],
  },
];

// Administration deliberately does NOT include a "Roles" entry: role
// assignment and filtering already live entirely inside the Users page
// (see admin-users.tsx) — there is no distinct Roles page to link to, and
// linking "Roles" to the exact same URL as "Users" would just show the
// identical screen under a second label, which reads as a mistake rather
// than a real destination. Omitted rather than faked.
const ADMIN_SECTION: NavSection = {
  title: "Administration",
  icon: Settings,
  items: [
    { key: "Admin Users", href: "/admin/users", icon: UserCog, label: "Users" },
    { key: "Admin Settings", href: "/admin/organization", icon: Settings, label: "Settings" },
    { key: "Audit Log", href: "/admin/audit-log", icon: History, label: "Audit Log" },
    { key: "Integrations", href: "/admin/integrations", icon: Plug, label: "Integrations" },
    { key: "Billing", href: "/admin/billing", icon: CreditCard, label: "Billing & Subscription" },
  ],
};

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

function matchesHref(location: string, href: string): boolean {
  return location === href || (href !== "/" && location.startsWith(href));
}

// Which titled group (if any) owns the current route — drives the
// accordion's auto-expand-active/collapse-rest behavior on navigation.
function findActiveGroupKey(location: string, sections: NavSection[]): string | null {
  for (const section of sections) {
    if (!section.title) continue;
    if (section.items.some((item) => matchesHref(location, item.href))) return section.title;
  }
  return null;
}

function getPageTitle(location: string, sections: NavSection[], t: (k: string) => string): string {
  if (location === "/") return t("Dashboard");
  for (const section of sections) {
    const item = section.items.find((i) => i.href !== "/" && matchesHref(location, i.href));
    if (item) return section.title ? `${t(section.title)} · ${t(item.key)}` : t(item.key);
  }
  return "";
}

const COLLAPSE_STORAGE_KEY = "amad_sidebar_collapsed";

export function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [location] = useLocation();
  const { t, i18n } = useTranslation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => {
    try { return window.localStorage.getItem(COLLAPSE_STORAGE_KEY) === "1"; } catch { return false; }
  });

  const isAdmin = user?.role === "admin";
  const allSections = isAdmin ? [...NAV_SECTIONS, ADMIN_SECTION] : NAV_SECTIONS;

  // Accordion: only one titled group open at a time. Default is all
  // collapsed; opening a group (or navigating into one of its pages)
  // collapses every other group.
  const [expandedGroup, setExpandedGroup] = useState<string | null>(null);

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      try { window.localStorage.setItem(COLLAPSE_STORAGE_KEY, next ? "1" : "0"); } catch { /* ignore */ }
      return next;
    });
  };

  const handleGroupClick = (title: string) => {
    setExpandedGroup((prev) => (prev === title ? null : title));
  };

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
  void alertsSummary; // reserved for a future nav badge — not rendered yet, kept fetched so it's ready without a second wiring pass

  const { data: notificationsSummary } = useGetNotificationsSummary({
    query: { queryKey: ["notifications-summary-badge"], enabled: !!token, staleTime: 30_000, refetchInterval: 60_000 },
  });
  const unreadNotifications = notificationsSummary?.unread_count ?? 0;

  const isRtl = i18n.language === "ar";

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

  useEffect(() => {
    setSidebarOpen(false);
  }, [location]);

  useEffect(() => {
    const activeGroup = findActiveGroupKey(location, isAdmin ? [...NAV_SECTIONS, ADMIN_SECTION] : NAV_SECTIONS);
    if (activeGroup) setExpandedGroup(activeGroup);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location, isAdmin]);

  const pageTitle = getPageTitle(location, allSections, t);

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

  const sidebarHiddenClass = isRtl ? "translate-x-full" : "-translate-x-full";
  const sidebarWidth = collapsed ? "md:w-[64px]" : "md:w-[220px]";

  return (
    <div className="min-h-screen flex w-full bg-background">

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
          fixed inset-y-0 start-0 z-50 w-64 ${sidebarWidth}
          bg-sidebar text-sidebar-foreground flex flex-col
          border-e border-sidebar-border shadow-2xl
          transition-[transform,width] duration-200 ease-in-out
          md:relative md:translate-x-0 md:shrink-0
          ${sidebarOpen ? "translate-x-0" : sidebarHiddenClass}
        `}
        aria-label="Navigation sidebar"
      >
        {/* Brand */}
        <div className={`px-3 py-4 border-b border-sidebar-border flex items-center ${collapsed ? "md:justify-center" : "justify-between"} gap-2`}>
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-9 h-9 rounded-lg bg-sidebar-primary flex items-center justify-center shrink-0 shadow-inner ring-1 ring-sidebar-primary/40">
              <LogoMark className="w-5 h-5 text-sidebar-primary-foreground" />
            </div>
            {!collapsed && (
              <div className="min-w-0 hidden md:block">
                <p className="font-bold text-sidebar-foreground text-sm leading-tight tracking-wide truncate">Amad</p>
                <p className="text-[9px] text-sidebar-foreground/50 uppercase tracking-[0.13em] leading-tight mt-0.5 truncate">
                  {t("Command Center")}
                </p>
              </div>
            )}
            <div className="min-w-0 md:hidden">
              <p className="font-bold text-sidebar-foreground text-sm leading-tight tracking-wide truncate">Amad</p>
            </div>
          </div>
          <button
            onClick={toggleCollapsed}
            className="hidden md:flex items-center justify-center w-6 h-6 rounded-md text-sidebar-foreground/40 hover:text-sidebar-foreground hover:bg-sidebar-accent/50 transition-colors shrink-0"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <PanelLeftOpen className="w-3.5 h-3.5" /> : <PanelLeftClose className="w-3.5 h-3.5" />}
          </button>
        </div>

        {/* Nav — accordion sectioned list. Only one titled group is open at
            a time; the untitled top group (Dashboard/Documents) always
            shows. Every row here — plain link, group header, or nested
            child link — renders through the same SidebarItem, so the whole
            list is one visual system: group headers are just a nav row
            with a trailing chevron instead of an href, and child rows are
            the same row with extra start indent. */}
        <nav className="flex-1 py-2 px-2 space-y-0.5 overflow-y-auto overflow-x-hidden">
          {allSections.map((section, si) => {
            const isTop = !section.title;
            const isExpanded = collapsed || isTop || expandedGroup === section.title;
            return (
              <div key={section.title ?? `top-${si}`} className={isTop ? "pb-1 mb-1 border-b border-sidebar-border/50" : ""}>
                {section.title && !collapsed && (
                  <SidebarItem
                    icon={section.icon!}
                    label={t(section.title)}
                    onClick={() => handleGroupClick(section.title!)}
                    expanded={isExpanded}
                    testId={`nav-group-${section.title.toLowerCase().replace(/[^a-z0-9]/g, "-")}`}
                  />
                )}
                {section.title && collapsed && si > 0 && (
                  <div className="mx-2 mb-1.5 border-t border-sidebar-border/60" />
                )}
                {section.title && !collapsed ? (
                  <div
                    className="grid transition-[grid-template-rows] duration-200 ease-out"
                    style={{ gridTemplateRows: isExpanded ? "1fr" : "0fr" }}
                  >
                    <div className="overflow-hidden">
                      <div className="space-y-0.5 pt-0.5">
                        {section.items.map((item, ii) => (
                          <div key={item.key}>
                            {item.subgroup && item.subgroup !== section.items[ii - 1]?.subgroup && (
                              <p className="px-3 pt-2.5 pb-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-sidebar-foreground/35">
                                {t(item.subgroup)}
                              </p>
                            )}
                            <SidebarItem
                              icon={item.icon}
                              label={t(item.label)}
                              href={item.href}
                              active={matchesHref(location, item.href)}
                              indent
                              testId={`nav-${item.key.toLowerCase().replace(/[^a-z0-9]/g, "-")}`}
                              badgeCount={item.key === "Notifications" ? unreadNotifications : undefined}
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : isExpanded ? (
                  <div className="space-y-0.5">
                    {section.items.map((item) => (
                      <SidebarItem
                        key={item.key}
                        icon={item.icon}
                        label={t(item.label)}
                        href={item.href}
                        active={matchesHref(location, item.href)}
                        collapsed={collapsed}
                        testId={`nav-${item.key.toLowerCase().replace(/[^a-z0-9]/g, "-")}`}
                        badgeCount={item.key === "Notifications" ? unreadNotifications : undefined}
                      />
                    ))}
                  </div>
                ) : null}
              </div>
            );
          })}
        </nav>

        {/* Bottom: user + controls */}
        <div className="p-2 border-t border-sidebar-border space-y-1">
          <div className={`flex items-center gap-2.5 px-2 py-2 rounded-lg bg-sidebar-accent/40 border border-sidebar-border/60 ${collapsed ? "md:justify-center" : ""}`}>
            <div className="w-7 h-7 rounded-full bg-sidebar-primary flex items-center justify-center text-sidebar-primary-foreground font-bold text-[11px] shrink-0 ring-1 ring-sidebar-primary/30">
              {initials}
            </div>
            {!collapsed && (
              <div className="flex-1 min-w-0 hidden md:block">
                <p className="text-xs font-semibold text-sidebar-foreground truncate leading-tight">
                  {user?.full_name || user?.email}
                </p>
                <p className="text-[10px] text-sidebar-foreground/50 truncate leading-tight mt-0.5">
                  {roleLabel}
                </p>
              </div>
            )}
            <div className="flex-1 min-w-0 md:hidden">
              <p className="text-xs font-semibold text-sidebar-foreground truncate leading-tight">
                {user?.full_name || user?.email}
              </p>
            </div>
          </div>

          <div className={`flex gap-1 pt-1 ${collapsed ? "md:flex-col" : ""}`}>
            <button
              onClick={toggleTheme}
              className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md text-xs font-medium text-sidebar-foreground/60 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground transition-colors ${collapsed ? "md:flex-none" : ""}`}
              data-testid="button-theme-toggle"
              aria-label={theme === "dark" ? t("Light Mode") : t("Dark Mode")}
              title={theme === "dark" ? t("Light Mode") : t("Dark Mode")}
            >
              {theme === "dark" ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
              <span className={collapsed ? "md:hidden" : ""}>{theme === "dark" ? t("Light Mode") : t("Dark Mode")}</span>
            </button>

            <button
              onClick={toggleLanguage}
              className="flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md text-xs font-medium text-sidebar-foreground/60 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground transition-colors"
              data-testid="button-language-toggle"
              aria-label="Switch language"
            >
              <Globe className="w-3.5 h-3.5" />
              <span className={collapsed ? "md:hidden" : ""}>{i18n.language === "en" ? "AR" : "EN"}</span>
            </button>
          </div>

          <button
            onClick={() => logout()}
            className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-xs font-medium text-sidebar-foreground/50 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground transition-colors ${collapsed ? "md:justify-center" : ""}`}
            data-testid="button-logout"
          >
            <LogOut className="w-3.5 h-3.5 shrink-0" />
            <span className={collapsed ? "md:hidden" : ""}>{t("Sign Out")}</span>
          </button>
        </div>
      </aside>

      {/* ── Main area ────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar — a minimal utility bar only (mobile nav toggle, role
            badges, avatar). The page title/breadcrumb is NOT repeated here:
            every page already renders its own via PageContextHeader
            directly below, and showing it twice was the exact "Dashboard /
            Executive Dashboard / Dashboard" duplication this bar used to
            produce on every single page, not just the Dashboard. */}
        <header className="h-12 shrink-0 bg-card/80 border-b border-border backdrop-blur-sm flex items-center justify-between px-4 md:px-5 sticky top-0 z-10">
          <button
            className="md:hidden flex items-center justify-center w-8 h-8 rounded-lg hover:bg-muted transition-colors shrink-0"
            onClick={() => setSidebarOpen((prev) => !prev)}
            aria-label="Toggle navigation menu"
            aria-expanded={sidebarOpen}
          >
            {sidebarOpen ? <X className="w-4 h-4 text-foreground" /> : <Menu className="w-4 h-4 text-foreground" />}
          </button>
          <div className="flex items-center gap-2 shrink-0 ms-auto">
            {isAdmin && (
              <span className="hidden sm:inline text-[11px] font-medium px-2 py-0.5 rounded-full bg-[#C8953A]/10 text-[#C8953A] border border-[#C8953A]/20">
                Admin
              </span>
            )}
            <span className="hidden sm:inline text-[11px] font-medium px-2 py-0.5 rounded-full bg-accent/15 text-accent">
              {roleLabel}
            </span>
            <div className="w-7 h-7 rounded-full bg-primary flex items-center justify-center text-primary-foreground font-bold text-[11px]">
              {initials}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto">
          <div className="p-4 md:p-5 lg:p-6 max-w-screen-2xl mx-auto">
            {children}
          </div>
        </main>
      </div>

      <ErrorBoundary silent>
        <FloatingAIButton />
      </ErrorBoundary>
    </div>
  );
}
