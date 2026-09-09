# Starter issue backlog

Ten issues covering the areas most likely to attract a first contribution. Each is written to
be filed as-is: title, labels, body. `scripts/create_issues.sh` files all ten with the `gh`
CLI, including creating the labels.

Everything here is grounded in the current code — the thresholds, filenames and numbers are
real, so nobody has to reverse-engineer the codebase to start.

---

## 1. Replace keyword-overlap clustering with sentence embeddings

**Labels:** `clustering`, `enhancement`, `help wanted`

Headlines are currently grouped by keyword overlap: two join a topic when they share at least
`MIN_SHARED_KEYWORDS` (2) keywords *and* those shared words are at least `MIN_CLUSTER_JACCARD`
(0.2) of the union of both keyword sets. It is crude, and it fails in both directions —
"OpenAI confirms wiki incident" and "OpenAI's rogue agents keep escaping" are the same story
but share only "openai", while unrelated stories can merge on a shared verb.

A small local sentence-transformer would almost certainly do better.

**The constraint is the interesting part.** It must still run in under a minute on a laptop
with no GPU, and — the project's one hard rule — **no API calls and no keys**. A model like
`all-MiniLM-L6-v2` runs locally in a few hundred milliseconds for 80 headlines, so this is
feasible; a hosted embedding endpoint is not.

**Acceptance criteria**
- Clustering runs offline after a one-time model download, and the download is documented
- Runtime for a full collection stays under a minute on CPU
- A before/after comparison on at least one cached day under `data/raw/`, showing which
  clusters changed and why
- The keyword path stays available behind a flag, so a contributor without the model can
  still run the pipeline

**Pointers:** `cluster()` and `keywords_of()` in `src/collect_live.py`.

---

## 2. Add a clustering diagnostic that surfaces suspect merges and splits

**Labels:** `clustering`, `tooling`, `good first issue`

Every clustering rule in this project exists because a real day of data exposed a specific
failure — the current Jaccard guard was added after "LibreOffice breaks download records" and
"Microsoft breaks another patch Tuesday record" merged on `{break, record}`. Those failures
were found by reading output by hand, which does not scale.

Add a script that takes a cached day and reports clusters worth a human look:

- **Suspect merges** — clusters whose members' pairwise similarity is only just above the
  threshold, or whose shared keywords are all common verbs
- **Suspect splits** — separate clusters that share a proper noun or a distinctive rare token
- **Singletons from the same source** with near-identical wording

**Acceptance criteria**
- `python src/cluster_report.py --date 2026-09-08` prints a readable report from cached feeds
- Works offline, reading only `data/raw/<date>/`
- Output is short enough to scan — this is a review aid, not a dump

This is a good first issue: self-contained, no schema change, and immediately useful for
tuning issue #1 and #3.

---

## 3. Build an unmatched-vocabulary report to drive lexicon expansion

**Labels:** `lexicon`, `tooling`, `good first issue`

`CATEGORY_TERMS` in `src/collect_live.py` was built from words the feeds actually produced,
which is why it works. Keeping it that way as feeds change needs tooling, not guesswork.

Add a report that ranks the keywords appearing most often across collected days which match
**no** category term — the vocabulary the lexicon is currently blind to. That list is the
shortest path to a good expansion PR, and it makes the "add terms you actually saw" rule in
CONTRIBUTING easy to follow.

**Acceptance criteria**
- Reports unmatched keywords by frequency across a date range, with an example headline for each
- Reports the share of clusters landing in `Other`, per day and overall
- Runs from cached feeds, offline

**Why it matters:** on the day this project was first tested against real feeds, rebuilding
the lexicon from actual headline vocabulary took cybersecurity detection from 2 clusters to 13
out of the same 80 headlines. That gain was found by hand; this report would have found it in
seconds.

---

## 4. Support per-repository tag rules in the release monitor

**Labels:** `releases`, `enhancement`

`NOISE` in `src/github_releases.py` is one regex applied to every repository: it drops tags
containing a slash or starting with `viable`/`trunk`/`ciflow`/`nightly`. That rule exists
because PyTorch's release feed contains **no releases at all** — only CI refs like
`viable/strict/<timestamp>` and `trunk/<sha>`.

One global regex is the wrong shape for this. Different repositories have different noise:
LangChain tags per-package (`langchain-core==1.6.2`), llama.cpp uses build numbers (`b10853`)
rather than semver, and others will surprise us.

**Proposed change:** let `WATCHLIST` entries optionally carry their own rules —

```python
WATCHLIST = [
    "streamlit/streamlit",
    ("pytorch/pytorch", {"exclude": r"^(viable|trunk|ciflow)"}),
    ("langchain-ai/langchain", {"packages": ["langchain"]}),   # ignore sub-package tags
]
```

**Acceptance criteria**
- Plain string entries keep working exactly as now (no breaking change to the default watchlist)
- Rules are documented next to `WATCHLIST` with the repository that motivated each
- `classify()` gains a test table of real tags, including the awkward ones above

**Context:** of 110 releases logged across twelve repositories in the first real run, only 21
were stable minor or major versions. Filtering is doing most of the work here, so it deserves
to be configurable.

---

## 5. Explain the prediction badge on the Daily Trends page

**Labels:** `ui`, `enhancement`, `help wanted`

Each topic gets a traffic-light badge from the model's recurrence probability, but the page
never says *why*. The model is a logistic regression on standardised features, so the
explanation is immediate and needs no interpretability library: multiply each standardised
feature value by its coefficient and you have that row's contribution in log-odds.

**Proposed UI:** an expander on each card — "why this prediction" — showing the top three
contributions, positive and negative, in plain language:

