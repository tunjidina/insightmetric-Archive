# Running InsightMetric in Docker

One image does three jobs — serve the app, run the collector, retrain the model — so there is
a single thing to build, version and ship.

```
docker build -t insightmetric .
docker run --rm -p 8501:8501 insightmetric                 # app on http://localhost:8501
```

With Compose (recommended locally, because it mounts `./data` so collected rows survive):

```
docker compose up -d                        # app on http://localhost:8501
docker compose run --rm collector           # collect today into ./data
docker compose run --rm collector --dry-run # preview, save nothing
docker compose run --rm trainer             # retrain from ./data
docker compose down
```

## The three jobs

`docker-entrypoint.sh` takes the job name as its first argument:

| Command | What runs |
|---|---|
| `app` (default) | `streamlit run Daily_Trends.py` on `$PORT` (8501 unless set) |
| `collect` | `src/collect_live.py` — news feeds, GitHub releases, HN engagement. Extra flags pass through (`--dry-run`, `--offline`, `--date`) |
| `train` | `src/train.py` |
| `mock` | `src/collect.py` — regenerates the synthetic history |
| anything else | executed as given, so `docker run --rm -it insightmetric sh` still gets you a shell |

## Why the files look the way they do

**`python:3.11-slim`, not `alpine`.** pandas, scikit-learn and matplotlib publish manylinux
wheels; Alpine's musl libc does not match them, so an Alpine build compiles all three from
source — twenty minutes and a compiler toolchain in the image, for no benefit. Slim installs
the same wheels in about a minute.

**Dependencies copied before the code.** `COPY requirements.txt` then `pip install` then
`COPY . .` means editing a page re-uses the cached install layer; the rebuild is seconds
rather than a minute. Reversing those two lines is the single most common reason Docker builds
feel slow.

**A non-root user.** The container runs as uid 10001. `data/` and `models/` are chowned to it
so the collector can still write, but nothing else in the image is writable by the process.

**`$PORT`, not a hardcoded 8501.** Render, Fly and Cloud Run all inject `$PORT`; the entrypoint
honours it, so the same image runs locally and on any of them without an override.

**A healthcheck on `/_stcore/health`.** Streamlit's own endpoint, so orchestrators can tell a
started container from a working one. `start-period=40s` covers first-run import time.

**`.dockerignore` earns its place.** It keeps `.git`, `docs/`, the screenshot PNGs and the
cached feed XML out: 29 files, about 360 KB of application payload. Without it the build
context carries the whole repository history.

## Data: baked in or mounted

The image ships the dataset and model that were committed with it, so `docker run` alone gives
a working app — useful for a demo or a one-off deploy. Anything the collector writes inside a
container is lost when that container is removed.

For a running system, mount the folders (Compose does this for you):

```
docker run --rm -p 8501:8501 -v "$PWD/data:/app/data" -v "$PWD/models:/app/models" insightmetric
```

On Windows PowerShell use `-v "${PWD}\data:/app/data"`.

The Releases and Hacker News pages show a "no log yet" notice until the collector has run at
least once, because those logs are generated rather than shipped. That is expected on a fresh
image, not a fault.

## Scheduling the daily run

Three options, in the order I would reach for them:

1. **GitHub Actions** (`.github/workflows/collect.yml`, already in the repo) — best when the
   app is hosted, since it commits the data and triggers a redeploy. No container needed.
2. **Host scheduler** — Task Scheduler or cron calling
   `docker compose run --rm collector` once a day. Simple, and failures are visible in the host's
   own logs.
3. **`docker compose --profile daily up -d`** — a `scheduler` service that loops inside the
   stack. Use it only when the stack must be self-contained on an always-on box; it is a poll
   loop, so it has no catch-up if the host is asleep at 06:15 UTC. The first two options are
   better whenever they are available.

## Deploying the image

Render can build from this Dockerfile instead of the Python runtime: in `render.yaml`, replace
`runtime: python` and the build/start commands with `runtime: docker`. The Dockerfile's
`$PORT` handling and healthcheck already match what Render expects. Fly.io and Cloud Run take
the image as-is.

The trade-off is build time: Render's free tier rebuilds the image on every commit, which is
slower than the Python runtime's cached pip install. For the current setup — where the daily
commit is *data*, not code — the Python runtime redeploys faster. Prefer Docker when you want
the same artifact to run locally, in CI and in production, and accept a slower deploy for it.

## Sizes and timings, for expectation-setting

| | |
|---|---|
| Image size | ~700 MB (base 130 MB, scikit-learn + pandas + matplotlib ~450 MB) |
| First build | 1–3 min depending on network |
| Rebuild after a code change | seconds (dependency layer is cached) |
| Container memory in use | ~250 MB serving the app |

If image size matters, the biggest single win is dropping matplotlib and the word cloud in
favour of Streamlit's native charts, which would remove roughly 200 MB. That is a real product
decision, not a packaging one, so it is not done here.
