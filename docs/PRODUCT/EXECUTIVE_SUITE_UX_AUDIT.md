# Executive Suite — UX/Product Audit

**Scope:** Executive Dashboard (`/`), Reports (`/reports`), Executive
Intelligence (`/ai-center/executive`), Executive Decision Center
(`/ai-center/executive-decision-center`) — evaluated together as one
connected experience, the way a paying customer's executive sponsor would
actually use them in a single session. No code was changed to produce this
document; every finding is a direct read of the current implementation.

**Method:** each page was re-read in full (component tree, data hooks,
props actually rendered) rather than assessed from memory, specifically to
check cross-page consistency — the thing a single-page review can't catch.

---

## Executive summary

The four pages are visually unified — all four now open with the same
`PageHero`, use the same `InsightPanel` for their dominant brief and their
recommended actions, and share loading/panel chrome. That work is real and
holding up. But **treating them as one connected suite** — which is what
was asked of this audit — surfaces a different picture: **the suite has no
shared identity in the product's own navigation, no page links to any of
the other three, and the flagship page (Executive Decision Center) shows a
portfolio health score, risk counts, and recommended actions that do not
match the other three pages**, because it runs on an isolated demo-data
generator instead of the real data the other three share. For a commercial
buyer, an executive who checks the Dashboard, then opens Decision Center to
act on it, would see different numbers with no page telling them why.

**Top 5 findings, by business impact:**

1. **No navigation connects the four pages to each other or signals they're
   a suite** — Critical. See §2.
2. **Executive Decision Center's headline numbers don't match Dashboard's,
   with no on-page explanation** — Critical. See §5, §10.
3. **"Generated at" on Executive Decision Center is a frozen constant, not
   a live timestamp** — High. See §6.
4. **Executive Intelligence has no error state** — Medium-High. See §6.
5. **"Recommended Actions" means three different things on three
   different pages, all under the same label** — High. See §5.

---

## 1. Information hierarchy

Within each individual page, hierarchy is now strong and consistent: hero
→ dominant brief → decision-critical lists → supporting context →
recommended action → navigation-out. That's a direct result of the last
three migration passes and it's the audit's clearest strength.

Across the four pages, hierarchy breaks down — there is no signal telling
a user which of the four is the "primary" page versus a deeper-dive or a
formal-output page.

