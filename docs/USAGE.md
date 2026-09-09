# Using InsightMetric

A short guide to reading the dashboard. No technical background needed.

- [Getting around](#getting-around)
- [Reading a trend card](#reading-a-trend-card)
- [Reading the sentiment bar](#reading-the-sentiment-bar)
- [Reading a recurrence badge](#reading-a-recurrence-badge)
- [Using the weekly summary](#using-the-weekly-summary)
- [Comparing categories](#comparing-categories)
- [Choosing what you see](#choosing-what-you-see)
- [Downloading the data](#downloading-the-data)
- [A two-minute routine](#a-two-minute-routine)

---

## Getting around

Pages are listed in the sidebar on the left:

| Page | Use it for |
|---|---|
| **Daily Trends** | Today, or any past day |
| **Weekly Summary** | A whole week, rolled up |
| **Settings** | Which categories appear, and light or dark |
| **Compare** | Two categories against each other over time |

The sidebar also holds the day or week selector for whichever page you are on, the dark-mode
switch, and the download buttons. On a narrow screen the sidebar starts collapsed — the
arrow in the top left opens it.

Your category and theme choices follow you across pages, so you set them once.

## Reading a trend card

Each topic on the Daily Trends page is one card:

```
#2  Open-weight model release          [ AI ]        🟢 Likely back tomorrow (76%)

Open-weight model release faces backlash amid reports of failures and
security concerns.

Covered by 4 outlets · Keywords: open-weights, release, benchmark, model
```

Reading it left to right:

- **The rank** (`#2`) is its position that day. It is relative to the same day only.
- **The topic** is the short name for the story.
- **The category** places it — AI, cybersecurity, cloud, chips, policy, startups and so on.
- **The summary line** is a one-sentence description.
- **Coverage** tells you how many outlets carried it. This is one of the more useful numbers
  on the page: a topic carried by five outlets is a different kind of event from one carried
  by a single publication, regardless of how loud either is.
- **Keywords** are the terms most associated with it, and are what the keyword cloud draws
  from.
- **The badge** on the right is the recurrence estimate — see below.

On a past day, the card also shows what actually happened. Comparing the two is the fastest
way to calibrate how much weight to give the badges.

## Reading the sentiment bar

The sentiment chart runs from **−1** to **+1**:

| Range | Reading |
|---|---|
| **+0.5 to +1** | Clearly positive — launches, funding, capability |
| **+0.1 to +0.5** | Mildly positive |
| **−0.1 to +0.1** | Neutral or mixed |
| **−0.5 to −0.1** | Mildly negative |
| **−1 to −0.5** | Clearly negative — outages, breaches, criticism, regulation |

Three things worth keeping in mind.

**Tone is not importance.** The most negative bar on the page is frequently the most
significant story of the day. Sentiment tells you the register of the coverage, nothing more.

**Strength is not certainty.** A −0.9 means the language is emphatic, not that the reading
is more reliable.

**A day's average can hide its shape.** A day with one euphoric topic and one furious one
averages to roughly nothing. The per-topic bars are more informative than the daily average
whenever the two disagree.

## Reading a recurrence badge

The badge is an estimate of one specific thing: **will this topic still be prominent
tomorrow?**

| Badge | Read it as |
|---|---|
| 🟢 **Likely back tomorrow** | More likely than not to persist |
| 🟡 **Toss-up** | Genuinely uncertain — treat it as unknown |
| 🔴 **Likely to fade** | More likely than not to drop away |

**Use the percentage, not just the colour.** 84% and 66% are both green and are not the same
statement. When the number is near 50%, the honest reading is that the product does not know.

**It is a forecast, and forecasts are wrong.** A well-calibrated estimate that says 70% is
supposed to be wrong about three times in ten. A run of misses is not automatically a fault;
what would be a fault is misses concentrated where it claims high confidence.

**It says nothing about importance.** A topic can be certain to fade and still be the most
consequential thing you read this week. Recurrence measures persistence in coverage, which
is a proxy for attention, not for significance.

**Today's badges cannot be checked yet.** Tomorrow has not happened. Judge the estimates on
past days, where the outcome is shown alongside.

## Using the weekly summary

Daily is for *what is happening*. Weekly is for *what actually mattered*, and it is the more
useful of the two if you only look once.

A productive way through it:

1. **Persistence leaders first.** Topics that held a place across several days are the ones
   with substance behind them. A topic that appeared once and vanished was probably a single
   news cycle.
2. **Then the category mix.** A category climbing week on week is worth noticing, though one
   week is a small sample and two is not much better.
3. **Then sentiment by day.** Look for a sharp move rather than the level. A day that swings
   negative usually means something broke.
4. **Then the keyword cloud.** It often reveals that several apparently separate topics were
   the same underlying story.

Week-on-week comparisons stay hidden until a week is complete, so a partial week will show
fewer figures than a finished one. That is deliberate.

## Comparing categories

The Compare page answers questions of the form *is AI or cybersecurity getting more
attention, and how is each being talked about?*

Pick two categories and read the three panels as three separate questions — volume, tone,
persistence. Resist collapsing them into a single verdict: a category can be loud and
shallow, or quiet and persistent, and both are worth knowing.

The bold lines are smoothed averages and the faint ones are the raw daily values. Trust the
bold lines for direction and the faint ones for volatility.

## Choosing what you see

On the **Settings** page, tick the categories you want. Every page updates immediately. Save
the selection and it will be there next time.

Two useful habits: narrow to one or two categories for a focused morning read, and widen to
everything before drawing any conclusion about the week — a filtered view will not tell you
that the story you care about was crowded out by something else.

## Downloading the data

Use the buttons in the sidebar. **CSV** opens anywhere, including Excel. **Parquet** is
smaller and faster if you are working in Python or R.

Please read the [note on sample data](../README.md#about-the-numbers) first. The bundled
history is largely generated sample data — fine for trying the product, not a record of real
events, and not something to cite.

## A two-minute routine

1. Open **Daily Trends**. Read the four figures at the top, then the top three or four cards.
2. Note anything green with a high percentage — those are worth carrying into tomorrow.
3. Once a week, open **Weekly Summary** and read the persistence leaders.
4. Occasionally, look back at a day from last week and check the badges against what
   happened. That is how you learn how much to trust them.