> Covered by 4 sources (+0.30) · ranked #2 today (+0.28) · only 3 keywords (−0.11)

**Acceptance criteria**
- Contributions computed from the fitted pipeline, not hard-coded
- Works when the model file is missing (the page should degrade, not crash)
- Wording is readable by a non-specialist — no raw feature names in the user-facing text

This is one of the strongest arguments for keeping the model small, and the app currently
throws that advantage away.

---

## 6. Add search, filtering and source links to the Daily Trends page

**Labels:** `ui`, `enhancement`, `good first issue`

The main page lists ten topics for the selected day with no way to search across days, and the
source names are plain text. Three small additions:

- A search box matching topic and keywords across the whole history, not just the current day
- A minimum-source-count filter, so "stories more than one outlet ran" is one click
- Source names rendered as links to the underlying articles

The third needs a schema note: `sources` currently holds names only, not URLs. Either add a
`links` column (**a schema change** — see `COLUMNS` in `src/collect.py`, and say so explicitly
in the PR) or join back to the cached feed. Discuss the approach on this issue before writing
code.

**Acceptance criteria**
- Search works with an empty query and with no matches
- Filters follow the existing pattern in `src/settings.py`, not new page-local state
- The page still renders on a fresh clone with only synthetic data

---

## 7. Add a comments-to-points ratio feature

**Labels:** `model`, `enhancement`, `help wanted`

The dataset carries `hn_points`, but points alone conflate two different things. A story with
600 points and 20 comments is a consensus story; 300 points and 400 comments is an argument.
Those plausibly persist differently, and neither raw number captures it.

The Hacker News page already plots points against comments and the separation is visible by
eye. Turning that into a feature is a small change to `src/features.py`.

**Acceptance criteria**
- Feature added to `NUMERIC_FEATURES` in `src/features.py`, handling division by zero
- Chronological-split metrics reported against the current baseline: accuracy 0.660, F1 0.667,
  ROC-AUC 0.709
- **State which dataset produced the numbers.** `hn_points` is zero throughout the committed
  synthetic history, so this feature can only be evaluated on real collected data — a result on
  three or more weeks of live data is what would settle it
- `hn_comments` may need adding to `COLUMNS` (a schema change — call it out)

This is the single most promising untested idea in the project.

---

## 8. Resolve the collinearity between `keyword_frequency` and `rank`

**Labels:** `model`, `good first issue`

`rank` is assigned by sorting on source count, cluster size and keyword frequency — so
`keyword_frequency` is partly baked into `rank`, and both are then fed to the model as
separate features. The fitted coefficients show the symptom: `rank` is the strongest feature
at −0.57 while `keyword_frequency` carries a small *negative* coefficient (−0.05) that has no
sensible interpretation on its own.

**What to do:** measure the correlation, then drop one, or replace the pair with something
orthogonal (raw frequency plus a within-day percentile, say). Either is defensible; the
evidence should decide.

**Acceptance criteria**
- Correlation between the two reported on both the synthetic and any available live data
- Chronological-split metrics before and after
- If a feature is dropped, `FEATURES` in `src/features.py` updated and the change noted in the
  README's model section

Good first modelling issue: small, self-contained, and it makes the coefficient table honest.

---

## 9. Write a data card for the dataset

**Labels:** `documentation`, `good first issue`

The README documents the fourteen schema fields, but there is no single document answering the
questions someone reusing the data would ask. Given that the repository invites people to
download the dataset, that gap matters.

**Write `docs/data_card.md` covering:**

- **Provenance** — which feeds, collected when, under what user agent, cached where
- **The synthetic-versus-live distinction**, stated plainly and early. The committed history is
  generated by `src/collect.py` and its metrics describe the pipeline, not the world
- **How the target is defined** — "appears in tomorrow's top ten", matched by Jaccard ≥ 0.4 on
  keyword sets, and why the most recent day is always unlabelled
- **Known biases** — English-language sources only; five outlets with a US/UK slant; the
  ranking is the collector's own, so "recurred" means "this agent ranked it again"
- **Label noise** — the fuzzy match both misses continuations that changed vocabulary and
  occasionally joins distinct stories
- **Licence and attribution** for reuse

Following the shape of a standard dataset data card is fine; being honest about limitations
matters more than the format.

---

## 10. Add a first test suite and a testing section in CONTRIBUTING

**Labels:** `documentation`, `testing`, `good first issue`

There is no test suite. CONTRIBUTING says so and calls adding one a welcome contribution —
this issue is that contribution, and it should land with the documentation to match.

**Highest-value first tests**, in order:

1. `classify()` in `src/github_releases.py` against a table of real tags: `v3.15.0`,
   `1.63.1.dev20260907`, `langchain-core==1.6.2`, `b10853`, `v0.29.0rc5`,
   `viable/strict/1788863288`. This function has the most branches and the least obvious behaviour
2. The clustering guard in `src/collect_live.py` against the "breaks record" false-merge case —
   a regression test for a bug that was actually shipped
3. `label_recurrence_fuzzy()` against a two-day fixture, including the always-unlabelled latest day
4. `build_features()` returning the expected 18 columns, guarding the schema contract

Cached feeds under `data/raw/` make good fixtures — no network needed.

**Acceptance criteria**
- `pytest` runs green from a clean clone with only `requirements.txt` and `requirements-dev.txt`
- `pytest` added to `requirements-dev.txt`
- A **Testing** section added to CONTRIBUTING, replacing the "there is no test suite yet" note
- Optionally, a CI workflow running lint and tests on pull requests

---

## Filing these

```bash
gh auth login                    # once
./scripts/create_issues.sh <you>/insightmetric
```

The script creates the labels first, then the issues. It is idempotent for labels but not for
issues — running it twice files twenty.
