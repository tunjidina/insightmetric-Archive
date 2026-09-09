## What changed and why

<!-- One or two sentences. If this closes an issue, say "Closes #123". -->

## How I checked it

<!-- Commands and their output. -->

```
ruff check .
python src/collect.py --days 45 --seed 42 && python src/train.py
```

## Does this touch anything load-bearing?

- [ ] Changes `COLUMNS` in `src/collect.py` (**schema change** — say so explicitly)
- [ ] Changes the model, its features, or the prediction target
- [ ] Changes clustering, categorisation or recurrence labelling
- [ ] Adds a dependency
- [ ] None of the above

## Invariants

- [ ] Raw feed responses are still cached, and `--offline` still rebuilds a day exactly
- [ ] Feature engineering still lives only in `src/features.py`
- [ ] Evaluation is still chronological, not random
- [ ] No new paid service or API key
