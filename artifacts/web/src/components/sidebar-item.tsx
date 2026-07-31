import type { ElementType } from "react";
import { Link } from "wouter";
import { ChevronRight } from "lucide-react";

// The one navigation-row component used for every entry in the app sidebar —
// top-level links (Dashboard, Documents), expandable group headers
// (Operations, AI Center, Analytics, Administration), and their child links.
// Previously each of those three roles had its own hand-rolled markup: plain
// links used one padding/active treatment, group headers rendered as a small
// uppercase label with no icon, and children used yet another padding/active
// treatment. That made the sidebar read as three different visual systems.
// This component is the single shared row — every level of the nav has the
// same height, padding, typography, icon size, hover/selected state, and
// animation, differing only by indentation (child rows) and an optional
// trailing chevron (group headers).

type SidebarItemBaseProps = {
  icon: ElementType;
  label: string;
  active?: boolean;
  /** Sidebar collapsed to an icon-only rail (desktop only). */
  collapsed?: boolean;
  /** Child row nested under an expanded group — same row, extra start padding. */
  indent?: boolean;
  testId?: string;
};

type SidebarItemProps =
  | (SidebarItemBaseProps & {
      href: string;
      onClick?: undefined;
      expanded?: undefined;
    })
  | (SidebarItemBaseProps & {
      href?: undefined;
      onClick: () => void;
      /** Marks this row as an expandable group header and renders the trailing chevron. */
      expanded: boolean;
    });

export function SidebarItem(props: SidebarItemProps) {
  const { icon: Icon, label, active = false, collapsed = false, indent = false, testId } = props;
  const isGroupHeader = props.expanded !== undefined;

  const rowClass = `group relative w-full flex items-center gap-2.5 h-9 rounded-md
    text-[13px] font-medium transition-colors duration-150
    ${indent ? "ps-7" : "ps-3"} pe-2.5
    ${collapsed ? "md:justify-center" : ""}
    ${
      active
        ? "bg-sidebar-primary/15 text-sidebar-primary font-semibold"
        : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
    }`;

  const content = (
    <>
      {active && (
        <span
          className="absolute inset-y-1 start-0 w-[3px] rounded-full bg-sidebar-primary"
          aria-hidden="true"
        />
      )}
      <Icon
        className={`w-4 h-4 shrink-0 ${
          active ? "text-sidebar-primary" : "text-sidebar-foreground/50 group-hover:text-sidebar-accent-foreground"
        }`}
      />
      <span className={collapsed ? "md:hidden" : "flex-1 truncate text-start"}>{label}</span>
      {isGroupHeader && !collapsed && (
        <ChevronRight
          className={`w-3.5 h-3.5 shrink-0 transition-transform duration-200 ease-out ${
            props.expanded ? "rotate-90" : ""
          }`}
        />
      )}
    </>
  );

  if (props.href) {
    return (
      <Link
        href={props.href}
        className={rowClass}
        title={label}
        data-testid={testId}
      >
        {content}
      </Link>
    );
  }

  return (
    <button
      type="button"
      onClick={props.onClick}
      className={rowClass}
      aria-expanded={props.expanded}
      title={label}
      data-testid={testId}
    >
      {content}
    </button>
  );
}
