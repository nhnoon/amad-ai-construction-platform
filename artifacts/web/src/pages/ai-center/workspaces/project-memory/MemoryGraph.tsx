import { useMemo, useState } from "react";
import type { MemoryItem } from "@/lib/mockProjectMemory";
import { SOURCE_META, SOURCE_TYPE_ORDER } from "./shared";

// Interactive memory relationship graph. Deliberately not a physics/force
// simulation (no new graph-layout dependency) — nodes are placed on a fixed
// radial layout, grouped into one angular sector per source type, with
// well-connected "hub" items pulled slightly toward the center. Edges come
// straight from each MemoryItem's `relatedIds`. Fully custom SVG so it
// themes correctly in light/dark without extra plumbing.

const WIDTH = 520;
const HEIGHT = 440;
const CENTER = { x: WIDTH / 2, y: HEIGHT / 2 - 6 };
const BASE_RADIUS = 168;

interface GraphNode {
  item: MemoryItem;
  x: number;
  y: number;
  degree: number;
}

function buildLayout(items: MemoryItem[]): { nodes: GraphNode[]; edges: [string, string][] } {
  const byType = new Map<string, MemoryItem[]>();
  for (const type of SOURCE_TYPE_ORDER) byType.set(type, []);
  for (const item of items) byType.get(item.sourceType)?.push(item);

  const degree = new Map<string, number>();
  const edgeSet = new Set<string>();
  for (const item of items) {
    for (const relId of item.relatedIds) {
      if (!items.some((i) => i.id === relId)) continue;
      const key = [item.id, relId].sort().join("::");
      edgeSet.add(key);
    }
  }
  for (const key of edgeSet) {
    const [a, b] = key.split("::");
    degree.set(a, (degree.get(a) ?? 0) + 1);
    degree.set(b, (degree.get(b) ?? 0) + 1);
  }

  const sectorWidth = (Math.PI * 2) / SOURCE_TYPE_ORDER.length;
  const nodes: GraphNode[] = [];
  SOURCE_TYPE_ORDER.forEach((type, sectorIdx) => {
    const sectorItems = byType.get(type) ?? [];
    const sectorStart = sectorIdx * sectorWidth - Math.PI / 2;
    sectorItems.forEach((item, i) => {
      const pad = sectorWidth * 0.15;
      const usable = sectorWidth - pad * 2;
      const angle = sectorItems.length === 1
        ? sectorStart + sectorWidth / 2
        : sectorStart + pad + (usable * i) / (sectorItems.length - 1);
      const d = degree.get(item.id) ?? 0;
      const radius = BASE_RADIUS - Math.min(d, 4) * 14;
      nodes.push({
        item,
        x: CENTER.x + radius * Math.cos(angle),
        y: CENTER.y + radius * Math.sin(angle),
        degree: d,
      });
    });
  });

  return { nodes, edges: Array.from(edgeSet).map((k) => k.split("::") as [string, string]) };
}

export function MemoryGraph({
  items,
  selectedId,
  onSelect,
}: {
  items: MemoryItem[];
  selectedId?: string | null;
  onSelect: (item: MemoryItem) => void;
}) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const { nodes, edges } = useMemo(() => buildLayout(items), [items]);
  const focusId = hoveredId ?? selectedId ?? null;

  const connectedIds = useMemo(() => {
    if (!focusId) return null;
    const set = new Set<string>([focusId]);
    for (const [a, b] of edges) {
      if (a === focusId) set.add(b);
      if (b === focusId) set.add(a);
    }
    return set;
  }, [focusId, edges]);

  const nodeById = new Map(nodes.map((n) => [n.item.id, n]));

  return (
    <div className="space-y-3">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full h-auto select-none" role="img" aria-label="Project memory relationship graph">
        <g>
          {edges.map(([a, b]) => {
            const na = nodeById.get(a);
            const nb = nodeById.get(b);
            if (!na || !nb) return null;
            const dim = focusId ? !(connectedIds?.has(a) && connectedIds?.has(b)) : false;
            return (
              <line
                key={`${a}-${b}`}
                x1={na.x} y1={na.y} x2={nb.x} y2={nb.y}
                stroke="hsl(var(--border))"
                strokeWidth={dim ? 1 : 1.5}
                opacity={dim ? 0.18 : 0.65}
              />
            );
          })}
        </g>
        <g>
          {nodes.map(({ item, x, y, degree }) => {
            const meta = SOURCE_META[item.sourceType];
            const isFocus = focusId === item.id;
            const dim = focusId ? !connectedIds?.has(item.id) : false;
            const r = 6 + Math.min(degree, 4) * 1.3;
            return (
              <g
                key={item.id}
                transform={`translate(${x}, ${y})`}
                onMouseEnter={() => setHoveredId(item.id)}
                onMouseLeave={() => setHoveredId(null)}
                onClick={() => onSelect(item)}
                className="cursor-pointer"
                opacity={dim ? 0.3 : 1}
              >
                <title>{`${item.title} (${meta.label})`}</title>
                {isFocus && <circle r={r + 5} fill="none" stroke={meta.color} strokeWidth={2} opacity={0.5} />}
                <circle r={r} fill={meta.color} stroke="hsl(var(--card))" strokeWidth={1.5} />
                {(isFocus || nodes.length <= 8) && (
                  <text
                    x={0} y={-(r + 8)}
                    textAnchor="middle"
                    className="fill-foreground"
                    style={{ fontSize: 10, fontWeight: 600 }}
                  >
                    {item.title.length > 26 ? `${item.title.slice(0, 24)}…` : item.title}
                  </text>
                )}
              </g>
            );
          })}
        </g>
      </svg>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 justify-center border-t border-border/50 pt-3">
        {SOURCE_TYPE_ORDER.map((type) => (
          <span key={type} className="inline-flex items-center gap-1.5 text-[10px] text-muted-foreground">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: SOURCE_META[type].color }} />
            {SOURCE_META[type].label}
          </span>
        ))}
      </div>
      <p className="text-[11px] text-center text-muted-foreground">
        Hover or click a node to trace its connections &middot; click to open full details.
      </p>
    </div>
  );
}
