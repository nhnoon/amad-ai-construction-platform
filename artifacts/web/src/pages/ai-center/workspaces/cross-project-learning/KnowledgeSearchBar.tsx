import { useEffect, useState } from "react";
import { Search, Star, History, Sparkles } from "lucide-react";
import { SearchInput } from "@/components/search-input";
import { SUGGESTED_SEARCHES } from "@/lib/mockCrossProjectLearning";
import {
  getRecentSearches, addRecentSearch, getSavedSearches, toggleSavedSearch,
} from "./shared";

// Knowledge Search — a semantic-style search bar (keyword-matched under
// the hood, see mockCrossProjectLearning.ts's searchKnowledge) plus
// suggested / recent / saved searches. Recent and saved searches are
// genuinely functional client-side preferences (localStorage), not demo
// data — everything they operate on (the search results) is demo data.

export function KnowledgeSearchBar({
  value,
  onChange,
}: {
  value: string;
  onChange: (query: string) => void;
}) {
  const [recent, setRecent] = useState<string[]>([]);
  const [saved, setSaved] = useState<string[]>([]);

  useEffect(() => {
    setRecent(getRecentSearches());
    setSaved(getSavedSearches());
  }, []);

  const commit = (query: string) => {
    onChange(query);
    if (query.trim()) setRecent(addRecentSearch(query));
  };

  const isSaved = value.trim() && saved.some((s) => s.toLowerCase() === value.trim().toLowerCase());

  return (
    <div className="space-y-2.5">
      <div className="flex items-center gap-2">
        <div className="flex-1">
          <SearchInput
            value={value}
            onChange={onChange}
            placeholder='Ask a question — e.g. "rebar delivery delays" or "concrete quality issues"...'
            testId="input-knowledge-search"
          />
        </div>
        <button
          type="button"
          onClick={() => { if (value.trim()) { setSaved(toggleSavedSearch(value)); commit(value); } }}
          disabled={!value.trim()}
          className={`h-9 w-9 flex items-center justify-center rounded-lg border transition-colors shrink-0 disabled:opacity-40 ${
            isSaved ? "border-amber-400/60 bg-amber-500/10 text-amber-500" : "border-border text-muted-foreground hover:text-foreground"
          }`}
          aria-label={isSaved ? "Remove saved search" : "Save this search"}
          title={isSaved ? "Remove saved search" : "Save this search"}
        >
          <Star className={`w-4 h-4 ${isSaved ? "fill-current" : ""}`} />
        </button>
      </div>

      <div className="space-y-1.5">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground flex items-center gap-1"><Sparkles className="w-3 h-3" /> Suggested searches</p>
        <div className="flex flex-wrap gap-1.5">
          {SUGGESTED_SEARCHES.map((s) => (
            <button key={s} type="button" onClick={() => commit(s)} className="inline-flex items-center gap-1 rounded-full border border-border px-2.5 py-1 text-[11px] text-muted-foreground hover:border-primary/40 hover:text-foreground transition-colors">
              <Search className="w-2.5 h-2.5" /> {s}
            </button>
          ))}
        </div>
      </div>

      {(recent.length > 0 || saved.length > 0) && (
        <div className="flex flex-wrap gap-4">
          {recent.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground flex items-center gap-1"><History className="w-3 h-3" /> Recent searches</p>
              <div className="flex flex-wrap gap-1.5">
                {recent.map((s) => (
                  <button key={s} type="button" onClick={() => commit(s)} className="rounded-full bg-muted px-2.5 py-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors">{s}</button>
                ))}
              </div>
            </div>
          )}
          {saved.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground flex items-center gap-1"><Star className="w-3 h-3" /> Saved searches</p>
              <div className="flex flex-wrap gap-1.5">
                {saved.map((s) => (
                  <button key={s} type="button" onClick={() => commit(s)} className="inline-flex items-center gap-1 rounded-full border border-amber-400/40 bg-amber-500/5 px-2.5 py-1 text-[11px] text-amber-600 dark:text-amber-400 hover:border-amber-400/70 transition-colors">
                    <Star className="w-2.5 h-2.5 fill-current" /> {s}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
