#!/usr/bin/env bash

# Editable defaults
PAPERS_DIR="papers"
MODEL="Qwen/Qwen3-Embedding-4B"
TOP_K=100
CACHE="/workspace/FindPaper/papers/_index_Qwen_Qwen3-Embedding-4B.npz"
FORCE_REBUILD=0  # set to 1 to ignore cache
QUERY="Diffusion for Sequential Recommendation"

args=(
	--papers-dir "${PAPERS_DIR}"
	--model "${MODEL}"
	--top-k "${TOP_K}"
)

if [[ -n "${CACHE}" ]]; then
	args+=(--cache "${CACHE}")
fi

if [[ "${FORCE_REBUILD}" == "1" ]]; then
	args+=(--force-rebuild)
fi

if [[ -n "${QUERY}" ]]; then
	args+=(--query "${QUERY}")
fi

python semantic_search.py "${args[@]}"
