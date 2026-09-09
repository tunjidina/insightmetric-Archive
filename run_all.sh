#!/usr/bin/env bash
# Rebuild everything from scratch: data -> EDA -> model. Then launch the app.
set -e
python src/collect.py --days 45 --seed 42
python src/eda.py
python src/train.py
streamlit run Daily_Trends.py
