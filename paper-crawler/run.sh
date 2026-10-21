#!/usr/bin/env bash
# set -euo pipefail

# Simple orchestrator for the arXiv → PDF → GROBID pipeline.
# Requires a reachable GROBID service; set GROBID_URL if not http://localhost:8070

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

python -m pip install -r requirements.txt

python scripts/01_search_arxiv.py
python scripts/02_download_arxiv_source.py
python scripts/03_download_pdf.py
python scripts/04_run_grobid.py
python scripts/05_parse_grobid.py

echo "Pipeline finished. Outputs: data/raw/*, data/parsed/*"
