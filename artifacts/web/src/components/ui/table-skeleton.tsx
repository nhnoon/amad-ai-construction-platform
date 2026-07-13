import { Skeleton } from "@/components/ui/skeleton";

// Shared `.data-table` loading state — renders placeholder rows sized to the
// real column count so the table's height doesn't jump once data arrives.
// Meant to replace the plain "Loading..." text rows scattered across list
// pages with something that previews the eventual layout.

export function TableSkeletonRows({ rows = 5, cols }: { rows?: number; cols: number }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, r) => (
        <tr key={r}>
          {Array.from({ length: cols }).map((_, c) => (
            <td key={c}>
              <Skeleton className="h-4 w-full max-w-[160px]" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}
