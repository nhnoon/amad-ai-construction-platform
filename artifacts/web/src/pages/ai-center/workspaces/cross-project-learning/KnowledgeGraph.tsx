import { useMemo, useState } from "react";
import { Building2, Truck, Boxes } from "lucide-react";
import type { KnowledgeItem } from "@/lib/mockCrossProjectLearning";
import { SOURCE_TYPE_META, SOURCE_TYPE_ORDER } from "./shared";

// Interactive knowledge relationship graph — Projects, Suppliers, and
// Materials sit on an inner ring as structural entity nodes; every
// knowledge item (Document / Meeting / Claim / Contract / Decision /
// Risk / Action, by source type) sits on an outer ring, grouped into a
// sector per source type. Edges connect each case to its project, its
// supplier and material (when relevant), and its same-issue siblings on
// other projects. No new graph-layout dependency — a fixed radial layout,
// same technique as Project Memory's relationship graph.

const WIDTH = 560;
const HEIGHT = 480;
const CENTER = { x: WIDTH / 2, y: HEIGHT / 2 - 4 };
const INNER_RADIUS = 90;
const OUTER_RADIUS = 200;

const ENTITY_COLOR = { project: "#eab308", supplier: "#0ea5e9", material: "#22c55e" } as const;
const ENTITY_ICON = { project: Building2, supplier: Truck, material: Boxes } as const;

interface GraphNode {
  id: string;
  kind: "project" | "supplier" | "material" | "case";
  label: string;
  x: number;
  y: number;
  color: string;
  item?: KnowledgeItem;
}

function buildLayout(items: KnowledgeItem[]) {
  const projectIds = Array.from(new Set(items.map((i) => i.projectCode)));
  const supplierIds = Array.from(new Set(items.map((i) => i.supplierName).filter(Boolean))) as string[];
  const materialIds = Array.from(new Set(items.map((i) => i.materialName).filter(Boolean))) as string[];

  const nodes: GraphNode[] = [];
  const nodeById = new Map<string, GraphNode>();

  // Inner ring — three 120° sectors: projects, suppliers, materials.
  const innerGroups: { kind: "project" | "supplier" | "material"; ids: string[] }[] = [
    { kind: "project", ids: projectIds }, { kind: "supplier", ids: supplierIds }, { kind: "material", ids: materialIds },
  ];
  const sectorWidth = (Math.PI * 2) / 3;
  innerGroups.forEach((group, gi) => {
    const sectorStart = gi * sectorWidth - Math.PI / 2;
    group.ids.forEach((id, i) => {
      const pad = sectorWidth * 0.1;
      const usable = sectorWidth - pad * 2;
      const angle = group.ids.length === 1 ? sectorStart + sectorWidth / 2 : sectorStart + pad + (usable * i) / (group.ids.length - 1);
      const node: GraphNode = {
        id: `${group.kind}:${id}`, kind: group.kind, label: id,
        x: CENTER.x + INNER_RADIUS * Math.cos(angle), y: CENTER.y + INNER_RADIUS * Math.sin(angle),
        color: ENTITY_COLOR[group.kind],
      };
      nodes.push(node);
      nodeById.set(node.id, node);
    });
  });

  // Outer ring — one sector per source type.
  const outerSectorWidth = (Math.PI * 2) / SOURCE_TYPE_ORDER.length;
  const byType = new Map<string, KnowledgeItem[]>();
  for (const t of SOURCE_TYPE_ORDER) byType.set(t, []);
  for (const item of items) byType.get(item.sourceType)?.push(item);

  SOURCE_TYPE_ORDER.forEach((type, ti) => {
    const inType = byType.get(type) ?? [];
    const sectorStart = ti * outerSectorWidth - Math.PI / 2;
    inType.forEach((item, i) => {
      const pad = outerSectorWidth * 0.08;
      const usable = outerSectorWidth - pad * 2;
      const angle = inType.length === 1 ? sectorStart + outerSectorWidth / 2 : sectorStart + pad + (usable * i) / (inType.length - 1);
      const node: GraphNode = {
        id: item.id, kind: "case", label: item.title,
        x: CENTER.x + OUTER_RADIUS * Math.cos(angle), y: CENTER.y + OUTER_RADIUS * Math.sin(angle),
        color: SOURCE_TYPE_META[item.sourceType].color, item,
      };
      nodes.push(node);
      nodeById.set(node.id, node);
    });
  });

  // Edges: case -> project / supplier / material, and case -> connected siblings.
  const edgeSet = new Set<string>();
  for (const item of items) {
    edgeSet.add([item.id, `project:${item.projectCode}`].sort().join("::"));
    if (item.supplierName) edgeSet.add([item.id, `supplier:${item.supplierName}`].sort().join("::"));
    if (item.materialName) edgeSet.add([item.id, `material:${item.materialName}`].sort().join("::"));
    for (const relId of item.connectedIds) edgeSet.add([item.id, relId].sort().join("::"));
  }
  const edges = Array.from(edgeSet).map((k) => k.split("::") as [string, string]).filter(([a, b]) => nodeById.has(a) && nodeById.has(b));

  return { nodes, edges, nodeById };
}

