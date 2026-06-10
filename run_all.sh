#!/usr/bin/env bash
set -e
python src/generate_realistic_synthetic_data.py
python src/run_pipeline.py
