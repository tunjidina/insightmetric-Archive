# Deploying InsightMetric on Render (free tier)

## How it fits together

```
GitHub Actions (06:15 UTC daily)          Render (free web service)
  python src/collect_live.py   ──commit──▶  auto-deploys on push
  weekly: python src/train.py                streamlit run Daily_Trends.py
  git push data/ models/                     reads data/*.parquet, models/*.joblib
```

The free Render instance has no persistent disk and restarts often, so the hosted app is
**read-only**. All collection happens in GitHub Actions, which commits the data files; every
commit triggers a redeploy. Nothing on the server is ever written to.

Files that make this work:

| File | Purpose |
|---|---|
| `render.yaml` | Render Blueprint: service definition, start command, env vars |
| `.github/workflows/collect.yml` | Daily collector + weekly retrain, commits data back to the repo |
| `requirements.txt` | Pinned upper bounds so a future Streamlit/pandas release cannot break the deploy |
| `DEPLOYED=1` env var | Hides "Save as default" and the dark-mode toggle (both single-user features) |

## One-time setup (about 15 minutes)

### 1. Put the project in a GitHub repository

From `Documents\tech_trends` in a terminal (Git for Windows, or GitHub Desktop):

```
git init
git add .
git commit -m "InsightMetric: daily tech trends dataset + micro insights app"
```

Create an empty repository on github.com (public is simplest; Actions minutes are unlimited
for public repos), then:

```
git remote add origin https://github.com/<you>/insightmetric.git
git branch -M main
git push -u origin main
```

`data/raw/` is git-ignored (the cached feed XML is not needed on the server), but
`data/*.parquet`, `data/*.csv` and `models/` are committed on purpose: the app reads them.

Before the first push, decide whether the repo starts with the **mock** history or **empty**
live data. For a public URL, mock data with a clear banner is fine for the article launch;
for a "real" dashboard, delete `data/tech_trends.csv` and `.parquet`, run
`python src\collect_live.py` once locally, retrain later. The Actions workflow appends to
whatever is committed.

### 2. Let the workflow commit

On github.com: **Settings → Actions → General → Workflow permissions → "Read and write
permissions"**, then Save. Without this the daily commit step fails with a 403.

Test it: **Actions → collect-daily → Run workflow**. It should finish in about two minutes
and produce a commit named `data: collect <date>`.

### 3. Create the Render service from the Blueprint

1. Sign in to render.com and connect your GitHub account when prompted.
2. **New → Blueprint**, pick the repository. Render reads `render.yaml` and shows one
   service, `insightmetric`, on the free plan. Click **Apply**.
3. First build takes 3–5 minutes (installing scikit-learn and matplotlib is the slow part).
   The URL will be `https://insightmetric.onrender.com` or a suffixed variant if the name
   is taken.

That is the whole deployment. Every commit the workflow makes redeploys the app automatically
(`autoDeployTrigger: commit` in the Blueprint).

## What to expect on the free tier

- **Cold starts.** After 15 minutes without visitors the instance sleeps; the next visitor
  waits 30–60 seconds. Fine for an article link, annoying for a demo: open it a minute before.
- **750 hours/month** of instance time. One always-on free service fits; two would not.
- **No disk.** The download buttons still work (the files are read from the repo checkout),
  but nothing a visitor does is saved, and the Settings page says so.
- **Memory.** 512 MB. The app loads a few hundred rows and a small model; comfortably under.

## Updating the app

Push to `main`. Code changes deploy like data changes. If a deploy fails, Render keeps the
previous version live; the build log (Render dashboard → service → Logs) shows why.

## Rolling back to local-only

Nothing about the project changed for local use. `streamlit run Daily_Trends.py` on your PC
still has the theme toggle and settings persistence; only `DEPLOYED=1` hides them.

## Alternatives considered

- **Streamlit Community Cloud** is also free, has no cold-start on the free tier, and deploys
  from GitHub in one click, but it is Streamlit-only and the app must be in a public repo.
  If Render's cold starts bother you, this is the easier trade.
- **Render Cron Job** would let the server collect the data itself, but cron jobs and
  persistent disks are paid features; GitHub Actions does the same job for free.
