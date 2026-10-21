# DBLP → arXiv → PDF → GROBID Pipeline

A minimal, reproducible pipeline that searches arXiv by title, downloads LaTeX sources or PDFs, and processes PDFs via GROBID into TEI and JSON sections suitable for downstream LLM use.

## Layout

```
paper-crawler/
├── data/
│   ├── input/           # titles.txt (one title per line)
│   ├── raw/
│   │   ├── arxiv_source/
│   │   └── pdf/
│   ├── parsed/
│   │   ├── tex/
│   │   └── grobid/
│   └── meta/
│       └── papers.jsonl
├── grobid/
│   └── docker-compose.yml
├── scripts/
│   ├── 01_search_arxiv.py
│   ├── 02_download_arxiv_source.py
│   ├── 03_download_pdf.py
│   ├── 04_run_grobid.py
│   └── 05_parse_grobid.py
├── requirements.txt
└── run.sh
```

## Quickstart

```bash
# 1) deps
python -m pip install -r requirements.txt

# 2) prepare input titles
# edit data/input/titles.txt

# 3) search arXiv and write meta
env PYTHONPATH=. python scripts/01_search_arxiv.py

# 4) download LaTeX sources (tar.gz)
env PYTHONPATH=. python scripts/02_download_arxiv_source.py

# 5) download PDFs (fallback)
env PYTHONPATH=. python scripts/03_download_pdf.py

# 6) ensure a GROBID service is reachable
# - default: http://localhost:8070
# - inside Docker: export GROBID_URL="http://host.docker.internal:8070" (or your host IP)
# - remote: export GROBID_URL="https://your-grobid-server"

# 7) process PDFs via GROBID (Python client)
env PYTHONPATH=. python scripts/04_run_grobid.py

# 8) parse GROBID XML to JSONL
env PYTHONPATH=. python scripts/05_parse_grobid.py
```

## Notes

- Network calls hit arXiv API; be gentle with rate limits.
- GROBID requires Docker; adjust `JAVA_OPTS` in `grobid/docker-compose.yml` for memory.
- Outputs: TEI XML in `data/parsed/grobid` and consolidated JSONL in `data/parsed/papers.jsonl`.
