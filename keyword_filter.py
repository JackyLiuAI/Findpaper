#!/usr/bin/env python3
"""
Filter paper titles by semantic similarity to a set of keywords using a Qwen embedding model.
Builds/loads the cached index from semantic_search.py and writes the top-N percent titles
into a new folder (one file per conference), plus a merged TSV summary.
"""

import argparse
import math
import os
from collections import defaultdict
from typing import List, Tuple

import numpy as np

import semantic_search


def compute_scores(
    keywords: List[str],
    model_name: str,
    embeddings: np.ndarray,
    model_cache_dir: str = None,
    offline: bool = False,
) -> np.ndarray:
    model = semantic_search._get_model(model_name, model_cache_dir=model_cache_dir, offline=offline)
    k_embs = model.encode(keywords, convert_to_numpy=True, normalize_embeddings=True)
    scores = embeddings @ k_embs.T
    return scores.max(axis=1)


def select_top_indices(scores: np.ndarray, percent: float) -> np.ndarray:
    percent = max(0.0, min(percent, 1.0))
    if percent == 0.0:
        return np.array([], dtype=int)
    n = scores.shape[0]
    k = max(1, int(math.ceil(n * percent)))
    idx = np.argpartition(-scores, k - 1)[:k]
    idx = idx[np.argsort(-scores[idx])]
    return idx


def write_outputs(
    titles: List[str],
    sources: List[str],
    scores: np.ndarray,
    selected_idx: np.ndarray,
    out_dir: str,
):
    os.makedirs(out_dir, exist_ok=True)
    by_conf: defaultdict[str, List[Tuple[float, str]]] = defaultdict(list)
    for i in selected_idx:
        by_conf[sources[i]].append((float(scores[i]), titles[i]))

    summary_path = os.path.join(out_dir, "selected.tsv")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("score\tsource\ttitle\n")
        for conf, items in sorted(by_conf.items()):
            items_sorted = sorted(items, key=lambda x: -x[0])
            for score, title in items_sorted:
                f.write(f"{score:.6f}\t{conf}\t{title}\n")

    for conf, items in by_conf.items():
        conf_path = os.path.join(out_dir, f"{conf}.txt")
        items_sorted = sorted(items, key=lambda x: -x[0])
        with open(conf_path, "w", encoding="utf-8") as f:
            for _, title in items_sorted:
                f.write(f"{title}\n")


def parse_args():
    parser = argparse.ArgumentParser(description="Filter papers by keyword similarity using Qwen embeddings")
    parser.add_argument("--papers-dir", default="papers", help="Directory with <CONF>.txt files")
    parser.add_argument("--model", default="Qwen/Qwen3-Embedding-0.6B", help="Qwen embedding model")
    parser.add_argument("--cache", default=None, help="Path to index cache npz; defaults to auto path under papers dir")
    parser.add_argument("--force-rebuild", action="store_true", help="Force rebuild index even if cache exists")
    parser.add_argument("--model-cache-dir", default=None, help="Local model cache directory")
    parser.add_argument("--offline", action="store_true", help="Offline mode (only use local cache)")
    parser.add_argument("--percent", type=float, default=0.3, help="Top fraction to keep (0-1), default 0.2 = 20%%")
    parser.add_argument("--out-dir", default="papers_top30", help="Output folder for filtered papers")
    parser.add_argument(
        "--keywords",
        nargs="+",
        default=[
            "MLLMs",
            "Multimodal LLMs",
            "Multimodal Large Language Models",
            "Large Language models",
        ],
        help="Keyword phrases to match",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    titles, sources, embeddings, cache_path = semantic_search.build_or_load_index(
        model_name=args.model,
        papers_dir=args.papers_dir,
        cache_path=args.cache,
        force_rebuild=args.force_rebuild,
        model_cache_dir=args.model_cache_dir,
        offline=args.offline,
    )

    scores = compute_scores(
        keywords=args.keywords,
        model_name=args.model,
        embeddings=embeddings,
        model_cache_dir=args.model_cache_dir,
        offline=args.offline,
    )

    selected_idx = select_top_indices(scores, args.percent)
    write_outputs(titles, sources, scores, selected_idx, args.out_dir)

    print(f"Loaded index from: {cache_path}")
    print(f"Total titles: {len(titles)}; selected: {len(selected_idx)} ({args.percent*100:.1f}% target)")
    print(f"Output written to: {args.out_dir} (per-conf files) and {os.path.join(args.out_dir, 'selected.tsv')}")


if __name__ == "__main__":
    main()
