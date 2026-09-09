# Features

Everything InsightMetric shows you, and what each part is for.

- [Daily Trends](#daily-trends)
- [Weekly Summary](#weekly-summary)
- [Category Comparison](#category-comparison)
- [Sentiment indicators](#sentiment-indicators)
- [Keyword cloud](#keyword-cloud)
- [Recurrence badge](#recurrence-badge)
- [Category filters](#category-filters)
- [Dark mode](#dark-mode)
- [Download the dataset](#download-the-dataset)

---

## Daily Trends

The home page and the reason to open the app. It shows the day's topics in rank order, one
card each, with a summary line and the signals attached to it.

Rank reflects prominence: how much attention a topic is drawing relative to the others that
day. It is a within-day ordering, so first place on a quiet day and first place on a busy
one are not the same achievement.

You can move between days. Looking back at a past day also shows what actually happened
next, which is the most useful way to build a feel for how much to trust the estimates.

Four figures sit above the list as a summary of the day: how many topics were picked up,
the average sentiment across them, the average breadth of coverage, and how many are
expected to recur.

## Weekly Summary

The same material, stepped back. Pick a week and see:

- **Persistence leaders** — the topics that held a place across the most days
- **Category mix** — how the week's balance compares with the week before
- **Sentiment by day** — whether the mood moved through the week
- **A weekly keyword cloud** — the vocabulary of the whole week rather than one morning
- **A per-topic table**, with its own download

Week-on-week comparisons are hidden while a week is still in progress. Comparing two days
against a full seven is not a comparison, and showing it would invite the wrong conclusion.

## Category Comparison

Two categories side by side over the full history — AI against cybersecurity by default,
though you can pick any pair.

Three panels share a date axis, because they answer three different questions:

- **Volume** — how much of the day each category occupied
- **Tone** — how positively or negatively each was discussed
- **Persistence** — how often each category's topics came back

A category can lead on one and trail on another, which is exactly why they are separated
rather than combined into a single score. Faint lines show daily values; bold lines show a
smoothed average, because day-to-day movement is too noisy to read directly.

## Sentiment indicators

Each topic carries a sentiment score: broadly, how positive or negative the language around
it is. Positive tends to mean launches, funding and capability; negative tends to mean
outages, breaches, criticism and regulation.

Sentiment is a description of tone, not a judgement of importance. A strongly negative topic
is often the most significant thing on the page.

## Keyword cloud

The vocabulary of the day or the week, with more prominent terms drawn larger. It is a
quick way to see what a period was *about* without reading every card — useful for spotting
that a week was dominated by one theme wearing several different headlines.

## Recurrence badge

Every topic carries a traffic-light estimate of whether it will still be here tomorrow:

| Badge | Meaning |
|---|---|
| 🟢 **Likely back tomorrow** | Expected to persist |
| 🟡 **Toss-up** | Genuinely uncertain |
| 🔴 **Likely to fade** | Expected to drop away |

Each badge carries a percentage. The amber band exists on purpose: when the product is not
confident, saying so is more useful than committing to a coin flip.

Today's badges cannot be checked yet — tomorrow has not happened. On past days you can see
the estimate and the outcome together, which is the honest way to judge whether the
estimates are worth anything.

## Category filters

A settings page lets you choose which categories appear. The choice applies across every
page immediately and can be saved so it persists between visits.

Filtering changes only what is displayed, never how anything is calculated — narrowing to
one category will not quietly change the numbers on the topics you kept.

## Dark mode

A one-click switch in the sidebar of every page, remembered between visits. Charts, clouds
and the logo all follow it.

## Download the dataset

Every page offers the underlying data as **CSV** or **Parquet**: the daily view exports the
history, the weekly view exports that week.

Before you use it for anything, please read the note on sample data in the
[README](../README.md#about-the-numbers). The bundled history is largely generated sample
data, and it should not be treated as a record of real events.