| Severity | Issue | Why it matters | Suggested improvement | Expected business impact |
|---|---|---|---|---|
| Medium | No visual or textual cue distinguishes "daily glance" (Dashboard), "AI lens" (Executive Intelligence), "decision workspace" (Decision Center), and "formal document" (Reports) — all four read as equally weighted destinations. | A new executive user has no way to know which page to start on, or why there are four instead of one. | A one-line descriptor pattern already exists (`PageHero`'s `description`) — use it to state each page's relationship to the others, e.g. Decision Center's description could open with "The deep-dive workspace for Dashboard's flagged items." | Faster time-to-value for new admins during onboarding/demo — directly affects sales-cycle conversion for a B2B trial. |
| Low | Executive Decision Center's own internal hierarchy is now good, but at ~11 stacked sections it's the longest scroll of the four despite being the one meant for daily decision-making. | The page most in need of "surface only what changes a decision" is still the longest single scroll in the suite. | See §8 (progressive disclosure) for a concrete mechanism. | Reduces daily-use friction on the page explicitly positioned as the flagship feature. |

---

## 2. Navigation flow

This is the audit's single largest gap.

| Severity | Issue | Why it matters | Suggested improvement | Expected business impact |
|---|---|---|---|---|
| **Critical** | The four pages do not link to each other as a group. Dashboard links only to Reports. Executive Intelligence links only to Reports. Reports and Executive Decision Center link to neither of the other three. There is no page that links to Executive Decision Center at all — not even Dashboard, despite Decision Center being the page an executive is meant to act on. | A user has to already know all four pages exist and go back to the sidebar every time. The page explicitly called "the screen an executive opens before making any portfolio-level decision" is unreachable from the page executives actually land on first. | Add a consistent small "suite" cross-link set — e.g. Dashboard's hero or KPI row gains a "Open Decision Center (N pending)" action; Executive Intelligence and Decision Center link to each other ("real-data view" ↔ "decision workspace"). | This is the difference between a demo that impresses once and a tool people actually adopt daily — navigation friction is a top-cited reason enterprise BI tools get abandoned after initial rollout. |
| **Critical** | The four pages live in three different sidebar locations — Dashboard (top-level), Reports (Analytics), Executive Intelligence (AI Center → Per-Entity, cross-listed under Analytics as "Insights"), Executive Decision Center (AI Center → Flagship Modules). Nothing in the shipped navigation groups them as "the Executive Suite" — that grouping exists only in how this work has been discussed, not in the product. | A buyer evaluating "executive features" during a trial has to already know to look in three different sidebar sections to find all four. | Not a redesign call to make unilaterally — but worth a deliberate product decision: either a literal "Executive Suite" sidebar entry, or accept these as four independent features and stop referring to them internally as one suite. | Directly affects how a sales demo is narrated and how a trial admin self-discovers the paid-tier value. |
| Medium | Reports and Executive Intelligence lost their explicit "Back to Dashboard" affordance when they moved from `PageContextHeader`/`WorkspaceLayout` (which had a back button and breadcrumb) to `PageHero` (which has neither). The sidebar still gets a user back to Dashboard, but the one-click in-page path is gone. | A minor but real regression introduced by the last three migrations, worth a deliberate call rather than an accidental loss. | `PageHero` doesn't currently support a back-link slot; either add one (affects the shared primitive, out of scope for a single-page pass) or accept the sidebar as sufficient. | Small, but consistent "how do I get back" friction compounds across a session. |

---

## 3. Cognitive load

| Severity | Issue | Why it matters | Suggested improvement | Expected business impact |
|---|---|---|---|---|
| Medium | Executive Decision Center still renders all ~11 sections fully expanded on every visit — filters narrow content but nothing is collapsed by default. | The page positioned for daily executive use asks for the same scroll depth every single time, regardless of whether anything changed since the last visit. | Default-collapse the two deepest/least time-sensitive sections (Executive Heat Map, Cross-Module Highlights) behind a "Show more" — see §8. | Daily-use tools live or die on how fast the "nothing needs me today" read takes; right now that read requires a full scroll every time. |
| Low | Reports renders 10 full sections on every load, several of which ("No procurement blockers detected," "No safety concerns") are just positive-empty-state filler when a portfolio is healthy. | Not wrong — a report should be complete — but on a healthy-portfolio week, a third of the page is "nothing to report" boilerplate. | Acceptable as-is given Reports' role as a formal, printable document (completeness matters more than density here) — flagged for awareness, not necessarily action. | Low; Reports' audience (weekly/board cadence) tolerates more length than a daily tool would. |
| Low | Dashboard and Executive Intelligence are both appropriately lean — this is working as intended and is called out here as a positive, not an issue. | — | — | — |

---

## 4. Visual consistency

| Severity | Issue | Why it matters | Suggested improvement | Expected business impact |
|---|---|---|---|---|
| Medium | Three different "small stat card" components are in play across the suite: `KpiStat` (Dashboard, Reports), `StatTile` (Executive Decision Center's `ExecutiveOverview`), and no stat strip at all on Executive Intelligence. | A user moving between pages sees the portfolio's vitals presented in three visually distinct shapes with no shared visual anchor. | Standardize on `KpiStat` across the suite (it's the newer, richer primitive); Executive Intelligence's omission was a deliberate anti-redundancy call (see §5) and can stay, but Decision Center's `StatTile` usage is an inconsistency worth reconciling. | Consistency is what makes a multi-page suite *read* like one product instead of four screens bolted together — directly visible in any demo. |
| Medium | Three independent implementations of the same `{icon, title, subtitle, action} → bordered panel-header` component now exist: Reports' `PanelHeader`, Executive Intelligence's `SectionShell`, Decision Center's `SectionPanel`. Visually identical today by construction, but nothing enforces that they stay identical as each page evolves independently. | Not a user-visible issue *today* — flagged here because "visual consistency" as an ongoing property, not a one-time state, depends on this kind of duplication being resolved before the pages next diverge. | Extract one shared primitive (`components/PanelHeader.tsx` or similar) and point all three at it — pure refactor, zero visual change, tracked as a candidate since the first migration pass. | Prevents future silent drift; the cost of fixing this grows every time one of the three copies gets edited without the other two being remembered. |
| Low | The portfolio health/status figure renders in four *different* visual forms across the suite: a `KpiStat` tile (Dashboard), a large centered number + status pill (Reports), a plain inline sentence (Executive Intelligence), and a circular gauge (Decision Center). | Each form is well-suited to its own page, but a user pattern-matching "where's the health score" has to re-learn the visual language every time. | Not necessarily wrong to vary by context — flagged for product judgment rather than as a clear-cut fix. | Minor; more a polish item than a trust or usability issue on its own. |

---

## 5. Repeated information

This is where the suite's "four separate builds sharing a design system" origin shows most clearly — several concepts are computed or shown more than once, sometimes from the *same* data, sometimes from *different* data that happens to share a label.

| Severity | Issue | Why it matters | Suggested improvement | Expected business impact |
|---|---|---|---|---|
| **Critical** | "Recommended Actions" / "Suggested Actions" means three different things: Reports and Executive Intelligence both render the exact same `report.recommended_actions` field (identical data, different card styling) — while Executive Decision Center's "Recommended Executive Actions" renders a completely separate, hand-authored demo list (`ACTION_TEMPLATES`) that has no relationship to the other two. | An executive who reads recommended actions on Executive Intelligence, then opens Decision Center expecting the same (or an expanded) list, sees an entirely different, unrelated set under the identical heading. This is the kind of inconsistency that reads as a bug in a paid product, not a design choice. | At minimum, rename Decision Center's section to signal it's illustrative-only (its `DemoDataBadge` already does this at the data level, but the *heading* doesn't); longer-term, this is the strongest case in the whole audit for wiring Decision Center to the real `recommended_actions` data instead of its own generator. | Directly a trust issue — the fastest way to lose an executive buyer's confidence in an "AI-powered" product is to show it contradicting itself under the same label. |
| High | Portfolio score/status is computed and displayed four times: Dashboard's `KpiStat`, Reports' brief panel, Executive Intelligence's inline sentence — all three from the same real `useExecutive()`/`useExecutiveWeeklyReport()` data and therefore consistent with each other — versus Decision Center's health gauge, which is a *different number* from an isolated demo generator. | Three pages agree; the fourth (the flagship one) doesn't, and nothing on Decision Center explains that its score is illustrative rather than "the real number, recomputed." | Same underlying fix as above — either visibly frame Decision Center's score as illustrative in the number's own label (not just a badge elsewhere on the page), or feed it real data. | Same trust-erosion risk as the actions finding, specifically on the single most attention-grabbing number on the page. |
| High | "Which projects need attention" is shown with three different underlying datasets across the suite: Dashboard and Executive Intelligence both use the real `attention_required` field (consistent with each other); Reports uses `top_priorities` (a real but *different* field — "worst-performing," not necessarily the same set); Decision Center uses a fully separate demo-generated risk ranking. | Three different "list of concerning projects," three different possible answers to "what's my most urgent project right now," depending on which of the four pages happens to be open. | Worth a product decision on whether `attention_required` and `top_priorities` are supposed to be the same concept (in which case reconcile them) or genuinely different lenses (in which case each page should say which lens it's using, not just show a bare list). | Executives cross-reference numbers between screens during real decisions; silently-different "most urgent" lists undermine confidence fast. |
| Medium | "Biggest Risks" / "Top Risks" appears on Dashboard (chart), Reports (progress bars), and Executive Intelligence (cards) — all three from the same real `biggest_risks` field, so at least internally consistent, but shown in three unrelated visual forms with no indication it's the same underlying list. | Less severe than the above since the data agrees — but a user has no way to know these three are the same list without comparing item-by-item. | Low-cost fix: a consistent small chart or list treatment (or at minimum consistent ordering/labeling) across the three would make the "same data" relationship visible instead of coincidental. | Reinforces trust once a user notices the numbers *do* agree — currently that reinforcement is accidental, not designed. |

---

## 6. Missing information

| Severity | Issue | Why it matters | Suggested improvement | Expected business impact |
|---|---|---|---|---|
| High | Dashboard — the page every executive lands on first — never surfaces that decisions are pending anywhere in the suite. `pendingDecisions` is computed and shown on Decision Center's overview but has no analog on Dashboard. | The entry point to the "flagship" decision-support feature gives no hint that there's anything to decide, undermining the whole premise of positioning Decision Center as where executives are guided to act. | Add a decision-pending count to Dashboard, linked to Decision Center (this also directly fixes the §2 navigation gap in one move). | Directly increases the odds an executive actually visits the flagship feature instead of never discovering it needs a click. |
| High | Executive Decision Center's "Generated {timestamp}" (shown twice — filter row area and footer) is not a live timestamp. `generateExecutiveDecisionCenter`'s `referenceMs` parameter defaults to a hardcoded constant (`Date.UTC(2026, 6, 28)`), and the hook that calls it never passes a real one — so the "Generated at" label will show the same fixed date on every visit, indefinitely, regardless of when the page is actually opened. | A "Generated at [timestamp]" label reads as a live-data freshness indicator. Once the real calendar date passes the hardcoded one, this becomes a visibly wrong, static-looking date on a page marketed as AI-driven — a specific, findable bug in a demo to a technical evaluator. | Pass `Date.now()` (or the query's actual fetch time) into the generator call, or relabel the field so it's clearly not a live clock. | A specific, easily-triggered "the AI system shows a wrong date" moment is a disproportionately damaging thing for a technical buyer to find during evaluation. |
| Medium-High | Executive Intelligence's data hook usage (`useExecutive()`) destructures `isLoading` but not `isError` — there is no error state on this page at all. If the request fails, the page silently falls back to placeholder copy ("No summary available yet") instead of telling the user anything failed. | Every other page in the suite (Dashboard, Reports, Decision Center) has an explicit error state with a retry action; Executive Intelligence is the one asymmetric exception. | Destructure and handle `isError` the same way the other three pages do — `ErrorState` with a retry button is already the established, reused pattern. | Silent failure on an executive-facing page reads as "nothing's wrong" when something is — the kind of gap that turns into a support ticket titled "the dashboard is empty" instead of a visible, self-explanatory error. |
| Low | No page in the suite shows who last reviewed a decision, when a priority item was created, or any audit trail. | Not expected at this stage of the product, and explicitly out of scope for a UI-layer fix (would need real backend support) — noted here only because "commercial readiness" (§10) for an enterprise buyer eventually expects this class of feature. | Roadmap item, not a UI fix. | Enterprise procurement checklists for decision-support tools frequently ask for this; worth knowing it's a gap before it's asked about in a deal. |

---

## 7. Missing navigation shortcuts

Largely a restatement of §2's findings from the "what's the specific missing link" angle, kept separate since the user asked for it as its own dimension.

| Severity | Issue | Suggested improvement | Expected business impact |
|---|---|---|---|
| High | No "Open Decision Center" shortcut anywhere on Dashboard or Executive Intelligence. | Add as part of the §2/§6 Dashboard decision-count fix. | See §2/§6. |
| Medium | No "View in Decision Center" from an individual risk/priority item on Dashboard or Executive Intelligence pointing at the matching Decision Center section. | Deep-link with a query param or hash anchor (Decision Center's sections already have stable ids in spirit, if not literally). | Turns "I noticed this on Dashboard" into a one-click path to act on it, rather than requiring the user to re-find it in a longer page. |
| Low | Decision Center's Cross-Module Highlights links out to the five source AI Center workspaces, but nothing links back from those five workspaces into Decision Center. | Each of the five Flagship Modules could carry a small "See this in Executive Decision Center" affordance. | Reinforces Decision Center's positioning as the aggregation point, rather than a dead-end destination. |

---

## 8. Progressive disclosure

| Severity | Issue | Why it matters | Suggested improvement | Expected business impact |
|---|---|---|---|---|
| Medium | The recent Decision Center pass achieved *ordering* (most-important-first) but not true progressive disclosure — nothing is actually collapsed or hidden by default; a user still scrolls past all ~11 sections every visit. | Ordering helps a user who's willing to scroll; it doesn't help a user who wants a 5-second answer and is willing to click once for more. | Introduce a default-collapsed state for the Executive Heat Map and Cross-Module Highlights (the two most "reference," least "act on this now" sections), expandable on demand. | The stated goal — "surface only information that changes executive decisions" — is only half-achieved by reordering; true disclosure would let the default view be shorter, not just better-ordered. |
| Low | None of the four pages offer a "compact" vs. "detailed" view toggle, a pattern common in comparable enterprise BI/exec-dashboard tools. | Not a gap unique to this suite, but worth naming since "commercial readiness" (§10) benchmarks against that category. | Longer-term feature, not a quick fix. | Table-stakes feature for buyers coming from Power BI / Tableau Pulse / Domo-style tools; its absence is neutral now but will be noticed in a bake-off. |

---

## 9. Executive decision workflow

Walking the intended sequence (per this suite's own stated goals across the last three migrations: *what's happening → why → what happens if ignored → what's recommended → where next*) as one continuous session:

| Severity | Issue | Why it matters | Suggested improvement | Expected business impact |
|---|---|---|---|---|
| High | The workflow has no continuity between pages — each of the four independently re-implements its own version of "what's happening / why / what's recommended," but nothing carries context (a selected project, an applied filter, an acknowledged decision) from one page to the next. | An executive who filters Decision Center down to one project, then jumps to Executive Intelligence to cross-check, starts over with no filter and no project context. | Out of scope for a documentation-only pass to fix, but worth flagging as the single biggest workflow gap: the suite behaves as four sessions, not one. | This is precisely the difference between "four dashboards" and "a decision-support workflow" — the latter is the actual commercial pitch implied by calling this an "Executive Suite." |
| Medium | Decision Queue's "Acknowledge" action (Decision Center) is explicitly session-local and not persisted — by design, per its own code comment — but there is no UI indication of that fact to the user in the moment. | An executive could reasonably believe acknowledging a decision here records something, refresh the page, and be confused when it's gone. | A small inline note ("not saved — for this session only") next to the control, or persist it. | Silent, unexpected state loss on an "acknowledge this decision" action is a specific, memorable bad-first-impression moment for exactly the persona this page targets. |
| Low | The five-step narrative (what/why/impact/recommendation/next) is well-realized *within* Decision Center itself post-migration — called out here as a genuine strength, not a gap. | — | — | — |

---

## 10. Commercial readiness

Assessed against what a technical evaluator or executive sponsor would look for in a paid enterprise decision-support product.

| Severity | Issue | Why it matters | Suggested improvement | Expected business impact |
|---|---|---|---|---|
| **Critical** | The page most likely to be demoed as "the AI feature" (Executive Decision Center) is the one running entirely on illustrative data, disconnected from the three real-data pages sitting next to it in the same suite. | This is the exact risk profile that turns a promising demo into a lost deal once a technical evaluator cross-checks two screens and finds contradicting numbers. | Prioritize wiring Decision Center to real data (per its own code's stated integration seam — `lib/useExecutiveDecisionCenter.ts` already documents exactly how) ahead of any further visual work on it. | This is the single highest-leverage fix in the entire audit for deal risk specifically. |
| Medium | Demo-data labeling itself is a genuine strength worth naming explicitly: every synthetic figure across all four pages is consistently tagged (`DemoDataBadge`, footer disclaimers, confidence tags on real-data figures), and it was preserved faithfully through three consecutive migrations. | Many AI-adjacent products blur real vs. synthetic data during demos, deliberately or not; this one doesn't, which is a legitimate trust asset with technical buyers. | Keep this discipline as new pages migrate — it's already a differentiator, worth protecting rather than "fixing." | Positive finding — a point to lead with in due-diligence conversations, not a gap. |
| Medium | No personalization or role-awareness across any of the four pages — every executive account sees an identical Dashboard/Decision Center regardless of their portfolio scope, role, or region. | Enterprise buyers evaluating multi-executive rollout (CFO vs. COO vs. regional director) expect scoped views, not one global view per account. | Roadmap item — likely ties to the existing role model already defined in `USER_ROLES.md` but not yet applied to page content. | Affects deal size/seat count more than deal risk — relevant for expansion revenue, not initial close. |
| Low | Print/export exists only on Reports; Decision Center and Executive Intelligence have no export path despite containing content (recommended actions, priorities) an executive might want to forward or archive. | Reasonable given Reports' role as the formal document, but worth naming since "share this with the board" is a plausible ask on any of the four pages. | Low priority; Reports already covers the primary export use case. | Minor; unlikely to affect a deal on its own. |

---

## Summary table — all findings by severity

31 findings total across the ten dimensions.

| Severity | Count | Sections |
|---|---|---|
| Critical | 4 | §2 (×2), §5, §10 |
| High | 6 | §5 (×2), §6 (×2), §7, §9 |
| Medium-High | 1 | §6 |
| Medium | 11 | §1, §2, §3, §4 (×2), §5, §7, §8, §9, §10 (×2) |
| Low | 9 | §1, §3 (×2), §4, §6, §7, §8, §9, §10 |

No changes were made to any file as part of this audit.
