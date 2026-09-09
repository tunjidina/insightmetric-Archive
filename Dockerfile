# InsightMetric - app, collector and trainer in one image.
#
#   docker build -t insightmetrics .
#   docker run --rm -p 8501:8501 insightmetrics                       # the app
#   docker run --rm -v "$PWD/data:/app/data" insightmetrics collect    # one collection run
#
# The same image serves the app (default) or runs the collector / trainer
# (see docker-entrypoint.sh), so there is exactly one thing to build and version.

FROM python:3.11-slim AS base

# Faster, quieter, reproducible Python inside containers.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_HEADLESS=true \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app

# curl only for the HEALTHCHECK; nothing else needs system packages (all wheels are binary).
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

# Dependencies first so code changes do not invalidate the (slow) install layer.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Application code, data and model. .dockerignore keeps the raw feed cache and scratch out.
COPY . .

# Run as an unprivileged user; data/ and models/ stay writable for the collector.
RUN useradd --create-home --uid 10001 app \
 && chown -R app:app /app
USER app

EXPOSE 8501
ENV PORT=8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS "http://localhost:${PORT}/_stcore/health" || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["app"]
