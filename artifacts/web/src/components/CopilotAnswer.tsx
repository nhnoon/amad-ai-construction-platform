/**
 * CopilotAnswer — structured block renderer for Copilot answers.
 *
 * Primary path: render `renderBlocks[]` from the backend (typed, deterministic).
 * Fallback path: parse `content` text into typed sections (legacy/LLM responses).
 *
 * All dynamic colors use inline `style` props — Tailwind v4 does not scan
 * JS object literal values for class generation.
 */

import { cn } from "@/lib/utils";

// ─── Backend block types ──────────────────────────────────────────────────────

interface ProjectData {
  name: string;
  code: string;
  status: string;
  budget?: number | null;
  budget_fmt?: string | null;
  city: string;
  client: string;
  start?: string | null;
  planned_finish?: string | null;
  safety_count?: number;
  safety_high?: number;
  ncr_count?: number;
}

interface RenderBlock {
  type: string;
  [key: string]: unknown;
}

// ─── Inline color tokens ──────────────────────────────────────────────────────

interface ColorToken { bg: string; color: string; border: string }

const STATUS_STYLE: Record<string, ColorToken> = {
  "delayed":   { bg:"rgba(239,68,68,0.12)",   color:"#b91c1c", border:"rgba(239,68,68,0.30)"  },
  "on hold":   { bg:"rgba(245,158,11,0.12)",  color:"#92400e", border:"rgba(245,158,11,0.30)" },
  "active":    { bg:"rgba(16,185,129,0.12)",  color:"#065f46", border:"rgba(16,185,129,0.30)" },
  "completed": { bg:"rgba(59,130,246,0.12)",  color:"#1e3a8a", border:"rgba(59,130,246,0.30)" },
  "planning":  { bg:"rgba(139,92,246,0.12)",  color:"#5b21b6", border:"rgba(139,92,246,0.30)" },
};
const STATUS_DEFAULT: ColorToken = { bg:"rgba(107,114,128,0.10)", color:"#374151", border:"rgba(107,114,128,0.28)" };

const SOURCE_STYLE: Record<string, ColorToken> = {
  "PRJ-": { bg:"rgba(59,130,246,0.10)",  color:"#1d4ed8", border:"rgba(59,130,246,0.28)" },
  "SE-":  { bg:"rgba(239,68,68,0.10)",   color:"#b91c1c", border:"rgba(239,68,68,0.28)"  },
  "NCR-": { bg:"rgba(245,158,11,0.10)",  color:"#92400e", border:"rgba(245,158,11,0.28)" },
  "PO-":  { bg:"rgba(99,102,241,0.10)",  color:"#3730a3", border:"rgba(99,102,241,0.28)" },
  "PR-":  { bg:"rgba(99,102,241,0.10)",  color:"#3730a3", border:"rgba(99,102,241,0.28)" },
  "#":    { bg:"rgba(107,114,128,0.10)", color:"#374151", border:"rgba(107,114,128,0.28)"},
};
const SOURCE_DEFAULT: ColorToken = { bg:"rgba(107,114,128,0.10)", color:"#374151", border:"rgba(107,114,128,0.28)" };

interface RiskStyleToken { border: string; bg: string; titleColor: string; metaColor: string; bulletColor: string }
const RISK_STYLE: Record<string, RiskStyleToken> = {
  red:    { border:"#ef4444", bg:"rgba(239,68,68,0.09)",   titleColor:"#dc2626", metaColor:"rgba(220,38,38,0.65)",  bulletColor:"#f87171" },
  orange: { border:"#f97316", bg:"rgba(249,115,22,0.09)",  titleColor:"#c2410c", metaColor:"rgba(194,65,12,0.65)",  bulletColor:"#fb923c" },
  yellow: { border:"#eab308", bg:"rgba(234,179,8,0.09)",   titleColor:"#a16207", metaColor:"rgba(161,98,7,0.65)",   bulletColor:"#facc15" },
  amber:  { border:"#f59e0b", bg:"rgba(245,158,11,0.09)",  titleColor:"#b45309", metaColor:"rgba(180,83,9,0.65)",   bulletColor:"#fbbf24" },
  blue:   { border:"#3b82f6", bg:"rgba(59,130,246,0.09)",  titleColor:"#1d4ed8", metaColor:"rgba(29,78,216,0.65)",  bulletColor:"#60a5fa" },
  gray:   { border:"#6b7280", bg:"rgba(107,114,128,0.06)", titleColor:"#374151", metaColor:"rgba(107,114,128,0.75)",bulletColor:"#9ca3af" },
};

const SEVERITY_STYLE: Record<string, ColorToken> = {
  high:   { bg:"rgba(239,68,68,0.12)",  color:"#b91c1c", border:"rgba(239,68,68,0.30)"  },
  medium: { bg:"rgba(245,158,11,0.12)", color:"#92400e", border:"rgba(245,158,11,0.30)" },
  low:    { bg:"rgba(16,185,129,0.12)", color:"#065f46", border:"rgba(16,185,129,0.30)" },
};

// ─── Primitive helpers ────────────────────────────────────────────────────────

function sourceStyle(code: string): ColorToken {
  for (const [prefix, s] of Object.entries(SOURCE_STYLE)) {
    if (code.startsWith(prefix)) return s;
  }
  return SOURCE_DEFAULT;
}

function statusStyle(status: string): ColorToken {
  return STATUS_STYLE[status.toLowerCase().trim()] ?? STATUS_DEFAULT;
}

