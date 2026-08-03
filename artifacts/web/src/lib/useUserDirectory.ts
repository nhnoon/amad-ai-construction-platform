import { useMemo } from "react";
import { useListAdminUsers } from "@workspace/api-client-react";
import { useAuth } from "@/context/AuthContext";

// There is no general user-directory endpoint in the backend — only
// GET /admin/users (role == "admin" only) returns real names;
// GET /projects/{id}/memberships (used for assignee pickers) returns
// only user_id + role_on_project, no name. Rather than add a new backend
// endpoint (out of scope this sprint), name resolution is admin-only
// best-effort: admins see real names everywhere, everyone else sees a
// plain "User #{id}" label. This is a known, documented UX gap — see
// the Sprint 6 final report — not a silent workaround.
export function useUserDirectory() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const { data: adminUsers, isLoading } = useListAdminUsers({
    query: { queryKey: ["admin-users-directory"], enabled: isAdmin, staleTime: 5 * 60 * 1000 },
  });

  const byId = useMemo(() => {
    const map = new Map<number, string>();
    for (const u of adminUsers ?? []) {
      map.set(u.id, u.full_name?.trim() || u.email);
    }
    return map;
  }, [adminUsers]);

  function resolveUserName(id: number | null | undefined): string | null {
    if (id == null) return null;
    return byId.get(id) ?? `User #${id}`;
  }

  return { resolveUserName, isDirectoryAvailable: isAdmin, isLoading: isAdmin && isLoading };
}
