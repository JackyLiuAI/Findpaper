# -*- coding: utf-8 -*-
"""
Semantic search over paper titles using a pre-trained Sentence-BERT model.
Reads titles from the 'papers/' directory (one title per line in <CONF>.txt files),
builds embeddings index with caching, and performs cosine similarity search.
"""

import os
# Respect an externally selected GPU; leave device selection to the launcher.
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
import glob
import argparse
import hashlib
import numpy as np
from typing import List, Tuple


try:
    from sentence_transformers import SentenceTransformer
except Exception as e:
    raise RuntimeError("请先安装依赖：pip install -r requirements.txt") from e


def load_titles(papers_dir: str) -> Tuple[List[str], List[str]]:
    titles: List[str] = []
    sources: List[str] = []
    for path in sorted(glob.glob(os.path.join(papers_dir, '*.txt'))):
        conf = os.path.splitext(os.path.basename(path))[0]
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    t = line.strip()
                    if t:
                        titles.append(t)
                        sources.append(conf)
        except Exception:
            # 跳过无法读取的文件
            continue
    # 去重并保序
    seen = set()
    dedup_titles: List[str] = []
    dedup_sources: List[str] = []
    for t, s in zip(titles, sources):
        if t in seen:
            continue
        seen.add(t)
        dedup_titles.append(t)
        dedup_sources.append(s)
    return dedup_titles, dedup_sources


def corpus_fingerprint(papers_dir: str) -> str:
    """Return a content fingerprint that changes when the title corpus changes."""
    digest = hashlib.sha256()
    for path in sorted(glob.glob(os.path.join(papers_dir, '*.txt'))):
        digest.update(os.path.basename(path).encode('utf-8'))
        digest.update(b'\0')
        with open(path, 'rb') as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b''):
                digest.update(chunk)
    return digest.hexdigest()


def _get_model(model_name: str, model_cache_dir: str = None, offline: bool = False):
    if offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", model_cache_dir or os.environ.get("SENTENCE_TRANSFORMERS_HOME", ""))

    kwargs = {}
    if model_cache_dir:
        kwargs["cache_folder"] = model_cache_dir
        # Also hint HF cache root for huggingface_hub-based downloads
        os.environ.setdefault("HF_HOME", model_cache_dir)

    try:
        return SentenceTransformer(model_name, **kwargs)
    except Exception as e:
        if offline:
            raise RuntimeError("离线模式下未找到本地模型缓存，请先联网下载或指定本地路径作为 --model") from e
        raise


def build_or_load_index(
    model_name: str,
    papers_dir: str,
    cache_path: str = None,
    force_rebuild: bool = False,
    model_cache_dir: str = None,
    offline: bool = False,
):
    titles, sources = load_titles(papers_dir)
    current_fingerprint = corpus_fingerprint(papers_dir)
    if cache_path is None:
        cache_path = os.path.join(papers_dir, f"_index_{model_name.replace('/', '_')}.npz")

    if (not force_rebuild) and os.path.exists(cache_path):
        try:
            data = np.load(cache_path, allow_pickle=True)
            cached_model = str(data['model_name']) if 'model_name' in data.files else None
            cached_fingerprint = (
                str(data['corpus_fingerprint'])
                if 'corpus_fingerprint' in data.files
                else None
            )
            if cached_model == model_name and cached_fingerprint == current_fingerprint:
                embeddings = data['embeddings']
                titles = list(data['titles'])
                sources = list(data['sources'])
                return titles, sources, embeddings, cache_path
        except Exception:
            pass

    model = _get_model(model_name, model_cache_dir=model_cache_dir, offline=offline)
    embeddings = model.encode(
        titles,
        batch_size=32,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    np.savez_compressed(
        cache_path,
        model_name=model_name,
        corpus_fingerprint=current_fingerprint,
        embeddings=embeddings,
        titles=np.array(titles, dtype=object),
        sources=np.array(sources, dtype=object),
    )
    return titles, sources, embeddings, cache_path


def search(
    query: str,
    titles: List[str],
    sources: List[str],
    embeddings: np.ndarray,
    model_name: str,
    top_k: int = 20,
    model_cache_dir: str = None,
    offline: bool = False,
):
    model = _get_model(model_name, model_cache_dir=model_cache_dir, offline=offline)
    q_emb = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
    scores = embeddings @ q_emb[0]
    idx = np.argsort(-scores)[:top_k]
    results = []
    for i in idx:
        results.append((float(scores[i]), titles[i], sources[i]))
    return results


def main():
    parser = argparse.ArgumentParser(description='基于 Sentence-BERT 的论文题目语义检索')
    parser.add_argument('--papers-dir', default='papers', help='包含 <CONF>.txt 的目录，默认 papers')
    parser.add_argument('--model', default='Qwen/Qwen3-Embedding-0.6B', help='Sentence-BERT 预训练模型名')
    parser.add_argument('--top-k', type=int, default=20, help='返回前 K 条结果')
    parser.add_argument('--cache', default=None, help='索引缓存路径（npz），默认在 papers 目录下自动生成')
    parser.add_argument('--force-rebuild', action='store_true', help='忽略缓存，强制重建索引')
    parser.add_argument('--model-cache-dir', default=None, help='本地模型缓存目录（覆盖默认的 HuggingFace 缓存位置）')
    parser.add_argument('--offline', action='store_true', help='离线模式（仅使用本地缓存，不访问网络）')
    parser.add_argument('--query', default=None, help='检索关键字/句子')
    args = parser.parse_args()

    titles, sources, embeddings, cache_path = build_or_load_index(
        args.model, args.papers_dir, args.cache, args.force_rebuild, args.model_cache_dir, args.offline
    )
    print(f'索引构建完成: {len(titles)} 条目, 缓存文件: {cache_path}')

    query = args.query
    if not query:
        try:
            query = input('请输入检索关键字/句子: ').strip()
        except EOFError:
            print('未提供查询。使用 --query 传入检索词。')
            return
    if not query:
        print('查询为空，已退出。')
        return

    results = search(
        query, titles, sources, embeddings, args.model, args.top_k, args.model_cache_dir, args.offline
    )
    print(f'Top-{args.top_k} 结果:')
    for score, title, conf in results:
        print(f'[{conf}] {title}   (cos={score:.4f})')


if __name__ == '__main__':
    main()
