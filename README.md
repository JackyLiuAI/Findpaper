# FindPaper Semantic Search

使用预训练的 Sentence-BERT 模型对 `papers/` 目录下的论文题目进行语义检索。

## 更新论文收录

根目录的 `paper_crawler.py` 从 DBLP 的会议/期刊目录页获取标题，并写入
`papers/<VENUE><YEAR>.txt`。请使用项目的 `findpaper` conda 环境：

```bash
# 查看当前配置的 2026 年来源，不发起下载
conda run -n findpaper python paper_crawler.py --years 2026 --list-sources

# 抓取 2026 年新收录；期刊年度卷会随 DBLP 持续更新，因此需要刷新已有文件
conda run -n findpaper python paper_crawler.py \
  --years 2026 \
  --refresh-existing

# 只更新指定 venue
conda run -n findpaper python paper_crawler.py \
  --years 2026 \
  --venues AAAI ACL TKDE TMM \
  --refresh-existing
```

爬虫读取 DBLP XML 端点，按来源顺序去重，并采用临时文件原子替换，避免网络失败时
破坏已有清单。若主站限流，可切换到 DBLP 官方镜像：

```bash
conda run -n findpaper python paper_crawler.py \
  --years 2026 \
  --refresh-existing \
  --base-url https://dblp.dagstuhl.de
```

`paper-crawler/` 子目录是标题收录之后的 arXiv、PDF 和 GROBID 全文处理流水线，
不负责生成顶会/顶刊标题清单。

## 准备

```bash
pip install -r requirements.txt
```

确保已有由爬虫生成的 `papers/` 目录（例如 `papers/ICLR2021.txt` 等），每行一个题目。

## 用法

- 构建索引并进行一次查询：

```bash
python semantic_search.py --query "entailment"
```

- 指定模型、Top-K 和缓存位置：

```bash
python semantic_search.py \
  --model sentence-transformers/all-MiniLM-L6-v2 \
  --top-k 30 \
  --cache papers/_index_all-MiniLM-L6-v2.npz \
  --query "graph neural network"
```

- 强制重建索引（忽略已有缓存）：

```bash
python semantic_search.py --force-rebuild --query "multimodal"
```

- 离线/本地缓存运行（避免联网）：

```bash
# 若已下载过模型，可开启离线并指定本地缓存目录
HF_HUB_OFFLINE=1 \
python semantic_search.py \
  --offline \
  --model-cache-dir ./.model_cache \
  --query "graph neural network"

# 也可将模型目录作为 --model 指定（如本地 models/all-MiniLM-L6-v2）
python semantic_search.py \
  --model ./models/all-MiniLM-L6-v2 \
  --offline \
  --query "retrieval"
```

## 说明

- 首次运行会在 `papers/` 下生成索引缓存（`.npz`），后续查询会直接加载以加速。
- `papers/*.txt` 有变化时，旧索引会自动失效并在下次检索时重建。
- 如需更换模型，传入 `--model` 即可，脚本会为不同模型维护独立缓存。
- 如需完全离线运行，请先在联网环境下下载模型，或直接使用本地模型目录作为 `--model`，并结合 `--offline` 与 `--model-cache-dir`。
