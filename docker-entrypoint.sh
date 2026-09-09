#!/bin/sh
# One image, three jobs. First argument selects the job; anything else is passed to sh.
#   app      - serve the Streamlit app (default). Honours $PORT so it also works on Render.
#   collect  - run the daily collector once (news feeds, GitHub releases, HN engagement)
#   train    - retrain the recurrence model on the current dataset
#   mock     - regenerate the 45-day mock history (fresh containers with no data)
set -e
case "${1:-app}" in
  app)     exec streamlit run Daily_Trends.py --server.port "${PORT:-8501}" --server.address 0.0.0.0 ;;
  collect) shift; exec python src/collect_live.py "$@" ;;
  train)   exec python src/train.py ;;
  mock)    shift; exec python src/collect.py "$@" ;;
  *)       exec "$@" ;;
esac
