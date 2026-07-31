import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

// AMAD Phase 2 — Contextual Hermes (ticket §2). A single source of truth for
// "what specific entity is the user currently looking at," set by the page
// itself (Project Workspace, Site Report detail, a contract's document
// panel, Meeting detail) and read by the "Currently analyzing: …" indicator
// and by anything that needs to scope an AI call to that entity. Pure
// client-side state — no backend change, no new endpoint. Deliberately NOT
// derived only from the URL (contracts don't have their own route — they're
// a document with a completed extraction) so any future entity type can
// register itself the same way without new URL-parsing rules.

export type CurrentEntityKind = "project" | "site_report" | "contract" | "meeting";

export interface CurrentEntity {
  kind: CurrentEntityKind;
  code: string; // e.g. "PRJ-0001", "SR-4", "CT-15", "MTG-12"
  label: string; // human-readable name, e.g. the project/contract title
  projectId?: number; // when known — used to scope /copilot/query calls
}

interface CurrentEntityContextValue {
  entity: CurrentEntity | null;
  setEntity: (entity: CurrentEntity) => void;
  clearEntity: (kind: CurrentEntityKind) => void;
}

const CurrentEntityContext = createContext<CurrentEntityContextValue | null>(null);

export function CurrentEntityProvider({ children }: { children: ReactNode }) {
  const [entity, setEntityState] = useState<CurrentEntity | null>(null);
  // Guards against a stale unmount's clearEntity() firing after a newer
  // page has already set a different entity (e.g. fast navigation between
  // two project pages) — only clear if the kind being cleared is still
  // the one currently displayed.
  const currentKindRef = useRef<CurrentEntityKind | null>(null);

  const setEntity = useCallback((next: CurrentEntity) => {
    currentKindRef.current = next.kind;
    setEntityState(next);
  }, []);

  const clearEntity = useCallback((kind: CurrentEntityKind) => {
    if (currentKindRef.current === kind) {
      currentKindRef.current = null;
      setEntityState(null);
    }
  }, []);

  const value = useMemo(() => ({ entity, setEntity, clearEntity }), [entity, setEntity, clearEntity]);
  return <CurrentEntityContext.Provider value={value}>{children}</CurrentEntityContext.Provider>;
}

export function useCurrentEntity(): CurrentEntity | null {
  const ctx = useContext(CurrentEntityContext);
  return ctx?.entity ?? null;
}

/** Called by a page component to register itself as the active AI context.
 * Call unconditionally at the top of the component — owns its own effect
 * and clears itself on unmount (or when the entity becomes null), so pages
 * never need to remember to clean up manually. */
export function useRegisterCurrentEntity(entity: CurrentEntity | null): void {
  const ctx = useContext(CurrentEntityContext);
  const entityKey = entity ? `${entity.kind}:${entity.code}:${entity.label}:${entity.projectId ?? ""}` : null;

  useEffect(() => {
    if (!ctx || !entity) return;
    ctx.setEntity(entity);
    return () => ctx.clearEntity(entity.kind);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ctx, entityKey]);
}