function SourceChip({ code }: { code: string }) {
  const s = sourceStyle(code);
  return (
    <span style={{ backgroundColor:s.bg, color:s.color, border:`1px solid ${s.border}` }}
          className="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-mono font-medium leading-none shrink-0">
      {code}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const s = statusStyle(status);
  return (
    <span style={{ backgroundColor:s.bg, color:s.color, border:`1px solid ${s.border}` }}
          className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium leading-none shrink-0">
      {status}
    </span>
  );
}

function CodeBadge({ code }: { code: string }) {
  return (
    <span className="text-xs font-mono text-muted-foreground px-1.5 py-0.5 rounded shrink-0"
          style={{ backgroundColor:"rgba(0,0,0,0.05)", border:"1px solid rgba(0,0,0,0.08)" }}>
      {code}
    </span>
  );
}

function InlineText({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <>
      {parts.map((p, i) =>
        p.startsWith("**") && p.endsWith("**")
          ? <strong key={i} className="font-semibold text-foreground">{p.slice(2, -2)}</strong>
          : <span key={i}>{p}</span>
      )}
    </>
  );
}

// ─── ProjectCard ──────────────────────────────────────────────────────────────

function ProjectCard({ proj, index, isAr }: { proj: ProjectData; index?: number; isAr: boolean }) {
  return (
    <div className="flex gap-2.5 items-start p-2.5 rounded-lg"
         style={{ backgroundColor:"rgba(0,0,0,0.03)", border:"1px solid rgba(0,0,0,0.08)" }}>
      {index != null && (
        <span className="text-muted-foreground text-xs mt-1 shrink-0 font-mono w-4 text-right">{index}</span>
      )}
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-sm text-foreground truncate">{proj.name}</span>
          <CodeBadge code={proj.code} />
          {proj.status && <StatusBadge status={proj.status} />}
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {proj.budget_fmt && (
            <span className="text-xs font-semibold text-primary">{proj.budget_fmt}</span>
          )}
          {proj.city && <span className="text-xs text-muted-foreground">{proj.city}</span>}
          {proj.client && <span className="text-xs text-muted-foreground">{proj.client}</span>}
        </div>
        {(proj.safety_count != null || proj.ncr_count != null) && (
          <div className="flex gap-2 flex-wrap">
            {proj.safety_count != null && (
              <span className="text-xs text-muted-foreground">
                {isAr ? `${proj.safety_count} حدث سلامة` : `${proj.safety_count} safety event(s)`}
                {proj.safety_high ? ` (${proj.safety_high} ${isAr ? "عالية" : "high"})` : ""}
              </span>
            )}
            {proj.ncr_count != null && (
              <span className="text-xs text-muted-foreground">
                {isAr ? `${proj.ncr_count} طلب تصحيح` : `${proj.ncr_count} NCR(s)`}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Block renderers ──────────────────────────────────────────────────────────

function ProjectListBlock({ block, isAr }: { block: RenderBlock; isAr: boolean }) {
  const total = block.total as number;
  const labelEn = block.filter_label_en as string;
  const labelAr = block.filter_label_ar as string;
  const projects = (block.projects as ProjectData[]) ?? [];
  const label = isAr ? labelAr : labelEn;

  return (
    <div className="space-y-2">
      <p className="text-sm text-muted-foreground font-medium">
        {isAr ? `تم العثور على ${total} مشروع (${label})` : `Found ${total} ${label} project(s)`}
      </p>
      {projects.map((proj, i) => (
        <ProjectCard key={proj.code} proj={proj} index={i + 1} isAr={isAr} />
      ))}
    </div>
  );
}

function ProjectCardBlock({ block, isAr }: { block: RenderBlock; isAr: boolean }) {
  const proj = block.project as ProjectData;
  const highlight = block.highlight as { label_en: string; label_ar: string; value: string } | null;
  const runnerUp = block.runner_up as { name: string; code: string; budget_fmt?: string } | null;

  return (
    <div className="space-y-2.5">
      {/* Main project card */}
      <div className="rounded-xl p-3.5 space-y-3"
           style={{ border:"1px solid rgba(59,130,246,0.25)", backgroundColor:"rgba(59,130,246,0.04)" }}>
        <div className="flex items-start gap-2 flex-wrap">
          <span className="font-semibold text-foreground text-sm">{proj.name}</span>
          <CodeBadge code={proj.code} />
          {proj.status && <StatusBadge status={proj.status} />}
        </div>
        {highlight && (
          <p className="text-sm text-foreground">
            {isAr ? highlight.label_ar : highlight.label_en}{" — "}
            <strong className="font-bold text-primary">{highlight.value}</strong>
          </p>
        )}
        {/* KV detail grid */}
        {(() => {
          const rows: [string, string, string][] = []; // [label_en, label_ar, value]
          if (proj.budget_fmt) rows.push(["Budget", "الميزانية", proj.budget_fmt]);
          if (proj.client)     rows.push(["Client", "العميل", proj.client]);
          if (proj.city)       rows.push(["City", "المدينة", proj.city]);
          if (proj.start)      rows.push(["Start date", "تاريخ البدء", proj.start]);
          if (proj.planned_finish) rows.push(["Planned finish", "الإنجاز المخطط", proj.planned_finish]);
          if (proj.safety_count != null) rows.push(["Safety events", "أحداث السلامة", String(proj.safety_count) + (proj.safety_high ? ` (${proj.safety_high} high)` : "")]);
          if (proj.ncr_count != null)    rows.push(["Open NCRs", "طلبات التصحيح", String(proj.ncr_count)]);
          if (!rows.length) return null;
          return (
            <div className="rounded-lg overflow-hidden text-xs"
                 style={{ border:"1px solid rgba(128,128,128,0.15)" }}>
              {rows.map(([en, ar, val], i) => (
                <div key={i} className="flex items-center"
                     style={{
                       borderBottom: i < rows.length - 1 ? "1px solid rgba(128,128,128,0.10)" : undefined,
                       backgroundColor: i % 2 !== 0 ? "rgba(128,128,128,0.03)" : "transparent",
                     }}>
                  <div className="px-3 py-1.5 font-medium text-muted-foreground shrink-0"
                       style={{ width:"40%", borderRight:"1px solid rgba(128,128,128,0.10)" }}>
                    {isAr ? ar : en}
                  </div>
                  <div className="px-3 py-1.5 text-foreground flex-1">{val}</div>
                </div>
              ))}
            </div>
          );
        })()}
      </div>

      {/* Runner-up / comparison note */}
      {runnerUp && (
        <div className="rounded-lg p-3 space-y-1"
             style={{ border:"1px solid rgba(128,128,128,0.15)", backgroundColor:"rgba(128,128,128,0.03)" }}>
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">VS</div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-sm text-foreground">{runnerUp.name}</span>
            <CodeBadge code={runnerUp.code} />
          </div>
          {runnerUp.budget_fmt && (
            <p className="text-xs text-muted-foreground">
              {isAr ? `الميزانية: ${runnerUp.budget_fmt}` : `Budget: ${runnerUp.budget_fmt}`}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function ComparisonBlock({ block, isAr }: { block: RenderBlock; isAr: boolean }) {
  const projects = (block.projects as ProjectData[]) ?? [];
  const metrics = (block.metrics as Array<{
    label_en: string; label_ar: string; a: string; b: string; winner?: string | null;
  }>) ?? [];
  const [pa, pb] = projects;
  if (!pa || !pb) return null;

  return (
    <div className="space-y-3">
      {/* Side-by-side header */}
      <div className="grid grid-cols-[1fr_auto_1fr] gap-2 items-center">
        <div className="rounded-lg p-2.5 space-y-1"
             style={{ border:"1px solid rgba(59,130,246,0.22)", backgroundColor:"rgba(59,130,246,0.05)" }}>
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-semibold text-sm text-foreground leading-tight">{pa.name}</span>
            <CodeBadge code={pa.code} />
          </div>
          {pa.status && <StatusBadge status={pa.status} />}
        </div>
        <div className="text-xs font-bold text-muted-foreground shrink-0 px-1">VS</div>
        <div className="rounded-lg p-2.5 space-y-1"
             style={{ border:"1px solid rgba(107,114,128,0.20)", backgroundColor:"rgba(107,114,128,0.04)" }}>
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-semibold text-sm text-foreground leading-tight">{pb.name}</span>
            <CodeBadge code={pb.code} />
          </div>
          {pb.status && <StatusBadge status={pb.status} />}
        </div>
      </div>

      {/* Metrics table */}
      {metrics.length > 0 && (
        <div className="rounded-lg overflow-hidden text-xs"
             style={{ border:"1px solid rgba(128,128,128,0.15)" }}>
          <div className="grid grid-cols-3"
               style={{ backgroundColor:"rgba(128,128,128,0.05)", borderBottom:"1px solid rgba(128,128,128,0.12)" }}>
            <div className="px-3 py-2 font-semibold text-muted-foreground">{isAr ? "السمة" : "Attribute"}</div>
            <div className="px-3 py-2 font-semibold text-foreground"
                 style={{ borderLeft:"1px solid rgba(128,128,128,0.10)" }}>{pa.name.split(" ").slice(0, 2).join(" ")}</div>
            <div className="px-3 py-2 font-semibold text-foreground"
                 style={{ borderLeft:"1px solid rgba(128,128,128,0.10)" }}>{pb.name.split(" ").slice(0, 2).join(" ")}</div>
          </div>
          {metrics.map((m, i) => (
            <div key={i} className="grid grid-cols-3"
                 style={{
                   borderBottom: i < metrics.length - 1 ? "1px solid rgba(128,128,128,0.08)" : undefined,
                   backgroundColor: i % 2 !== 0 ? "rgba(128,128,128,0.025)" : "transparent",
                 }}>
              <div className="px-3 py-1.5 text-muted-foreground">{isAr ? m.label_ar : m.label_en}</div>
              <div className="px-3 py-1.5 text-foreground font-medium"
                   style={{
                     borderLeft:"1px solid rgba(128,128,128,0.08)",
                     color: m.winner === "a" ? "#059669" : undefined,
                   }}>
                {m.a}{m.winner === "a" && " ↑"}
              </div>
              <div className="px-3 py-1.5 text-foreground font-medium"
                   style={{
                     borderLeft:"1px solid rgba(128,128,128,0.08)",
                     color: m.winner === "b" ? "#059669" : undefined,
                   }}>
                {m.b}{m.winner === "b" && " ↑"}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SafetySummaryBlock({ block, isAr }: { block: RenderBlock; isAr: boolean }) {
  const total  = block.total  as number;
  const high   = block.high   as number;
  const medium = block.medium as number;
  const low    = block.low    as number;
  const notable = (block.notable as Array<{ code: string; description: string; severity: string }>) ?? [];

  const rawCounts: [string, string, number, ColorToken][] = [
    [isAr ? "عالية" : "High",   "high",   high,   SEVERITY_STYLE.high   ?? SOURCE_DEFAULT],
    [isAr ? "متوسطة" : "Medium", "medium", medium, SEVERITY_STYLE.medium ?? SOURCE_DEFAULT],
    [isAr ? "منخفضة" : "Low",    "low",    low,    SEVERITY_STYLE.low    ?? SOURCE_DEFAULT],
  ];
  const counts = rawCounts.filter((row) => row[2] > 0);

  return (
    <div className="rounded-xl p-3 space-y-3"
         style={{ border:"1px solid rgba(239,68,68,0.25)", backgroundColor:"rgba(239,68,68,0.04)" }}>
      <div className="flex items-center gap-3">
        <span className="text-2xl leading-none">🛡️</span>
        <div>
          <p className="font-semibold text-sm text-foreground">
            {isAr ? `أحداث السلامة — ${total} حدث` : `Safety Events — ${total} on record`}
          </p>
        </div>
      </div>
      {counts.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {counts.map(([label,, count, s]) => (
            <span key={label}
                  style={{ backgroundColor:s.bg, color:s.color, border:`1px solid ${s.border}` }}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold">
              <span className="text-base leading-none font-bold">{count}</span>
              {label}
            </span>
          ))}
        </div>
      )}
      {notable.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            {isAr ? "أحداث بارزة" : "Notable events"}
          </p>
          {notable.map(ev => {
            const sevKey = ev.severity?.toLowerCase();
            const sevStyle = SEVERITY_STYLE[sevKey] ?? SOURCE_DEFAULT;
            return (
              <div key={ev.code} className="flex items-start gap-2 text-xs">
                <SourceChip code={ev.code} />
                <span className="text-foreground flex-1">{ev.description}</span>
                {ev.severity && (
                  <span style={{ backgroundColor:sevStyle.bg, color:sevStyle.color, border:`1px solid ${sevStyle.border}` }}
                        className="px-1.5 py-0.5 rounded text-xs font-medium shrink-0">
                    {ev.severity}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function NcrSummaryBlock({ block, isAr }: { block: RenderBlock; isAr: boolean }) {
  const total = block.total as number;
  const underAction = block.under_corrective_action as number;
  const items = (block.items as Array<{ code: string; type: string; status: string }>) ?? [];

  return (
    <div className="rounded-xl p-3 space-y-3"
         style={{ border:"1px solid rgba(245,158,11,0.25)", backgroundColor:"rgba(245,158,11,0.04)" }}>
      <div className="flex items-center gap-3">
        <span className="text-2xl leading-none">📋</span>
        <div>
          <p className="font-semibold text-sm text-foreground">
            {isAr ? `طلبات التصحيح — ${total} مفتوح` : `Open NCRs — ${total} total`}
          </p>
          {underAction > 0 && (
            <p className="text-xs text-muted-foreground">
              {isAr ? `${underAction} قيد التنفيذ` : `${underAction} under corrective action`}
            </p>
          )}
        </div>
      </div>
      {items.length > 0 && (
        <div className="space-y-1">
          {items.map(item => (
            <div key={item.code} className="flex items-center gap-2 text-xs">
              <SourceChip code={item.code} />
              {item.type && <span className="text-foreground">{item.type}</span>}
              {item.status && <span className="text-muted-foreground">{item.status}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RiskSummaryBlock({ block, isAr }: { block: RenderBlock; isAr: boolean }) {
  const categories = (block.categories as Array<{
    color: string;
    emoji: string;
    title_en: string;
    title_ar: string;
    subtitle_en?: string | null;
    subtitle_ar?: string | null;
    items: Array<{ code?: string; text?: string; text_ar?: string; codes?: string[]; label_en?: string; label_ar?: string }>;
  }>) ?? [];

  return (
    <div className="space-y-2">
      {categories.map((cat, ci) => {
        const s = RISK_STYLE[cat.color] ?? RISK_STYLE.gray;
        const title = isAr ? cat.title_ar : cat.title_en;
        const subtitle = isAr ? cat.subtitle_ar : cat.subtitle_en;
        return (
          <div key={ci}
               style={{ borderInlineStart:`3px solid ${s.border}`, backgroundColor:s.bg }}
               className="rounded-lg px-3 py-2.5 space-y-1.5">
            <div className="flex items-start gap-2 flex-wrap">
              <span className="text-base leading-none">{cat.emoji}</span>
              <span className="font-semibold text-sm" style={{ color:s.titleColor }}>{title}</span>
              {subtitle && (
                <span className="text-xs mt-px" style={{ color:s.metaColor }}>— {subtitle}</span>
              )}
            </div>
            {cat.items.length > 0 && (
              <ul className="space-y-1">
                {cat.items.map((item, ii) => {
                  const label = isAr ? (item.label_ar ?? item.label_en ?? "") : (item.label_en ?? "");
                  const text  = isAr ? (item.text_ar ?? item.text ?? "") : (item.text ?? "");
                  const codes = item.codes ?? [];
                  return (
                    <li key={ii} className="flex items-start gap-1.5 text-xs text-foreground flex-wrap">
                      <span className="mt-0.5 shrink-0 font-bold" style={{ color:s.bulletColor }}>›</span>
                      {label && <span className="text-muted-foreground shrink-0">{label}:</span>}
                      {item.code && <SourceChip code={item.code} />}
                      {codes.map((c, ci2) => <SourceChip key={ci2} code={c} />)}
                      {text && <span className="text-foreground">{text}</span>}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        );
      })}
    </div>
  );
}

function CitationsBlock({ block, isAr }: { block: RenderBlock; isAr: boolean }) {
  const codes = (block.codes as string[]) ?? [];
  if (!codes.length) return null;

  const proj  = codes.filter(c => c.startsWith("PRJ-"));
  const se    = codes.filter(c => c.startsWith("SE-"));
  const ncr   = codes.filter(c => c.startsWith("NCR-"));
  const po    = codes.filter(c => c.startsWith("PO-") || c.startsWith("PR-"));
  const risk  = codes.filter(c => c.startsWith("#"));
  const rest  = codes.filter(c => !proj.includes(c) && !se.includes(c) && !ncr.includes(c) && !po.includes(c) && !risk.includes(c));

  const groups: [string, string[]][] = ([
    [isAr ? "مشاريع"  : "Projects",   proj],
    [isAr ? "سلامة"   : "Safety",     se],
    [isAr ? "جودة"    : "NCR",        ncr],
    [isAr ? "مشتريات" : "PO / PR",    po],
    [isAr ? "مخاطر"   : "Risks",      risk],
    ["",                                rest],
  ] as [string, string[]][]).filter(([, arr]) => arr.length > 0);

  return (
    <div className="flex flex-col gap-1.5 pt-2"
         style={{ borderTop:"1px solid rgba(128,128,128,0.12)" }}>
      <span className="text-xs text-muted-foreground uppercase tracking-wide font-medium">
        {isAr ? "المصادر" : "Sources"}
      </span>
      <div className="flex flex-col gap-1">
        {groups.map(([label, grpCodes], gi) => (
          <div key={gi} className="flex items-start gap-1.5 flex-wrap">
            {label && <span className="text-xs text-muted-foreground shrink-0 mt-px">{label}:</span>}
            {(grpCodes as string[]).map((c, i) => <SourceChip key={i} code={c} />)}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Health score blocks ──────────────────────────────────────────────────────

interface HealthItem {
  code: string;
  name: string;
  score: number | null;
  level: string | null;
  reasons: string[];
  href?: string;
}

const HEALTH_STYLE: Record<string, { bar: string; text: string; bg: string; border: string }> = {
  "Excellent": { bar:"#22c55e", text:"#16a34a", bg:"rgba(22,163,74,0.08)",   border:"rgba(22,163,74,0.25)"  },
  "Good":      { bar:"#3b82f6", text:"#2563eb", bg:"rgba(37,99,235,0.08)",   border:"rgba(37,99,235,0.25)"  },
  "At Risk":   { bar:"#f59e0b", text:"#d97706", bg:"rgba(245,158,11,0.08)",  border:"rgba(245,158,11,0.25)" },
  "Critical":  { bar:"#ef4444", text:"#dc2626", bg:"rgba(220,38,38,0.08)",   border:"rgba(220,38,38,0.25)"  },
};
const HEALTH_DEFAULT = { bar:"#94a3b8", text:"#64748b", bg:"rgba(148,163,184,0.08)", border:"rgba(148,163,184,0.25)" };

function HealthScoreRow({ item }: { item: HealthItem }) {
  const s = HEALTH_STYLE[item.level ?? ""] ?? HEALTH_DEFAULT;
  return (
    <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg"
         style={{ backgroundColor: s.bg, border: `1px solid ${s.border}` }}>
      {/* Score mini-circle */}
      <div className="relative w-10 h-10 shrink-0">
        <svg viewBox="0 0 40 40" className="w-10 h-10 -rotate-90">
          <circle cx="20" cy="20" r="15" fill="none" stroke="currentColor"
                  strokeWidth="4" className="text-muted opacity-20" />
          <circle cx="20" cy="20" r="15" fill="none" strokeWidth="4"
                  strokeDasharray={`${((item.score ?? 0) / 100) * 94.2} 94.2`}
                  strokeLinecap="round"
                  style={{ stroke: s.bar }} />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-[10px] font-bold tabular-nums" style={{ color: s.text }}>
            {item.score ?? "—"}
          </span>
        </div>
      </div>
      {/* Name + level */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-sm text-foreground truncate">{item.name}</span>
          <span className="text-xs font-mono text-muted-foreground px-1 py-0.5 rounded"
                style={{ backgroundColor:"rgba(0,0,0,0.05)", border:"1px solid rgba(0,0,0,0.08)" }}>
            {item.code}
          </span>
          <span className="text-xs font-semibold" style={{ color: s.text }}>{item.level}</span>
        </div>
        {item.reasons.length > 0 && (
          <p className="text-xs text-muted-foreground mt-0.5 truncate">
            {item.reasons[0]}{item.reasons.length > 1 ? ` +${item.reasons.length - 1} more` : ""}
          </p>
        )}
      </div>
    </div>
  );
}

function HealthListBlock({ block, isAr }: { block: RenderBlock; isAr: boolean }) {
  const items = (block.items as HealthItem[]) ?? [];
  if (!items.length) return null;
  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
        {isAr ? "درجات صحة المشاريع" : `Project Health Scores (${items.length})`}
      </p>
      {items.map((item) => (
        <HealthScoreRow key={item.code} item={item} />
      ))}
    </div>
  );
}

function HealthCardBlock({ block, isAr }: { block: RenderBlock; isAr: boolean }) {
  const score   = block.score   as number | null;
  const level   = block.level   as string | null;
  const name    = block.name    as string;
  const code    = block.code    as string;
  const reasons = (block.reasons as string[]) ?? [];
  const s = HEALTH_STYLE[level ?? ""] ?? HEALTH_DEFAULT;
  const circ = ((score ?? 0) / 100) * 163.4;

  return (
    <div className="rounded-xl p-4 space-y-3"
         style={{ backgroundColor: s.bg, border: `1px solid ${s.border}` }}>
      <div className="flex items-center gap-4">
        {/* Score dial */}
        <div className="relative w-16 h-16 shrink-0">
          <svg viewBox="0 0 64 64" className="w-16 h-16 -rotate-90">
            <circle cx="32" cy="32" r="26" fill="none" stroke="currentColor"
                    strokeWidth="6" className="text-muted opacity-20" />
            <circle cx="32" cy="32" r="26" fill="none" strokeWidth="6"
                    strokeDasharray={`${circ} 163.4`} strokeLinecap="round"
                    style={{ stroke: s.bar }} />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-sm font-bold tabular-nums" style={{ color: s.text }}>
              {score ?? "—"}
            </span>
          </div>
        </div>
        <div>
          <div className="flex items-center gap-2 flex-wrap mb-0.5">
            <span className="font-semibold text-foreground">{name}</span>
            <span className="text-xs font-mono px-1.5 py-0.5 rounded text-muted-foreground"
                  style={{ backgroundColor:"rgba(0,0,0,0.05)", border:"1px solid rgba(0,0,0,0.08)" }}>
              {code}
            </span>
          </div>
          <p className="text-xl font-bold" style={{ color: s.text }}>{level}</p>
          <p className="text-xs text-muted-foreground">{isAr ? `درجة الصحة: ${score}/100` : `Score: ${score}/100`}</p>
        </div>
      </div>
      {/* Score bar */}
      <div className="space-y-1">
        <div className="h-1.5 rounded-full bg-muted overflow-hidden">
          <div className="h-full rounded-full" style={{ width: `${score ?? 0}%`, backgroundColor: s.bar }} />
        </div>
      </div>
      {/* Reasons */}
      {reasons.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            {isAr ? "الأسباب" : "Contributing factors"}
          </p>
          <ul className="space-y-0.5">
            {reasons.map((r, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs text-foreground">
                <span className="shrink-0 mt-0.5" style={{ color: s.text }}>•</span>
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}
      {reasons.length === 0 && (
        <p className="text-xs font-medium" style={{ color:"#16a34a" }}>
          ✓ {isAr ? "لا توجد مشكلات — المشروع في المسار الصحيح" : "No issues detected — project is on track"}
        </p>
      )}
    </div>
  );
}

// ─── Block dispatcher ────────────────────────────────────────────────────────

function BlockRenderer({ block, isAr }: { block: RenderBlock; isAr: boolean }) {
  switch (block.type) {
    case "project_list":    return <ProjectListBlock    block={block} isAr={isAr} />;
    case "project_card":    return <ProjectCardBlock    block={block} isAr={isAr} />;
    case "comparison":      return <ComparisonBlock     block={block} isAr={isAr} />;
    case "safety_summary":  return <SafetySummaryBlock  block={block} isAr={isAr} />;
    case "ncr_summary":     return <NcrSummaryBlock     block={block} isAr={isAr} />;
    case "risk_summary":    return <RiskSummaryBlock    block={block} isAr={isAr} />;
    case "health_list":     return <HealthListBlock     block={block} isAr={isAr} />;
    case "health_card":     return <HealthCardBlock     block={block} isAr={isAr} />;
    case "citations":       return <CitationsBlock      block={block} isAr={isAr} />;
    default:                return null;
  }
}

// ─── Fallback text parser (LLM responses) ────────────────────────────────────

type FallbackSectionType = "title" | "risk" | "kv" | "numbered" | "metric" | "list" | "heading" | "sources" | "paragraph";
interface FallbackSection {
  type: FallbackSectionType;
  emoji?: string;
  color?: string;
  title?: string;
  metadata?: string;
  items?: string[];
  text?: string;
  citations?: string[];
  count?: number;
  domain?: string;
}

const EMOJI_COLOR: Record<string, string> = {
  "🔴":"red","🟠":"orange","🟡":"yellow","⚠️":"amber","📦":"blue",
};
const BOILERPLATE_RE = [
  /^based on (the )?retrieved (evidence|records?|data|information)/i,
  /^please refer to/i,
  /^i found the following/i,
  /^according to (the )?retrieved/i,
  /^the (following|retrieved) (records?|data|evidence)/i,
  /^here (are|is) the (retrieved|matching|following)/i,
  /^based on the retrieved records?,\s*\d+\s+project\(s\)/i,
  /^the data includes\s/i,
  /^refer to\s+(prj|se|ncr|po)-/i,
];
function isBoilerplate(line: string) { return BOILERPLATE_RE.some(r => r.test(line.trim())); }
const METRIC_RE = /^(\d+)\s+([\w\u0600-\u06FF][\w\u0600-\u06FF\s]+?)\s*\(s\)\s+found:\s*/i;
function extractCodes(text: string) { return [...text.matchAll(/\b((?:SE|NCR|PO|PR|PRJ)-[\d\w]+)\b/g)].map(m => m[1]); }
function domainFromText(t: string): string {
  t = t.toLowerCase();
  if (t.includes("safety") || t.includes("سلامة")) return "safety";
  if (t.includes("ncr") || t.includes("جودة")) return "ncr";
  if (t.includes("procurement") || t.includes("purchase")) return "procurement";
  if (t.includes("project") || t.includes("مشروع")) return "project";
  return "generic";
}
const METRIC_DOMAIN: Record<string, { bg: string; color: string; border: string; label_en: string; label_ar: string }> = {
  safety:      { bg:"rgba(239,68,68,0.10)",   color:"#b91c1c", border:"rgba(239,68,68,0.30)",   label_en:"Safety Events",       label_ar:"أحداث السلامة" },
  procurement: { bg:"rgba(99,102,241,0.10)",  color:"#3730a3", border:"rgba(99,102,241,0.30)",  label_en:"Procurement Records", label_ar:"سجلات المشتريات" },
  ncr:         { bg:"rgba(245,158,11,0.10)",  color:"#92400e", border:"rgba(245,158,11,0.30)",  label_en:"NCRs",                label_ar:"عدم المطابقة" },
  project:     { bg:"rgba(59,130,246,0.10)",  color:"#1d4ed8", border:"rgba(59,130,246,0.30)",  label_en:"Projects",            label_ar:"المشاريع" },
  generic:     { bg:"rgba(107,114,128,0.10)", color:"#374151", border:"rgba(107,114,128,0.30)", label_en:"Records",             label_ar:"سجلات" },
};

function parseFallback(raw: string): FallbackSection[] {
  const sections: FallbackSection[] = [];
  let cur: FallbackSection | null = null;
  function flush() {
    if (!cur) return;
    const keep = (cur.title?.trim()) || (cur.text?.trim()) || (cur.items?.length ?? 0) > 0 || (cur.count !== undefined);
    if (keep) sections.push(cur);
    cur = null;
  }
  for (const rawLine of raw.split("\n")) {
    const line = rawLine.trim();
    if (!line) { flush(); continue; }
    if (isBoilerplate(line)) continue;
    const riskM = line.match(/^\*\*(🔴|🟠|🟡|⚠️|📦)\s*(.+?)\*\*\s*(.*)$/);
    if (riskM) { flush(); cur = { type:"risk", emoji:riskM[1], color:EMOJI_COLOR[riskM[1]] ?? "gray", title:riskM[2].trim(), metadata:riskM[3].trim()||undefined, items:[] }; continue; }
    if (/^(Sources?:|المصادر:|مصادر:|المراجع:)/i.test(line)) {
      flush();
      const codes = [...line.replace(/^(Sources?:|المصادر:|مصادر:|المراجع:)/i,"").matchAll(/\[([^\]]+)\]/g)].map(m=>m[1]);
      if (codes.length) sections.push({ type:"sources", citations:codes }); continue;
    }
    if (/^(\[[\w\d#-]+\][\s,]*)+$/.test(line)) {
      flush();
      const codes = [...line.matchAll(/\[([^\]]+)\]/g)].map(m=>m[1]);
      if (codes.length) sections.push({ type:"sources", citations:codes }); continue;
    }
    const metricM = line.match(METRIC_RE);
    if (metricM) {
      flush();
      const count = parseInt(metricM[1], 10), domainRaw = metricM[2].trim();
      sections.push({ type:"metric", count, domain:domainFromText(domainRaw+" "+line), title:`${count} ${domainRaw}(s)`, text:line, citations:extractCodes(line) }); continue;
    }
    const headM = line.match(/^\*\*([^*]+)\*\*\s*(?:\([^)]*\)|—\s*.+)?\s*$/);
    if (headM) { flush(); sections.push({ type:"title", title:headM[1].trim() }); continue; }
    const numM = line.match(/^(\d+)\.\s+(.+)$/);
    if (numM) { if (!cur || cur.type !== "numbered") { flush(); cur = { type:"numbered", items:[] }; } cur.items!.push(numM[2]); continue; }
    if (/^-\s/.test(line) || /^\s+-\s/.test(rawLine)) {
      const item = line.replace(/^-\s+/, "").trim();
      if (cur && (cur.type === "risk" || cur.type === "list" || cur.type === "heading")) { cur.items = cur.items ?? []; cur.items.push(item); }
      else { if (!cur || cur.type !== "list") { flush(); cur = { type:"list", items:[] }; } cur.items!.push(item); }
      continue;
    }
    if (!cur) cur = { type:"paragraph", text:line };
    else if (cur.type === "paragraph") cur.text = (cur.text ?? "") + "\n" + line;
    else { cur.items = cur.items ?? []; cur.items.push(line); }
  }
  flush();
  return sections.map(s => {
    if (s.type !== "list" || !s.items?.length) return s;
    const isKV = s.items.every(i => { const m = i.match(/^([^:]+):\s+(.+)$/); return m && !/^(SE|NCR|PO|PR|PRJ)-/i.test(m[1].trim()); });
    return isKV ? { ...s, type:"kv" as FallbackSectionType } : s;
  });
}

// Fallback section renderers (kept for LLM/edge-case answers)
function FbItemValue({ text }: { text: string }) {
  const trailing: string[] = [];
  const cleanText = text.replace(/\s*\[([^\]]+)\]/g, (_, c) => { trailing.push(c); return ""; }).trim();
  return (
    <span className="inline-flex items-center gap-1 flex-wrap text-sm">
      <InlineText text={cleanText} />
      {trailing.map((c, i) => <SourceChip key={i} code={c} />)}
    </span>
  );
}

function FbRiskCard({ section }: { section: FallbackSection }) {
  const s = RISK_STYLE[section.color ?? "gray"];
  return (
    <div style={{ borderInlineStart:`3px solid ${s.border}`, backgroundColor:s.bg }}
         className="rounded-lg px-3 py-2.5 space-y-1.5">
      <div className="flex items-start gap-2 flex-wrap">
        <span className="text-base leading-none">{section.emoji}</span>
        <span className="font-semibold text-sm" style={{ color:s.titleColor }}>{section.title}</span>
        {section.metadata && <span className="text-xs mt-px" style={{ color:s.metaColor }}>{section.metadata}</span>}
      </div>
      {(section.items ?? []).length > 0 && (
        <ul className="space-y-1">
          {section.items!.map((item, i) => (
            <li key={i} className="flex items-start gap-1.5 text-xs text-foreground">
              <span className="mt-0.5 shrink-0 font-bold" style={{ color:s.bulletColor }}>›</span>
              <FbItemValue text={item} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function FbKVCard({ section }: { section: FallbackSection }) {
  const pairs = (section.items ?? []).map(item => {
    const m = item.match(/^([^:]+):\s+(.+)$/);
    return m ? { key:m[1].trim(), val:m[2].trim() } : { key:item, val:"" };
  });
  return (
    <div className="rounded-lg overflow-hidden text-sm" style={{ border:"1px solid rgba(128,128,128,0.15)" }}>
      {pairs.map(({ key, val }, i) => (
        <div key={i} className="flex items-start"
             style={{ borderBottom: i < pairs.length-1 ? "1px solid rgba(128,128,128,0.10)" : undefined, backgroundColor: i%2!==0 ? "rgba(128,128,128,0.03)" : "transparent" }}>
          <div className="px-3 py-1.5 shrink-0 font-medium text-muted-foreground text-xs" style={{ width:"38%", borderRight:"1px solid rgba(128,128,128,0.10)" }}>{key}</div>
          <div className="px-3 py-1.5 flex-1 text-foreground text-xs">{val || "—"}</div>
        </div>
      ))}
    </div>
  );
}

function FbMetricCard({ section, isAr }: { section: FallbackSection; isAr: boolean }) {
  const dm = METRIC_DOMAIN[section.domain ?? "generic"];
  const label = isAr ? dm.label_ar : dm.label_en;
  const shown = (section.citations ?? []).slice(0, 12);
  const extra = (section.citations?.length ?? 0) - shown.length;
  return (
    <div className="rounded-lg p-3 space-y-2.5" style={{ backgroundColor:dm.bg, border:`1px solid ${dm.border}` }}>
      <div className="flex items-center gap-3">
        <span className="text-2xl font-bold leading-none" style={{ color:dm.color }}>{section.count ?? "—"}</span>
        <span className="font-semibold text-sm" style={{ color:dm.color }}>{label}</span>
      </div>
      {shown.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {shown.map((c, i) => <SourceChip key={i} code={c} />)}
          {extra > 0 && <span className="text-xs text-muted-foreground self-center">+{extra} more</span>}
        </div>
      )}
    </div>
  );
}

function FbProjectCard({ raw, index }: { raw: string; index: number }) {
  const nameM = raw.match(/^\*\*(.+?)\*\*\s*\((.+?)\)/);
  if (!nameM) return (
    <div className="flex gap-2 items-start p-2.5 rounded-lg text-sm"
         style={{ backgroundColor:"rgba(0,0,0,0.03)", border:"1px solid rgba(0,0,0,0.08)" }}>
      <span className="text-muted-foreground text-xs mt-0.5 shrink-0 font-mono">{index}.</span>
      <InlineText text={raw} />
    </div>
  );
  const [, name, code] = nameM;
  const rest = raw.slice(nameM[0].length).replace(/^\s*—?\s*/,"");
  const parts = rest.split("|").map(s => s.trim()).filter(Boolean);
  const statusStr = parts[0];
  const budgetPart = parts.find(p => /budget/i.test(p));
  const budget = budgetPart?.replace(/budget:\s*/i,"").trim();
  const extras = parts.filter(p => p !== parts[0] && p !== budgetPart);
  return (
    <div className="flex gap-2.5 items-start p-2.5 rounded-lg"
         style={{ backgroundColor:"rgba(0,0,0,0.03)", border:"1px solid rgba(0,0,0,0.08)" }}>
      <span className="text-muted-foreground text-xs mt-1 shrink-0 font-mono w-4 text-right">{index}</span>
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-sm text-foreground truncate">{name}</span>
          <CodeBadge code={code} />
          {statusStr && <StatusBadge status={statusStr} />}
        </div>
        {(budget || extras.length > 0) && (
          <div className="flex items-center gap-3 flex-wrap">
            {budget && <span className="text-xs font-semibold text-primary">{budget}</span>}
            {extras.map((e, i) => <span key={i} className="text-xs text-muted-foreground">{e}</span>)}
          </div>
        )}
      </div>
    </div>
  );
}

function FbParagraph({ section }: { section: FallbackSection }) {
  const text = section.text ?? "";
  const lines = text.split("\n").map(l => l.trim()).filter(Boolean);
  if (!lines.length) return null;
  const first = lines[0];
  const isProjectRef = /^\*\*[^*]+\*\*\s*\((?:PRJ|SE|NCR|PO|PR)-[\w\d]+\)/.test(first) || /^(?:Details? for|تفاصيل)\s+\*\*/.test(first);
  const isComparison = /^For comparison/i.test(first) || /^للمقارنة/i.test(first);
  if (isProjectRef || isComparison) {
    const m = first.match(/^\*\*(.+?)\*\*\s*\(([\w\d-]+)\)\s*[：:—]?\s*(.*)$/) ?? first.match(/^.+\*\*(.+?)\*\*\s*\(([\w\d-]+)\)\s*[：:—]?\s*(.*)$/);
    if (m) {
      const [, name, code, restFirst] = m;
      return (
        <div className="rounded-lg p-3 space-y-1.5"
             style={{ backgroundColor: isComparison ? "rgba(107,114,128,0.04)" : "rgba(59,130,246,0.05)", border: isComparison ? "1px solid rgba(128,128,128,0.15)" : "1px solid rgba(59,130,246,0.20)" }}>
          {isComparison && <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">vs</div>}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-foreground text-sm">{name}</span>
            <CodeBadge code={code} />
          </div>
          {(restFirst || lines.slice(1).length > 0) && (
            <p className="text-sm text-foreground leading-relaxed">
              {restFirst && <InlineText text={restFirst} />}
              {lines.slice(1).map((l, i) => <span key={i}> <InlineText text={l} /></span>)}
            </p>
          )}
        </div>
      );
    }
  }
  return (
    <div className="space-y-1">
      {lines.map((line, i) => (
        <p key={i} className="text-sm text-foreground leading-relaxed">
          <InlineText text={line} />
        </p>
      ))}
    </div>
  );
}

function FbSourcesRow({ citations, isAr }: { citations: string[]; isAr: boolean }) {
  const proj  = citations.filter(c => c.startsWith("PRJ-"));
  const se    = citations.filter(c => c.startsWith("SE-"));
  const ncr   = citations.filter(c => c.startsWith("NCR-"));
  const po    = citations.filter(c => c.startsWith("PO-") || c.startsWith("PR-"));
  const risk  = citations.filter(c => c.startsWith("#"));
  const rest  = citations.filter(c => !["PRJ-","SE-","NCR-","PO-","PR-","#"].some(p => c.startsWith(p)));
  const groups: [string, string[]][] = ([
    [isAr ? "مشاريع" : "Projects",   proj],
    [isAr ? "سلامة"  : "Safety",     se],
    [isAr ? "جودة"   : "NCR",        ncr],
    [isAr ? "مشتريات": "PO / PR",    po],
    [isAr ? "مخاطر"  : "Risks",      risk],
    ["",                               rest],
  ] as [string, string[]][]).filter(([, arr]) => arr.length > 0);
  return (
    <div className="flex flex-col gap-1.5 pt-2" style={{ borderTop:"1px solid rgba(128,128,128,0.12)" }}>
      <span className="text-xs text-muted-foreground uppercase tracking-wide font-medium">{isAr ? "المصادر" : "Sources"}</span>
      <div className="flex flex-col gap-1">
        {groups.map(([label, codes], gi) => (
          <div key={gi} className="flex items-start gap-1.5 flex-wrap">
            {label && <span className="text-xs text-muted-foreground shrink-0 mt-px">{label}:</span>}
            {(codes as string[]).map((c, i) => <SourceChip key={i} code={c} />)}
          </div>
        ))}
      </div>
    </div>
  );
}

function FallbackRenderer({ content, isAr }: { content: string; isAr: boolean }) {
  const sections = parseFallback(content);
  if (!sections.length) return <p className="text-sm text-foreground leading-relaxed whitespace-pre-wrap break-words">{content}</p>;
  const main = sections.filter(s => s.type !== "sources");
  const cites = [...new Set(sections.filter(s => s.type === "sources").flatMap(s => s.citations ?? []))];
  return (
    <div className="space-y-2.5 w-full">
      {main.map((s, i) => {
        switch (s.type) {
          case "title":    return <h3 key={i} className="font-semibold text-sm text-foreground pb-1.5" style={{ borderBottom:"1px solid rgba(128,128,128,0.15)" }}>{s.title}</h3>;
          case "risk":     return <FbRiskCard key={i} section={s} />;
          case "kv":       return <FbKVCard   key={i} section={s} />;
          case "metric":   return <FbMetricCard key={i} section={s} isAr={isAr} />;
          case "numbered": return <div key={i} className="space-y-2">{(s.items ?? []).map((item, j) => <FbProjectCard key={j} raw={item} index={j+1} />)}</div>;
          case "list":     return <ul key={i} className="space-y-1 ps-1">{(s.items ?? []).map((item, j) => <li key={j} className="flex items-start gap-2 text-sm text-foreground"><span className="text-primary mt-1.5 shrink-0 text-xs">•</span><FbItemValue text={item} /></li>)}</ul>;
          default:         return <FbParagraph key={i} section={s} />;
        }
      })}
      {cites.length > 0 && <FbSourcesRow citations={cites} isAr={isAr} />}
    </div>
  );
}

// ─── Public export ────────────────────────────────────────────────────────────

export function RichAnswer({
  content,
  isAr = false,
  renderBlocks: renderBlocksRaw,
}: {
  content: string;
  isAr?: boolean;
  renderBlocks?: Array<Record<string, unknown>> | null;
  comparisonData?: Record<string, unknown> | null; // kept for backward compat
}) {
  const renderBlocks = renderBlocksRaw as RenderBlock[] | null | undefined;

  // Primary path: structured blocks from backend
  if (renderBlocks && renderBlocks.length > 0) {
    return (
      <div className={cn("space-y-2.5 w-full")}>
        {renderBlocks.map((block, i) => (
          <BlockRenderer key={i} block={block} isAr={isAr} />
        ))}
      </div>
    );
  }

  // Fallback: parse content text
  if (!content?.trim()) return null;
  return <FallbackRenderer content={content} isAr={isAr} />;
}
