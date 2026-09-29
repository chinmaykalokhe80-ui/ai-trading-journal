# Trade coach: evidence, principles, and optional LLMs

The journal now computes the assessment locally by default. Choose **Analyze saved trades** to review all closed journal records, or **Analyze report** to review a CSV/Excel report without importing it. The dashboard filters do not restrict the saved-journal review. Refresh still clears the journal and resets the review. Tax and brokerage calculations remain removed.

## What the report covers

- Sample P&L, expectancy per record, profit factor, average win/loss, payoff ratio, largest win/loss, flat records, and an approximate win-rate interval.
- Sensitivity to the best winner and concentration in the largest loss.
- Strategy, segment, and emotion groups with sample counts. Small groups are flagged; comparisons do not prove causation.
- Cumulative daily realized P&L and daily drawdown when all records have reliable dates. Intraday/account-equity drawdown is not inferred.
- Win/loss streaks only when chronological order is unambiguous.
- Recorded-plan coverage and R-multiples for simple two-leg, fully closed positions with a valid stop. Complex positions are not forced into a misleading risk calculation.
- Evidence-backed strengths, review priorities, specific exercises, and measurable follow-up goals. There is no invented overall trader score.

Historical summary records with zero-price placeholder legs do not have trustworthy execution timestamps. Their dates are excluded from sequence analysis. Manual entries currently use insertion timestamps and also cannot establish the actual trading timeline. A report row or instrument-grouped journal record may represent several individual trades.

## Principles and attribution

These are short paraphrases of themes supported by publisher materials, not a claim to have ingested complete books or a universal ranking of the best books. The app's thresholds and scoring logic are original operational choices.

| Source | Principle | Application in the journal |
|---|---|---|
| Mark Douglas, [Trading in the Zone](https://www.penguinrandomhouse.com/books/350665/trading-in-the-zone-by-mark-douglas/) | Evaluate outcomes probabilistically, over a sample. | Pair win rate with payoff and expectancy; flag sample uncertainty instead of treating one result as proof. |
| Alexander Elder, [The New Trading for a Living](https://www.wiley-vch.de/en/areas-interest/finance-economics-law/the-new-trading-for-a-living-978-1-118-44392-7) | Define risk and maintain useful records. | Check whether plans are recorded; compare measurable initial risk with the realized result without assuming why an overrun occurred. |
| Brett N. Steenbarger, [The Daily Trading Coach — publisher excerpt](https://catalogimages.wiley.com/images/db/pdf/9780470398562.excerpt.pdf) | Build improvement through specific self-review exercises. | Attach an action and progress measure to each concern; judge process separately from profit. |

Heuristics: fewer than 30 records triggers a small-sample note; fewer than 5 records flags a subgroup; average loss exceeding 1.5 times average win prompts a payoff review; over 50% concentration flags an outcome dependency. These thresholds are not quotations, investment rules, or statistically validated decision boundaries. A low payoff can be compatible with a profitable strategy. Removing the best winner is a sensitivity check, not a recommendation to eliminate such trades.

## Free-tier API shortlist

Checked against the linked official pages on 28 September 2026. These are eligible services/model presets, not a guarantee that an arbitrary configured account is unbilled. Limits and availability can change. No provider benchmarking on your trades was performed.

| Service | Preset | What to know |
|---|---|---|
| [Google Gemini API](https://ai.google.dev/gemini-api/docs/pricing) | `gemini-3.8-flash` | Official pricing lists free input/output for eligible free-tier use. Google's unpaid-service content may be used for product improvement. Check your project's billing tier. |
| [Groq](https://console.groq.com/docs/rate-limits) | `qwen/qwen3.8-27b` | The listed free-plan table shows 30 requests/minute, 1,000/day, 8,000 tokens/minute and 200,000/day for this model. Your console is authoritative. Review [data handling](https://console.groq.com/docs/your-data). |
| [OpenRouter](https://openrouter.ai/docs/api_reference/limits) | `openrouter/free` | The [free router](https://openrouter.ai/openrouter/free/apps) chooses an available free model. Quality and availability vary. The integration allows only this route or a `:free` model; quotas and provider privacy policies still apply. |

Start with local rules. If you want a second perspective, Groq is a reasonable first integration to try for this small aggregate-data task; that is an engineering preference, not a measured quality ranking. Gemini is another option. OpenRouter is useful for trying changing free models but less reproducible because the routed model can vary.

## Optional setup

Add the relevant values to `backend/.env` using `backend/.env.example`, then restart the backend:

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.8-flash
GROQ_API_KEY=
GROQ_MODEL=qwen/qwen3.8-27b
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openrouter/free
```

Keep keys on the backend; do not add them to `NEXT_PUBLIC_` variables or paste them into chat. A configured key only enables the dropdown choice. External calls happen only when an external reviewer is explicitly selected and Analyze is pressed. No automatic provider switching, paid-model fallback, or retries are performed.

The LLM receives computed numeric aggregates, record-coverage counts, source type, excluded-open count, and app-generated finding IDs. It receives no raw file, notes, symbols, strategy labels, timestamps, filenames, or account identifiers. Aggregate financial data is still financial data, so check the selected service's data terms.

AI output appears in a separate panel and cannot replace computed metrics. Its structured response is validated, and unsupported evidence IDs are rejected. A timeout, quota error, missing key, or malformed response preserves the complete local assessment. This validates the response structure, not the factual accuracy of every generated sentence.

## Verification

Backend tests cover accounting metrics, all-winning/all-losing/flat samples, missing/tied timestamps, simple-position risk, read-only API behavior, user filtering, default-local behavior even with configured keys, all three mocked provider adapters, data minimization, invalid model output, timeouts and rate limits. Live provider calls require your configured credentials and were not performed.
