# Architecture

A high-level view. This page describes the shape of the product, not how any part of it
works internally.

## The three pieces

```
                    ┌─────────────────────────┐
                    │      Daily job          │
                    │  refreshes the dataset  │
                    │     once a day          │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │        Backend          │
                    │  API serving the data   │
                    │     and estimates       │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │        Frontend         │
                    │       Streamlit         │
                    │   the pages you use     │
                    └─────────────────────────┘
```

**Frontend — Streamlit.** The dashboard itself: the pages, charts and controls described in
[FEATURES.md](FEATURES.md).

**Backend — an API.** Serves the day's data and the recurrence estimates to the frontend.

**Daily job.** Runs once a day and updates the dataset the other two read from.

That is the whole of it at this level. The three are separate so that each can be improved
or replaced without disturbing the others, which is the same principle the product follows
everywhere: small pieces, swappable.

## What this means in practice

**The dashboard refreshes once a day, not continuously.** InsightMetric is a daily briefing
rather than a live feed. Opening it twice in an afternoon will show you the same thing, and
that is the intended experience.

**The most recent day is always incomplete.** Recurrence describes whether a topic returns
*tomorrow*, so today's topics cannot have an outcome yet. Blank values on the newest day are
correct, not missing.

**The product improves with time rather than with attention.** Its accuracy is a function of
how much history it has, so the most valuable thing it can do is keep running.

## Deliberately not documented here

This page is intentionally limited to the product's shape. Internal design — how data is
gathered, processed, organised, estimated or deployed — is not documented publicly.

If you are contributing an interface or documentation change, you will not need any of it.
See [CONTRIBUTING.md](CONTRIBUTING.md).
