import json
import requests
from pathlib import Path


def main():
    out_dir = Path("data/raw/pdf")
    out_dir.mkdir(parents=True, exist_ok=True)

    meta_path = Path("data/meta/papers.jsonl")
    if not meta_path.exists():
        raise SystemExit("papers.jsonl not found. Run 01_search_arxiv.py first.")

    with meta_path.open(encoding="utf-8") as f:
        for line in f:
            paper = json.loads(line)
            arxiv_id = paper.get("arxiv_id")
            pdf_url = paper.get("pdf_url")
            if not arxiv_id or not pdf_url:
                continue

            pdf_path = out_dir / f"{arxiv_id}.pdf"
            if pdf_path.exists():
                continue

            resp = requests.get(pdf_url, timeout=30)
            if resp.status_code == 200:
                pdf_path.write_bytes(resp.content)


if __name__ == "__main__":
    main()
