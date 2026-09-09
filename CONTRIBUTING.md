<picture>
  <source media="(prefers-color-scheme: dark)" srcset="outputs/logo_wordmark_dark.svg">
  <img src="outputs/logo_wordmark.svg" alt="InsightMetric" width="420">
</picture>

# Contributing to InsightMetric

*Tech Trends, Minus the Noise.*

Thank you for considering a contribution. This is a deliberately small project, and the bar
for a change is that it stays that way: readable, reproducible, and explainable to someone who
is not a specialist.

- [The one hard constraint](#the-one-hard-constraint)
- [Getting set up](#getting-set-up)
- [Coding standards](#coding-standards)
- [Naming, copy and colour](#naming-copy-and-colour)
- [Reporting issues](#reporting-issues)
- [Proposing a new feed](#proposing-a-new-feed)
- [Proposing a model change](#proposing-a-model-change)
- [Other good contributions](#other-good-contributions)
- [Pull requests](#pull-requests)
- [A note on the data](#a-note-on-the-data)

---

## The one hard constraint

**No paid services and no API keys.** Every data source is a public feed, sentiment runs
locally, and the whole pipeline executes on a laptop in about a minute. This is not a budget
decision — it is the point of the project. Anyone can clone it and have it running without an
account anywhere.

A change that needs a credential, a hosted inference endpoint, or a subscription is the wrong
change for this repository, however good the idea. If you think a case genuinely warrants an
exception, open an issue and argue it before writing code.

---

## Getting set up

```bash
git clone https://github.com/<you>/insightmetric.git
cd insightmetric
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt                   # linter
```

Verify the setup without touching the network:

```bash
python src/collect.py --days 45 --seed 42   # synthetic history
python src/train.py                         # should print ~0.66 test accuracy
streamlit run Daily_Trends.py               # app on http://localhost:8501
```

Preview a real collection without saving anything:

```bash
python src/collect_live.py --dry-run
```

There is no test suite yet. Adding one is itself a welcome contribution — see
[Other good contributions](#other-good-contributions).

---

## Coding standards

The codebase has consistent conventions. Please match them; a PR that reads like the
surrounding code is far quicker to review.

### Enforced by tooling

Run before you open a PR:

```bash
ruff check .
```

Configuration lives in `pyproject.toml`, and the current code passes it clean. The rule set is
deliberately modest — correctness and import hygiene (`E`, `W`, `F`, `I`, `UP`, `B`), not style
opinions.

**Formatting is not enforced.** `ruff format` would rewrite all fifteen files and flatten
compact lines like `ax.set_xlim(0, 1); ax.set_ylim(0, 1)` that are intentionally paired. Please
match the surrounding style by eye rather than running the formatter over the repository.

Three rules are switched off for reasons worth knowing:

| Rule | Why it is off |
|---|---|
| `E501` line length | Long lines are allowed where a data literal reads better packed than split — the category lexicon in particular |
| `E402` import position | `sys.path` is extended before local imports so every script runs from any working directory |
| `E702` paired statements | `fig.tight_layout(); fig.savefig(...); plt.close(fig)` is one thought, and reads better as one line |

`B905` (`zip(..., strict=)`) is also off. The zips in this codebase are equal-length by
construction, but adding `strict=True` to each call site — and checking that assumption holds
at each one — would be a genuinely useful small contribution.

### Conventions the tooling cannot check

**Every module opens with a docstring** that says what the module does and, for anything
runnable, how to run it:

```python
"""
Hacker News trending topics.

Uses the already-approved Hacker News front-page feed: each item carries points,
comment count and submission time, which is enough to measure engagement and
velocity without any further API.

Run:  python src/hn_trending.py
      python src/hn_trending.py --offline
"""
```

**`from __future__ import annotations` at the top of every module.** All fifteen files do
this; it keeps type hints cheap and lets modern syntax work on older interpreters.

**Type hints on function signatures**, including return types. Internal locals do not need
annotating.

**Comments explain why, not what.** The code already says what it does. A comment earns its
place when it records a decision someone would otherwise undo:

```python
# Order matters only for ties: the first category listed wins. AI is last because "ai"
# appears in headlines from every other category and would otherwise absorb them.
```

That comment prevents a future contributor from "tidying" the dictionary into alphabetical
order and silently breaking categorisation. This is the standard to aim for.

**Configuration is module-level constants in CAPS**, not a config file. There is no YAML to
drift out of sync with the code. If you add a tunable, put it near the top of its module with
a comment giving its units and the trade-off it controls.

**Failures degrade, they do not abort.** One unreachable feed must never kill a collection
run. Catch, log a `[warn]` line, and continue:

```python
try:
    raw = _download(feed_url(repo))
except Exception as exc:            # network errors should not abort the other feeds
    print(f"  [warn] {repo}: {exc}")
    continue
```

**Handle the empty case.** A fresh clone has no release log and no HN log. Every function that
reads a generated file must work when that file is missing or its DataFrame has no columns,
and every app page must render a sensible notice rather than an exception.

### Invariants you must not break

These four properties are what make the project trustworthy. A PR that breaks one will be
asked to change, however useful the feature.

| Invariant | Why |
|---|---|
| **Raw responses are cached** under `data/raw/<date>/` before parsing | `--offline` must rebuild any day exactly. This turns debugging a parser change into a local operation. |
| **Feature engineering lives only in `src/features.py`** | Imported by both the trainer and the app, so the app can never score rows with different transformations from those the model was fitted on. |
| **`COLUMNS` in `src/collect.py` is the schema contract** | The parquet file, the model and the app all depend on it. Changing it is a breaking change and must be called out explicitly. |
| **Evaluation is chronological** | The target is forward-looking. A random split puts tomorrow's rows in training and inflates every metric. |

---

## Naming, copy and colour

The project has a brand specification: [`docs/BRAND.md`](docs/BRAND.md). It is short, and a
pull request that touches user-visible text, a figure or the interface is checked against it.

The parts that come up most often:

- **The name is `InsightMetric`** — singular, one word, two capitals. Not *InsightMetrics*.
  The only lowercase form is `insightmetric`, for repository, package and image names.
- **The tagline is "Tech Trends, Minus the Noise."**, with the full stop, used once per
  surface. Please don't write a new one.
- **Colours come from `src/brand.py`.** Import `ACCENT`, `INK`, `FADED` and the rest; never
  paste a hex value into a chart or a page — `grep -rn '#[0-9A-Fa-f]\{6\}' src pages` should
  only ever match `brand.py`. If you need a colour the palette does not have, raise an issue
  rather than adding one — the palette is monochrome plus a single accent, and that constraint
  is the design. `CONTRAST` is the sole second hue and is reserved for encodings with exactly
  two opposed sides.
- **British spelling** in prose and comments: *behaviour*, *licence*, *modelling*.
- **No hype vocabulary.** The project's argument is that a model you can read beats one you
  cannot; the writing should sound like it believes that.

Logo and cover assets are generated, never hand-edited:

```bash
python src/make_logo.py     # the whole logo set from src/brand.py and src/world.py
python src/make_cover.py    # the article cover, drawn from the dataset
```

If a brand value changes, change it in `src/brand.py` and `docs/BRAND.md` in the same commit,
and re-run both scripts.

**`docs/article.md` quotes the source in full.** If your change touches a file the article
lists, re-quote it rather than editing the article by hand:

```bash
python scripts/sync_article.py --check    # what has drifted
python scripts/sync_article.py            # rewrite the listings from source
```

The script only rewrites the fenced listings. If your change makes the surrounding paragraph
wrong — a threshold the prose quotes, a behaviour it describes — fix that too; `--check` names
the files that moved so you know which paragraphs to re-read.

---

## Reporting issues

Issue templates live in `.github/ISSUE_TEMPLATE/` and are offered automatically when you open
a new issue. Pick the one that fits:

| Template | Use it for |
|---|---|
| **Bug report** | Something behaves incorrectly — a crash, a wrong number, a page that will not render |
| **New feed proposal** | You want a source added to `FEEDS` |
| **Model or feature proposal** | You want to change the model, add a feature, or alter the target |
| **Data quality report** | Clustering merged unrelated stories, a topic was miscategorised, a label looks wrong |

For anything else — a question, a documentation gap, an idea you are not sure about — open a
blank issue and describe it plainly.

**A good bug report includes** the command you ran, what you expected, what happened, the full
traceback if there was one, and your Python version and OS. If the bug involves collected
data, say whether you were running on the synthetic history or on live data, and attach the
relevant file from `data/raw/<date>/` if you can — that makes the problem reproducible offline
for everyone else.

---

## Proposing a new feed

Adding a source is the most common contribution, and the most common one to get wrong. A feed
is not free: it costs a request every day, it widens the vocabulary the lexicon must cover, and
it shifts the category mix of the whole dataset.

### Requirements

1. **Public RSS or Atom, no authentication.** If it needs a key, it cannot go in.
2. **Reasonable volume.** Roughly 10–30 items per day. A firehose drowns the other sources; a
   feed publishing twice a week adds nothing.
3. **Distinct coverage.** It must add something the existing five do not. "More AI news" is
   not a reason; "the current five have almost no hardware or semiconductor coverage" is.
4. **Stable.** A feed that reshapes its XML every few months creates maintenance nobody signed
   up for.

### How to do it

Add the entry to `FEEDS` in `src/collect_live.py`:

```python
FEEDS = {
    ...
    "yoursource": "https://example.com/feed.xml",
}
```

Then run a dry run and look hard at the output:

```bash
python src/collect_live.py --dry-run
```

Check three things. **Do the headlines cluster sensibly**, or does the new source's house style
(all-caps, a site-name suffix on every title) create false merges? **Are the categories right**,
or does the lexicon need terms for vocabulary this source uses that the others do not? **Does
the top ten still look like the day's real news**, or has one source crowded it out?

If categorisation is poor, extend `CATEGORY_TERMS` in the same PR — but only with words you
actually saw in the feed. The lexicon was built from real headlines rather than from
imagination, and that is why it works; please keep it that way.

### What to include in the PR

- The feed URL, and one sentence on what it adds
- A `--dry-run` top ten from before and after your change
- The category distribution before and after
- A note on anything you had to add to `CATEGORY_TERMS`, and which headlines motivated it

---

## Proposing a model change

The recurrence model is a logistic regression on 18 features. It is small on purpose: with a
few hundred rows, a larger model buys variance rather than signal, and standardised
coefficients mean any prediction can be explained without an interpretability library.

That said, the model is the least developed part of the project, and better ideas are welcome.

### The rules of evidence

**Report chronological-split metrics.** `src/train.py` already does the split correctly — use
it. A random-split number is not evidence and will be rejected, however good it looks.

**Compare against the current baseline, not against nothing.** The table to beat, on whatever
dataset you are testing:

| Metric | Current |
|---|---|
| Majority-class baseline | 0.560 |
| Accuracy | 0.660 |
| F1 | 0.667 |
| ROC-AUC | 0.709 |

**Say which dataset produced your numbers.** The committed history is synthetic and generated
by a noisy logistic rule, which flatters linear models. If you have real collected data, that
result is far more interesting — say how many days it covers.

**Keep the runtime honest.** Training must stay fast enough to run in a GitHub Actions job:
seconds, not minutes, and no GPU.

### What is most wanted

**Better features beat bigger models.** The most promising untested idea is the ratio of
Hacker News comments to points — a story being argued about behaves differently from one being
quietly upvoted, and neither number alone captures that. Other candidates: source diversity
rather than raw count, time-of-day of first appearance, and whether a topic's category was
already crowded that day.

**A better target.** "Appears in tomorrow's top ten" is easy to label but is defined by the
collector's own ranking. Something like "still covered by two or more sources in three days"
would be more demanding and more useful. This is a bigger change — open an issue first.

**Better labelling.** The day-to-day topic match is Jaccard overlap at 0.4 on keyword sets. It
misses continuations that changed vocabulary and occasionally joins distinct stories. Improving
this improves every metric downstream, because it reduces label noise.

### If you want to change the model class

Fine in principle, but bring evidence and keep the explainability. A gradient-boosted model
that beats the logistic regression by two points on real data but cannot be explained without
SHAP is a worse fit for this project than a linear model with a better feature. If your change
needs a new dependency, justify it against the "runs on a laptop with no keys" constraint.

---

## Other good contributions

**Tests.** There is no suite. The highest-value first tests are: `classify()` in
`github_releases.py` against a table of real tags; the clustering guard in `collect_live.py`
against the "breaks record" false-merge case; and `label_recurrence_fuzzy()` against a small
two-day fixture. Cached feeds under `data/raw/` make good fixtures.

**Clustering.** Keyword overlap is crude and embeddings would very likely beat it. The
constraint is that it must still run in under a minute on a laptop with no GPU and no paid API —
a small local sentence-transformer is a legitimate proposal; an API call is not.

**UI.** New Streamlit pages must render correctly when the logs they read are empty, and must
follow the theme through `src/settings.py` rather than hard-coding colours.

**Documentation.** If something in the README or this file was wrong or unclear when you
followed it, that is a bug worth fixing.

---

## Pull requests

Small and focused beats large and sweeping. One concern per PR.

**In the description, say:**

- What changed and why
- What you ran to check it — commands and their output
- Whether it touches `COLUMNS` (a schema change), the model, or any of the four invariants above

**Before you open it:**

```bash
ruff check .
python src/collect.py --days 45 --seed 42 && python src/train.py
python src/collect_live.py --dry-run --offline      # if you touched the collector
```

The last command needs a cached day under `data/raw/`; run a live collection once to create one.

Commits should be legible in a log: a short imperative subject line, and a body explaining why
if the reason is not obvious. Please do not force-push over review feedback — add commits, and
they can be squashed on merge.

---

## A note on the data

The dataset committed to this repository is **synthetic**, generated by `src/collect.py` to
exercise the pipeline. Model metrics computed on it describe the plumbing, not the
predictability of real trends. Please do not cite them as evidence about the world, and if you
add analysis or documentation, carry that caveat with it.
