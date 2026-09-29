# Trading journal review — 28 September 2026

> Subsequent requirements update: tax and brokerage calculations, fee UI, and the charges-config endpoint have been removed. P&L now reflects execution results without deductions. Refresh clears saved trades and resets analysis/filters. The review below records the earlier audit; its charge-engine descriptions are historical.

## Project summary

This is a local trading journal for Indian equity and derivatives. The Next.js 16 / React 19 dashboard supports manual multi-leg entry, Zerodha CSV imports, trade notes, strategy/emotion tags, filtering, and P&L summaries. FastAPI handles parsing, charge estimates, and CRUD; SQLAlchemy/SQLite is the primary working database. Optional Firebase writes mirror some actions. The P&L report analyzer computes statistics and calls Gemini when configured, otherwise generating rule-based commentary.

The application is a useful prototype for a personal journal. Its strongest features are the small, understandable architecture and the combination of execution records with reflection notes. Accounting correctness and import provenance should take priority over additional AI or broker integrations.

## Fixes completed

- **Open-position P&L:** replaced sell-minus-buy cash flow with FIFO matching within each submitted trade. Unmatched buys no longer become immediate losses and unmatched sells no longer become immediate profits. Partial closes recognize only the matched quantity. Charges incurred on all submitted legs are still deducted.
- **Position status:** manual and imported records are closed only when instrument quantities balance; open records have no exit time. Dashboard win rate includes closed records only.
- **Import identity:** deterministic execution/trade IDs prevent repeat imports from adding identical records. Partial overlap with previously imported executions returns a 409 before any local insertion. Fill records now reference their legs.
- **Input validation:** malformed tradebooks and invalid manual prices, quantities, symbols, sides, and segments are rejected instead of silently manufacturing executions. Bad dates no longer become today's date. Uppercase file extensions are accepted.
- **Charge persistence:** stored charge components come from the calculation result, replacing invented percentage splits. Manual entries now persist the breakdown too. This fixes persistence, not the accuracy of underlying rates.
- **Deletion:** deleting trades uses ORM cascades to remove associated legs, fills, and charges while preserving other users' records.
- **Editable optional values:** PATCH can clear nullable fields such as a planned stop loss.
- **P&L analysis:** unsupported formats return validation errors, numeric P&L values are cleaned consistently, and filtering total rows no longer breaks percentage-series alignment. Analysis no longer inserts fabricated executions or duplicates into the journal.
- **AI output:** malformed AI response fields fall back safely; several unsupported behavioral/tax assertions were removed from fallback commentary. Cached report results were removed to avoid presenting an unrelated old report as current analysis.
- **Configuration:** validated settings now supply the SQLite path, Gemini key, and Firebase credential path from `.env`.
- **Frontend:** duplicate TypeScript member and lint failures fixed; request ordering prevents stale filter responses from replacing current data; loading/errors are visible; manual prices accept decimals and equity delivery mode is selectable; page metadata is descriptive.
- **Repository:** replaced the orphaned frontend Git submodule entry with ordinary source tracking. The frontend had no submodule repository/configuration, so a clean clone could not recover its source. Scoped the root Python `lib` ignore so frontend utilities are included. The large frontend diff is primarily previously untracked existing source, not a rewrite.
- **Setup:** added backend dependency and environment templates; corrected README commands; launcher uses the project virtual environment or `JOURNAL_PYTHON` instead of a personal Anaconda path. Shutdown no longer force-kills arbitrary processes occupying ports 3000/8000.
- **Tests:** added temporary-database isolation and regression coverage. An initial run of the old tests inserted two sample records in the local database; those exact records were identified and removed. Existing journal records were not recalculated or migrated.

## Validation

- Backend: 31 tests pass, including 21 new regression cases.
- Frontend: ESLint and TypeScript pass.
- Production: `npm run build -- --webpack` passes. Default Turbopack build encountered environment restrictions (font networking, then process/port binding); this is not recorded as a passing default build.
- Shell scripts: syntax checked. Full launcher/shutdown behavior was not exercised against the user's running services.
- External Gemini and Firebase services and real broker files were not exercised. Tests use isolated storage and disable external service calls.

## Remaining limitations and recommended priorities

1. **Execution ledger and trade matching.** Imports currently group activity by instrument across the whole file, rather than splitting independent round trips or strategy episodes. FIFO matching is within that group, not across separate imports/manual records. Build a persistent execution ledger with broker IDs, import batches, positions, and explicit strategy grouping; reconcile overlapping imports rather than rejecting them.
2. **Broker reconciliation and fees.** Lot size 25 is hard-coded for derivatives. CSV equities are assumed delivery. Fee rates, exchange-specific charges, charge dates, rounding, and exercise treatment need a dedicated source-backed audit and contract-note comparison. A multi-date group currently uses its first date's fee configuration. Existing figures should not be treated as audited accounting.
3. **Report semantics.** A broker P&L report may be gross, net, or aggregated per symbol. The analyzer currently uses the supplied P&L (or sell value minus buy value) and counts report rows; it does not establish that each row is a trade or that charges were deducted. Add explicit column mapping, charge inclusion, date coverage, and a preview before analysis. Some broker exports with preamble rows remain unsupported.
4. **History repair.** Earlier random-ID imports, orphaned records, and summaries inserted by the previous analyzer may remain. New fixes cannot reliably infer their provenance. Add a backup and a reviewable cleanup/reconciliation tool before modifying historic records.
5. **Cloud reliability.** Firebase is an optional best-effort mirror, not dependable two-way synchronization. Manual creates are not mirrored, import writes precede local commit, and failures lack a retry/outbox process. Keep SQLite authoritative until synchronization has explicit guarantees.
6. **Access control.** There is no authentication and callers can select `user_id`. Wildcard CORS and unauthenticated mutation endpoints are appropriate only for a trusted local prototype, not shared hosting. Establish the intended single-user/multi-user deployment model before adding authentication and ownership enforcement.
7. **Daily journaling workflow.** Prioritize trade date/time entry, an import preview, date-range filters, screenshots, export/backup, individual deletion, and a review calendar. Then add equity curve, drawdown, profit factor, expectancy, and strategy breakdowns once trade accounting is reliable.
8. **Explainable coaching.** Separate measured observations from hypotheses, display the insight source, and connect feedback to real notes/emotion tags. Aggregate P&L alone cannot establish revenge trading, FOMO, or stop-loss discipline.
9. **Operations.** Pin a tested dependency lock for Python, add CI, pagination/eager loading, upload limits, database migrations, and process supervision. The new requirements file is a compatibility range manifest, not a fully locked environment.

## Requirements to settle next

- Personal offline journal, cloud-synced single user, or multiple users?
- Which brokers and exact export formats are authoritative?
- Intraday equity, delivery, futures, options, or all four?
- Is a “trade” a round trip, individual execution, position, or multi-leg strategy?
- Which workflow matters most: daily reflection, performance analytics, broker reconciliation, or coaching?
