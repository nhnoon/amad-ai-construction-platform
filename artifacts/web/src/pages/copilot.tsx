import { useState, useRef, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import {
  Bot, Send, Plus, Loader2,
  MessageSquare, AlertTriangle, BookOpen, Sparkles,
  ShieldAlert, ShoppingCart, ClipboardCheck,
  Briefcase, Users, RotateCcw, ChevronDown, ChevronUp,
  Layers, HelpCircle, Lightbulb,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { useAuth } from "@/context/AuthContext";
import { RichAnswer } from "@/components/CopilotAnswer";

// BASE is used only for in-app navigation links (citations, hrefs), NOT for API calls.
const BASE = (import.meta.env.BASE_URL ?? "/").replace(/\/$/, "");

interface Citation {
  id: number;
  source_type: string;
  source_id: string;
  label: string;
  evidence_snippet?: string;
  ui_metadata?: { href?: string; icon?: string };
}

interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  status?: string;
  citations?: Citation[];
  confidence?: string;
  intent?: string;
  isTyping?: boolean;
  timestamp?: string;
  // Phase 3B
  followUpSuggestions?: string[];
  clarificationRequired?: boolean;
  clarificationQuestion?: string;
  clarificationOptions?: string[];
  keyFindings?: string[];
  comparisonData?: Record<string, unknown> | null;
  domainsUsed?: string[];
  isMultiDomain?: boolean;
  resolvedQuery?: string;
  renderBlocks?: Array<Record<string, unknown>>;
}

interface ConversationStub {
  id: number;
  title: string;
  updated_at: string;
}

const SUGGESTED_PROMPTS = [
  { icon: Briefcase, key: "proj_status", en: "What is the status of active projects?", ar: "ما هو وضع المشاريع النشطة؟" },
  { icon: ShoppingCart, key: "late_pos", en: "Show me late purchase orders", ar: "أرني أوامر الشراء المتأخرة" },
  { icon: ShieldAlert, key: "safety", en: "Any recent safety events or incidents?", ar: "هل هناك أحداث سلامة أو حوادث حديثة؟" },
  { icon: ClipboardCheck, key: "site", en: "Recent site reports summary", ar: "ملخص التقارير الميدانية الأخيرة" },
  { icon: Users, key: "suppliers", en: "List our active suppliers", ar: "أرني قائمة الموردين النشطين" },
  { icon: Sparkles, key: "exec", en: "Give me an executive summary", ar: "أعطني ملخصاً تنفيذياً" },
];

const CONFIDENCE_COLORS: Record<string, string> = {
  high: "bg-emerald-500/15 text-emerald-500 border-emerald-500/30",
  medium: "bg-amber-500/15 text-amber-500 border-amber-500/30",
  low: "bg-muted text-muted-foreground border-border",
  none: "bg-muted text-muted-foreground border-border",
};

const INTENT_LABEL: Record<string, { en: string; ar: string }> = {
  project_overview: { en: "Projects", ar: "المشاريع" },
  procurement: { en: "Procurement", ar: "المشتريات" },
  suppliers: { en: "Suppliers", ar: "الموردون" },
  safety: { en: "Safety", ar: "السلامة" },
  ncr: { en: "NCR", ar: "عدم المطابقة" },
  site_reports: { en: "Site Reports", ar: "تقارير الموقع" },
  meetings: { en: "Meetings", ar: "الاجتماعات" },
  decisions: { en: "Decisions", ar: "القرارات" },
  risks: { en: "Risks", ar: "المخاطر" },
  executive_summary: { en: "Executive Summary", ar: "ملخص تنفيذي" },
};

// ── Small helper: timestamp ────────────────────────────────────────────────
function formatTime(ts?: string): string {
  if (!ts) return "";
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// ── Citations section (expandable) ────────────────────────────────────────
function CitationsSection({ citations, lang }: { citations: Citation[]; lang: string }) {
  const [expanded, setExpanded] = useState(false);
  if (!citations.length) return null;

  return (
    <div className="border-t border-border/50 mt-2 pt-2">
      <button
        onClick={() => setExpanded((p) => !p)}
        className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <BookOpen className="w-3 h-3" />
        <span>
          {lang === "ar"
            ? `${citations.length} مصدر`
            : `${citations.length} source${citations.length !== 1 ? "s" : ""}`}
        </span>
        {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>

      {expanded && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {citations.map((cit) => {
            const href = cit.ui_metadata?.href;
            const inner = (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary/10 text-primary text-xs border border-primary/20 cursor-pointer hover:bg-primary/20 transition-colors">
                <BookOpen className="w-3 h-3" />
                {cit.label}
              </span>
            );
            if (href) {
              return (
                <a key={cit.id} href={`${BASE}${href}`} className="no-underline">
                  {inner}
                </a>
              );
            }
            return <span key={cit.id}>{inner}</span>;
          })}
        </div>
      )}
    </div>
  );
}

// ── Confidence badge with tooltip ─────────────────────────────────────────
function ConfidenceBadge({ confidence, lang }: { confidence: string; lang: string }) {
  const labels: Record<string, { en: string; ar: string; tip: string }> = {
    high: { en: "High confidence", ar: "ثقة عالية", tip: "Answer is well-supported by platform evidence" },
    medium: { en: "Medium confidence", ar: "ثقة متوسطة", tip: "Answer is partially supported" },
    low: { en: "Low confidence", ar: "ثقة منخفضة", tip: "Limited evidence available" },
    none: { en: "No evidence", ar: "لا أدلة", tip: "No matching records found" },
  };
  const label = lang === "ar" ? labels[confidence]?.ar : labels[confidence]?.en;
  const tip = labels[confidence]?.tip ?? "";
  return (
    <span
      title={tip}
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border cursor-help",
        CONFIDENCE_COLORS[confidence]
      )}
    >
      <Sparkles className="w-3 h-3" />
      {label}
    </span>
  );
}

