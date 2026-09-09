# LinkedIn announcement — three versions

Before posting, replace: `[REPO LINK]`, `[ARTICLE LINK]`, and `[APP LINK]` (omit the app link
entirely until it is actually deployed — see the note at the end).

---

## Version A — Build-in-public, technical narrative

*Best for the data/AI audience. Leads with the problem, not the tool.*

Most "AI trend" commentary is opinion wearing a lab coat.

So I built the boring alternative: a small system that collects tech trends every day, stores them in a proper schema, and asks one narrow question of the data — will this topic still be trending tomorrow?

What it does, end to end:

→ A data agent reads five public RSS feeds each morning (Hacker News, TechCrunch, The Verge, Ars Technica, Wired), plus the release feeds of twelve open-source repositories.

→ Headlines are clustered into topics by keyword overlap, categorised against a lexicon, and scored for sentiment locally with VADER.

→ Hacker News points, comments and points-per-hour ride along, so "developer attention" becomes a number rather than a vibe.

→ A logistic regression predicts whether each topic recurs the next day. Standardised coefficients are the feature importance — no SHAP, no gradient boosting, nothing that would obscure a model this small.

→ A Streamlit app puts it on screen: today's trends with a prediction badge, weekly roll-ups, category comparisons, and the release log.

No API keys. No paid services. Roughly 2,000 lines of Python, runs in under a minute, ships as one Docker image.

The honest part: the metrics I have so far (66% accuracy against a 56% baseline, ROC-AUC 0.71) come from 45 days of *synthetic* data built to test the pipeline. That number says the plumbing works. It does not say trends are predictable. Live collection has only just started, and I expect the real figure to be lower.

I would rather publish that caveat than a flattering chart.

Full write-up and code below. Happy to hear where you would attack the methodology.

[ARTICLE LINK]
[REPO LINK]

#DataScience #MachineLearning #Python #OpenSource #Analytics

---

## Version B — Lead with a finding

*Higher engagement potential. Opens with something concrete and slightly counter-intuitive.*

I pointed a data agent at twelve major open-source repositories for a week and logged every release.

110 releases. Only 21 were stable minor or major versions. The rest were release candidates, nightlies and patches — about two "real" releases a week across PyTorch, pandas, scikit-learn, LangChain, vLLM and friends combined.

That single number changed a design decision. My first instinct was to treat every release as a signal. The data said most releases are noise, so only stable versions now reach the trend list; everything else is logged and ignored.

This is from a small project I have been building: a daily tech-trend intelligence system. It reads five public RSS feeds and a set of GitHub release feeds each morning, clusters headlines into topics, scores sentiment, tracks Hacker News engagement, and runs a logistic regression that predicts whether a topic will still be trending tomorrow.

Three other things the real data taught me that a tutorial would not:

→ Two headlines sharing two keywords are not the same story. "LibreOffice breaks download records" and "Microsoft breaks another patch Tuesday record" merged into one topic until I required the overlap to be a meaningful share of both.

→ A category lexicon written from imagination misses. Rebuilding mine from the words the feeds actually used took cybersecurity detection from 2 clusters to 13 on the same 80 headlines.

→ On a 20-item front page, a keyword that appears in one story is not a theme. It is that story.

The model's current numbers come from synthetic data, so they measure the pipeline rather than the world. Live collection has just begun; I will publish what the real figures look like, flattering or not.

Write-up and code:

[ARTICLE LINK]
[REPO LINK]

#DataEngineering #MachineLearning #Python #Analytics #BuildInPublic

---

## Version C — Short bullet summary

*Matches your standalone-post format. Lowest friction, easiest to skim.*

New project: a lightweight daily tech-trend intelligence system.

What it does:

• Reads five public RSS feeds and twelve GitHub release feeds every morning
• Clusters headlines into topics, categorises them, scores sentiment locally
• Tracks Hacker News points, comments and velocity as an attention signal
• Predicts whether each topic recurs tomorrow (logistic regression, chronological split)
• Serves it all through a six-page Streamlit app

Design constraints I set myself:

• No API keys, no paid services, no vendor lock-in
• Every step reproducible offline from cached feeds
• The simplest model that can be explained on one slide

Current accuracy figures come from synthetic data and measure the pipeline, not the world. Real numbers to follow once enough live days accumulate.

Code and full write-up:

[ARTICLE LINK]
[REPO LINK]

#DataScience #Python #MachineLearning #OpenSource

---

## Notes before you post

**The app link.** There is no deployed URL yet. Do not include `[APP LINK]` until Render is
live, and remember the free tier sleeps after 15 minutes idle — a cold start of 30–60 seconds
on a post that lands well will cost you readers. If the link is going in the post, warm it up
first, or use Streamlit Community Cloud, which does not sleep.

**The accuracy caveat is not optional.** Your audience includes people who will ask which
dataset produced 0.66. Leading with the caveat is what makes the rest of the post credible;
burying it is what gets a comment you have to answer defensively.

**Sequencing.** Publish the Medium article first, then post. A LinkedIn post pointing at a
live article outperforms one promising an article soon.

**First two lines.** LinkedIn truncates at roughly 200 characters. All three versions are
written so the hook survives the fold — check on mobile before publishing.