export function KnowledgeGraph({
  items,
  selectedId,
  onSelectCase,
}: {
  items: KnowledgeItem[];
  selectedId?: string | null;
  onSelectCase: (item: KnowledgeItem) => void;
}) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const { nodes, edges, nodeById } = useMemo(() => buildLayout(items), [items]);
  const focusId = hoveredId ?? selectedId ?? null;

  const connected = useMemo(() => {
    if (!focusId) return null;
    const set = new Set<string>([focusId]);
    for (const [a, b] of edges) { if (a === focusId) set.add(b); if (b === focusId) set.add(a); }
    return set;
  }, [focusId, edges]);

  return (
    <div className="space-y-3">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full h-auto select-none" role="img" aria-label="Cross-project knowledge relationship graph">
        <g>
          {edges.map(([a, b]) => {
            const na = nodeById.get(a); const nb = nodeById.get(b);
            if (!na || !nb) return null;
            const dim = focusId ? !(connected?.has(a) && connected?.has(b)) : false;
            return <line key={`${a}-${b}`} x1={na.x} y1={na.y} x2={nb.x} y2={nb.y} stroke="hsl(var(--border))" strokeWidth={dim ? 1 : 1.5} opacity={dim ? 0.15 : 0.6} />;
          })}
        </g>
        <g>
          {nodes.map((node) => {
            const isFocus = focusId === node.id;
            const dim = focusId ? !connected?.has(node.id) : false;
            const r = node.kind === "case" ? 6 : 8;
            return (
              <g
                key={node.id}
                transform={`translate(${node.x}, ${node.y})`}
                onMouseEnter={() => setHoveredId(node.id)}
                onMouseLeave={() => setHoveredId(null)}
                onClick={() => { if (node.kind === "case" && node.item) onSelectCase(node.item); }}
                className={node.kind === "case" ? "cursor-pointer" : ""}
                opacity={dim ? 0.28 : 1}
              >
                <title>{node.label}</title>
                {isFocus && <circle r={r + 5} fill="none" stroke={node.color} strokeWidth={2} opacity={0.5} />}
                <circle r={r} fill={node.color} stroke="hsl(var(--card))" strokeWidth={1.5} />
                {(isFocus || nodes.length <= 10) && (
                  <text x={0} y={-(r + 8)} textAnchor="middle" className="fill-foreground" style={{ fontSize: 10, fontWeight: 600 }}>
                    {node.label.length > 26 ? `${node.label.slice(0, 24)}…` : node.label}
                  </text>
                )}
              </g>
            );
          })}
        </g>
      </svg>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 justify-center border-t border-border/50 pt-3">
        {(["project", "supplier", "material"] as const).map((k) => {
          const Icon = ENTITY_ICON[k];
          return (
            <span key={k} className="inline-flex items-center gap-1.5 text-[10px] text-muted-foreground">
              <Icon className="w-3 h-3" style={{ color: ENTITY_COLOR[k] }} /> {k[0].toUpperCase() + k.slice(1)}
            </span>
          );
        })}
        {SOURCE_TYPE_ORDER.map((type) => (
          <span key={type} className="inline-flex items-center gap-1.5 text-[10px] text-muted-foreground">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: SOURCE_TYPE_META[type].color }} /> {SOURCE_TYPE_META[type].label}
          </span>
        ))}
      </div>
      <p className="text-[11px] text-center text-muted-foreground">
        Inner ring: projects, suppliers, materials &middot; outer ring: knowledge items by source type &middot; hover or click to trace connections.
      </p>
    </div>
  );
}
