import feedparser
import urllib.parse
import json
from difflib import SequenceMatcher
from pathlib import Path


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def search_arxiv(title: str, max_results: int = 5):
    query = f'ti:"{title}"'
    url = (
        "http://export.arxiv.org/api/query?"
        f"search_query={urllib.parse.quote(query)}"
        f"&start=0&max_results={max_results}"
    )
    return feedparser.parse(url).entries


def main():
    input_path = Path("data/input/titles.txt")
    output_path = Path("data/meta/papers.jsonl")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    results = []
    with input_path.open(encoding="utf-8") as f:
        titles = [l.strip() for l in f if l.strip()]

    for title in titles:
        entries = search_arxiv(title)
        best, score = None, 0.0
        for entry in entries:
            s = similarity(title, entry.title)
            if s > score:
                best, score = entry, s

        if best and score > 0.8:
            arxiv_id = best.id.split("/")[-1].split("v")[0]
            results.append(
                {
                    "title": title,
                    "arxiv_id": arxiv_id,
                    "matched_title": best.title,
                    "score": score,
                    "pdf_url": best.links[1].href,
                }
            )
        else:
            results.append({"title": title, "arxiv_id": None})

    with output_path.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