// ── Key findings list ──────────────────────────────────────────────────────
function KeyFindingsList({ findings, lang }: { findings: string[]; lang: string }) {
  if (!findings.length) return null;
  return (
    <div className="mt-2 p-2.5 rounded-lg bg-muted/50 border border-border/60 space-y-1">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1.5">
        {lang === "ar" ? "الاستنتاجات الرئيسية" : "Key Findings"}
      </p>
      {findings.map((f, i) => (
        <div key={i} className="flex items-start gap-2 text-xs text-foreground">
          <span className="text-primary mt-0.5">•</span>
          <span>{f}</span>
        </div>
      ))}
    </div>
  );
}

// ── Clarification chips ───────────────────────────────────────────────────
function ClarificationChips({
  question,
  options,
  onSelect,
  lang,
}: {
  question: string;
  options: string[];
  onSelect: (q: string) => void;
  lang: string;
}) {
  return (
    <div className="mt-3 space-y-2">
      <div className="flex items-center gap-1.5 text-xs text-amber-500 font-medium">
        <HelpCircle className="w-3.5 h-3.5" />
        <span>{question}</span>
      </div>
      {options.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {options.map((opt, i) => (
            <button
              key={i}
              onClick={() => onSelect(opt)}
              className="px-3 py-1 rounded-full text-xs border border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400 hover:bg-amber-500/20 transition-colors"
            >
              {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Follow-up suggestion chips ────────────────────────────────────────────
function FollowUpChips({
  suggestions,
  onSelect,
  lang,
}: {
  suggestions: string[];
  onSelect: (q: string) => void;
  lang: string;
}) {
  if (!suggestions.length) return null;
  return (
    <div className="mt-3 space-y-1.5">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Lightbulb className="w-3 h-3" />
        <span>{lang === "ar" ? "اقتراحات للمتابعة" : "Follow-up suggestions"}</span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {suggestions.map((s, i) => (
          <button
            key={i}
            onClick={() => onSelect(s)}
            className="px-3 py-1 rounded-full text-xs border border-primary/25 bg-primary/8 text-primary hover:bg-primary/15 hover:border-primary/40 transition-colors"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Multi-domain indicator ────────────────────────────────────────────────
function DomainBadges({ domains, lang }: { domains: string[]; lang: string }) {
  if (domains.length <= 1) return null;
  return (
    <div className="flex items-center gap-1 flex-wrap">
      <Layers className="w-3 h-3 text-muted-foreground" />
      {domains.map((d) => (
        <span key={d} className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border/50">
          {INTENT_LABEL[d]?.en ?? d}
        </span>
      ))}
    </div>
  );
}

// ── Loading skeleton ──────────────────────────────────────────────────────
function TypingBubble() {
  return (
    <div className="flex items-start gap-3">
      <div className="w-8 h-8 rounded-full bg-primary/15 flex items-center justify-center shrink-0">
        <Bot className="w-4 h-4 text-primary" />
      </div>
      <div className="bg-card border border-border rounded-2xl rounded-tl-sm px-4 py-3">
        <div className="flex gap-1 items-center h-4">
          <span className="w-2 h-2 bg-primary/60 rounded-full animate-bounce [animation-delay:0ms]" />
          <span className="w-2 h-2 bg-primary/60 rounded-full animate-bounce [animation-delay:150ms]" />
          <span className="w-2 h-2 bg-primary/60 rounded-full animate-bounce [animation-delay:300ms]" />
        </div>
      </div>
    </div>
  );
}

// ── Message bubble ────────────────────────────────────────────────────────
function MessageBubble({
  msg,
  lang,
  onSuggestionClick,
}: {
  msg: Message;
  lang: string;
  onSuggestionClick: (q: string) => void;
}) {
  const isUser = msg.role === "user";
  const isInsufficient =
    msg.status === "insufficient_evidence" || msg.status === "grounding_failed";
  const isError =
    msg.status === "provider_unavailable" || msg.status === "provider_error";
  const isUnsupported = msg.status === "unsupported_intent";
  const isClarification = msg.status === "clarification_required";

  if (msg.isTyping) return <TypingBubble />;

  return (
    <div className={cn("flex items-start gap-3 group", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
          isUser ? "bg-primary text-primary-foreground" : "bg-primary/15"
        )}
      >
        {isUser ? (
          <span className="text-xs font-bold">U</span>
        ) : (
          <Bot className="w-4 h-4 text-primary" />
        )}
      </div>

      <div
        className={cn(
          "rounded-2xl px-4 py-3 space-y-2",
          isUser
            ? "max-w-[80%] bg-primary text-primary-foreground rounded-tr-sm"
            : cn(
                "w-full sm:max-w-[92%] bg-card border border-border rounded-tl-sm",
                isInsufficient && "border-amber-500/30 bg-amber-500/5",
                isError && "border-red-500/30 bg-red-500/5",
                isClarification && "border-blue-500/30 bg-blue-500/5",
              )
        )}
      >
        {!isUser && (isInsufficient || isError) && (
          <div className="flex items-center gap-1.5 text-xs text-amber-500 font-medium">
            <AlertTriangle className="w-3.5 h-3.5" />
            {lang === "ar"
              ? isError
                ? "الخدمة غير متاحة"
                : "أدلة غير كافية"
              : isError
              ? "Service unavailable"
              : "Insufficient evidence"}
          </div>
        )}

        {isUser ? (
          <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">{msg.content}</p>
        ) : (
          <RichAnswer
            content={msg.content}
            isAr={lang === "ar"}
            comparisonData={msg.comparisonData as Record<string, unknown> | null}
            renderBlocks={msg.renderBlocks as Array<Record<string, unknown>>}
          />
        )}

        {/* Key findings */}
        {!isUser && msg.keyFindings && msg.keyFindings.length > 0 && (
          <KeyFindingsList findings={msg.keyFindings} lang={lang} />
        )}

        {/* Intent + confidence row */}
        {!isUser && msg.intent && (
          <div className="flex items-center gap-2 pt-1 flex-wrap">
            {INTENT_LABEL[msg.intent] && (
              <span className="text-xs text-muted-foreground px-2 py-0.5 rounded-full bg-muted border border-border">
                {lang === "ar"
                  ? INTENT_LABEL[msg.intent].ar
                  : INTENT_LABEL[msg.intent].en}
              </span>
            )}
            {msg.confidence && msg.confidence !== "none" && (
              <ConfidenceBadge confidence={msg.confidence} lang={lang} />
            )}
            {msg.domainsUsed && msg.domainsUsed.length > 1 && (
              <DomainBadges domains={msg.domainsUsed} lang={lang} />
            )}
          </div>
        )}

        {/* Citations — expandable */}
        {!isUser && msg.citations && msg.citations.length > 0 && (
          <CitationsSection citations={msg.citations} lang={lang} />
        )}

        {/* Clarification chips */}
        {!isUser && isClarification && msg.clarificationOptions && (
          <ClarificationChips
            question={msg.clarificationQuestion ?? msg.content}
            options={msg.clarificationOptions}
            onSelect={onSuggestionClick}
            lang={lang}
          />
        )}

        {/* Follow-up suggestion chips */}
        {!isUser &&
          !isClarification &&
          msg.followUpSuggestions &&
          msg.followUpSuggestions.length > 0 && (
            <FollowUpChips
              suggestions={msg.followUpSuggestions}
              onSelect={onSuggestionClick}
              lang={lang}
            />
          )}

        {/* Timestamp */}
        {msg.timestamp && (
          <p
            className={cn(
              "text-[10px] opacity-40 select-none",
              isUser ? "text-right text-primary-foreground" : "text-muted-foreground"
            )}
          >
            {formatTime(msg.timestamp)}
          </p>
        )}
      </div>
    </div>
  );
}

// ── Empty / welcome state ─────────────────────────────────────────────────
function EmptyState({ onPrompt, lang }: { onPrompt: (q: string) => void; lang: string }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4 py-12 gap-8">
      <div className="flex flex-col items-center gap-3 text-center">
        <div className="w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center">
          <Bot className="w-8 h-8 text-primary" />
        </div>
        <h2 className="text-xl font-semibold text-foreground">
          {lang === "ar" ? "مرحباً بك في مساعد عَمَد" : "Welcome to Amad Copilot"}
        </h2>
        <p className="text-sm text-muted-foreground max-w-sm">
          {lang === "ar"
            ? "اطرح أسئلة متعددة الأدوار حول المشاريع، المشتريات، السلامة، الموردين، والتقارير."
            : "Ask multi-turn questions about projects, procurement, safety, suppliers, site reports, and meetings."}
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
        {SUGGESTED_PROMPTS.map(({ icon: Icon, key, en, ar }) => (
          <button
            key={key}
            onClick={() => onPrompt(lang === "ar" ? ar : en)}
            className="flex items-start gap-3 p-3 rounded-xl border border-border bg-card hover:bg-muted/50 hover:border-primary/30 text-start transition-all group"
          >
            <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 group-hover:bg-primary/20 transition-colors">
              <Icon className="w-3.5 h-3.5 text-primary" />
            </div>
            <span className="text-xs text-muted-foreground group-hover:text-foreground transition-colors leading-relaxed">
              {lang === "ar" ? ar : en}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────
// `compact` is opt-in only (AI Center's Copilot tab passes it) — default
// behavior at the standalone /copilot route is unchanged. `projectId` is
// opt-in too (Project Workspace's "Ask Hermes" tab passes it) — when set,
// every query is scoped server-side via CopilotQueryRequest.project_id
// (already supported by /copilot/query; just never sent from the UI
// before this).
export default function CopilotPage({
  compact = false, projectId, projectLabel,
}: { compact?: boolean; projectId?: number; projectLabel?: string } = {}) {
  const { i18n } = useTranslation();
  const lang = i18n.language ?? "en";
  const isRTL = lang === "ar";

  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [conversations, setConversations] = useState<ConversationStub[]>([]);

  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { token } = useAuth();

  // Synchronous, immediate re-entry guard for sendMessage — separate from
  // the `isLoading` state flag. `isLoading` only takes effect once React
  // has committed the state update and re-rendered (so `disabled={isLoading}`
  // reflects it); a ref is readable/writable synchronously the instant
  // sendMessage starts, closing the gap where two triggers firing in the
  // same tick (e.g. Enter key + a queued click) could both read a stale
  // `isLoading=false` and both issue the request.
  const sendingRef = useRef(false);

  const fetchConversations = useCallback(async () => {
    if (!token) return;
    try {
      const resp = await fetch(`/api/v1/ai/conversations?limit=30`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (resp.ok) setConversations(await resp.json());
    } catch {}
  }, [token]);

  useEffect(() => { fetchConversations(); }, [fetchConversations]);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const sendMessage = async (q: string) => {
    if (!q.trim() || isLoading || sendingRef.current) return;
    sendingRef.current = true;
    setError(null);

    const now = new Date().toISOString();
    const userMsg: Message = {
      id: Date.now(),
      role: "user",
      content: q.trim(),
      timestamp: now,
    };
    const typingMsg: Message = {
      id: Date.now() + 1,
      role: "assistant",
      content: "",
      isTyping: true,
    };

    setMessages((prev) => [...prev, userMsg, typingMsg]);
    setQuestion("");
    setIsLoading(true);

    try {
      const resp = await fetch(`/api/v1/ai/copilot/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          question: q.trim(),
          conversation_id: conversationId ?? undefined,
          project_id: projectId,
        }),
      });

      if (!resp.ok) {
        let errMsg: string;
        if (resp.status === 401) {
          errMsg = isRTL
            ? "انتهت صلاحية جلستك. يُرجى تسجيل الدخول من جديد."
            : "Your session has expired. Please sign in again.";
        } else if (resp.status === 403) {
          errMsg = isRTL
            ? "ليس لديك صلاحية لهذا الإجراء."
            : "You don't have permission to perform this action.";
        } else if (resp.status === 429) {
          errMsg = isRTL
            ? "لقد تجاوزت حد الطلبات. يُرجى الانتظار لحظة."
            : "Rate limit reached. Please wait a moment.";
        } else if (resp.status === 503 || resp.status === 502) {
          errMsg = isRTL
            ? "خدمة الذكاء الاصطناعي غير متاحة مؤقتاً."
            : "AI service is temporarily unavailable.";
        } else {
          errMsg = isRTL
            ? "حدث خطأ في الخادم. يُرجى المحاولة مجدداً."
            : "A server error occurred. Please try again.";
        }
        setError(errMsg);
        setMessages((prev) => prev.filter((m) => !m.isTyping));
        return;
      }

      const data = await resp.json();
      if (!conversationId) {
        setConversationId(data.conversation_id);
        fetchConversations();
      }

      const assistantMsg: Message = {
        id: data.message_id,
        role: "assistant",
        content: data.answer,
        status: data.status,
        citations: data.citations ?? [],
        confidence: data.confidence,
        intent: data.intent,
        timestamp: new Date().toISOString(),
        // Phase 3B
        followUpSuggestions: data.follow_up_suggestions ?? [],
        clarificationRequired: data.clarification_required ?? false,
        clarificationQuestion: data.clarification_question ?? undefined,
        clarificationOptions: data.clarification_options ?? [],
        keyFindings: data.key_findings ?? [],
        comparisonData: data.comparison_data ?? null,
        domainsUsed: data.domains_used ?? [],
        isMultiDomain: data.is_multi_domain ?? false,
        resolvedQuery: data.resolved_query ?? undefined,
        renderBlocks: data.render_blocks ?? [],
      };

      setMessages((prev) =>
        prev.filter((m) => !m.isTyping).concat(assistantMsg)
      );
    } catch {
      setError(
        isRTL ? "حدث خطأ في الاتصال." : "Connection error. Please try again."
      );
      setMessages((prev) => prev.filter((m) => !m.isTyping));
    } finally {
      setIsLoading(false);
      sendingRef.current = false;
    }
  };

  const startNew = () => {
    setMessages([]);
    setConversationId(null);
    setError(null);
    textareaRef.current?.focus();
  };

  const openConversation = async (id: number) => {
    if (!token) return;
    setConversationId(id);
    setError(null);
    try {
      const resp = await fetch(`/api/v1/ai/conversations/${id}/messages`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (resp.ok) {
        const data: Array<{
          id: number;
          role: string;
          content: string;
          status: string;
          domains_used?: string[];
        }> = await resp.json();
        setMessages(
          data.map((m) => ({
            id: m.id,
            role: m.role as "user" | "assistant",
            content: m.content,
            status: m.status,
            domainsUsed: m.domains_used ?? [],
          }))
        );
      }
    } catch {}
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(question);
    }
  };

  const handleSuggestionClick = (q: string) => {
    setQuestion("");
    sendMessage(q);
  };

  return (
    <div
      className={cn(
        "flex overflow-hidden",
        compact ? "h-[75vh] min-h-[480px] rounded-lg border border-border" : "h-[calc(100vh-64px)]",
        isRTL && "direction-rtl"
      )}
      dir={isRTL ? "rtl" : "ltr"}
    >
      {/* ── Sidebar ──────────────────────────────────────────────────── */}
      <aside
        className={cn(
          "w-64 border-border bg-card flex-col transition-all duration-200",
          "hidden md:flex border-r",
          isRTL && "md:border-r-0 md:border-l"
        )}
      >
        <div className="p-3 border-b border-border">
          <Button
            variant="default"
            size="sm"
            className="w-full gap-2 justify-start"
            onClick={startNew}
          >
            <Plus className="w-4 h-4" />
            {isRTL ? "محادثة جديدة" : "New conversation"}
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {conversations.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-6">
              {isRTL ? "لا توجد محادثات" : "No conversations yet"}
            </p>
          ) : (
            conversations.map((conv) => (
              <button
                key={conv.id}
                onClick={() => openConversation(conv.id)}
                className={cn(
                  "w-full text-start px-3 py-2 rounded-lg text-xs hover:bg-muted/60 transition-colors space-y-0.5",
                  conversationId === conv.id && "bg-primary/10 text-primary"
                )}
              >
                <div className="flex items-start gap-2">
                  <MessageSquare className="w-3.5 h-3.5 shrink-0 mt-0.5 opacity-60" />
                  <span className="truncate">{conv.title}</span>
                </div>
                <p className="text-[10px] text-muted-foreground opacity-60 ps-5">
                  {new Date(conv.updated_at).toLocaleDateString(
                    isRTL ? "ar-SA" : "en-US",
                    { month: "short", day: "numeric" }
                  )}
                </p>
              </button>
            ))
          )}
        </div>

        <div className="p-3 border-t border-border">
          <p className="text-xs text-muted-foreground text-center opacity-60">
            {isRTL ? "مساعد عَمَد · قراءة فقط" : "Amad Copilot · Read-only"}
          </p>
        </div>
      </aside>

      {/* ── Main chat area ───────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border bg-card shrink-0">
          <div className="w-8 h-8 rounded-xl bg-primary/10 flex items-center justify-center">
            <Bot className="w-4 h-4 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-sm font-semibold text-foreground">
              {isRTL ? "مساعد عَمَد الذكي" : "Amad Copilot"}
            </h1>
            <p className="text-xs text-muted-foreground">
              {projectLabel
                ? `${isRTL ? "نطاق المشروع" : "Scoped to"}: ${projectLabel}`
                : isRTL
                  ? "استخبارات البناء متعدد الأدوار · قراءة فقط"
                  : "Multi-turn Construction Intelligence · Read-only"}
            </p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={startNew}
            className="gap-2 hidden sm:flex"
          >
            <Plus className="w-4 h-4" />
            {isRTL ? "جديد" : "New"}
          </Button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
          {messages.length === 0 ? (
            <EmptyState onPrompt={(q) => sendMessage(q)} lang={lang} />
          ) : (
            messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                msg={msg}
                lang={lang}
                onSuggestionClick={handleSuggestionClick}
              />
            ))
          )}

          {error && (
            <div className="flex items-center gap-3 p-3 rounded-xl bg-destructive/10 border border-destructive/30">
              <AlertTriangle className="w-4 h-4 text-destructive shrink-0" />
              <p className="text-sm text-destructive">{error}</p>
              <button
                onClick={() => {
                  setError(null);
                  const last = messages.findLast((m) => m.role === "user");
                  if (last) sendMessage(last.content);
                }}
                className="ms-auto shrink-0"
                aria-label="Retry last message"
              >
                <RotateCcw className="w-4 h-4 text-destructive/70 hover:text-destructive transition-colors" />
              </button>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="shrink-0 border-t border-border bg-card px-4 py-3">
          <div className="flex items-end gap-2 max-w-3xl mx-auto">
            <Textarea
              ref={textareaRef}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                isRTL
                  ? "اسأل سؤالاً متعدد الأدوار عن المشاريع، المشتريات، السلامة…"
                  : "Ask a multi-turn question about projects, procurement, safety…"
              }
              className="resize-none min-h-[48px] max-h-[120px] text-sm bg-background border-border rounded-xl"
              rows={1}
              disabled={isLoading}
            />
            <Button
              size="icon"
              onClick={() => sendMessage(question)}
              disabled={!question.trim() || isLoading}
              className="shrink-0 rounded-xl w-10 h-10"
              aria-label="Send message"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className={cn("w-4 h-4", isRTL && "scale-x-[-1]")} />
              )}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground text-center mt-2 opacity-50">
            {isRTL
              ? "المساعد يجيب بناءً على بيانات المنصة فقط — للقراءة فقط."
              : "Answers are grounded in platform data only — read-only."}
          </p>
        </div>
      </div>
    </div>
  );
}
