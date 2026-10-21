#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch configured conference and journal titles from DBLP.

Each DBLP table-of-contents page is read from its XML endpoint and written to
``papers/<VENUE><YEAR>.txt``. Multiple pages belonging to the same venue/year
(for example KDD 2025) are merged and de-duplicated in source order.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

import requests
from bs4 import BeautifulSoup


OUT_DIR = "papers"
DEFAULT_BASE_URL = "https://dblp.org"
USER_AGENT = "FindPaper/1.0 (DBLP title collection; contact repository owner)"


@dataclass(frozen=True)
class Source:
    name: str
    path: str

    @property
    def venue(self) -> str:
        return self.name.rstrip("0123456789")

    @property
    def year(self) -> int:
        return int(self.name[len(self.venue) :])


def conference_sources(
    venue: str,
    slug: str,
    start_year: int,
    end_year: int,
) -> list[Source]:
    return [
        Source(f"{venue}{year}", f"conf/{slug}/{slug}{year}")
        for year in range(start_year, end_year + 1)
    ]


SOURCES = [
    Source("NIPS2019", "conf/nips/nips2019"),
    *[
        Source(f"NIPS{year}", f"conf/nips/neurips{year}")
        for year in range(2020, 2026)
    ],
    *[
        Source(f"ICCV{year}", f"conf/iccv/iccv{year}")
        for year in (2019, 2021, 2023, 2025)
    ],
    Source("KDD2025", "conf/kdd/kdd2025-1"),
    Source("KDD2025", "conf/kdd/kdd2025-2"),
    Source("ACL2019", "conf/acl/acl2019-1"),
    Source("ACL2020", "conf/acl/acl2020"),
    *[
        Source(f"ACL{year}", f"conf/acl/acl{year}-1")
        for year in range(2021, 2027)
    ],
    Source("EMNLP2019", "conf/emnlp/emnlp2019-1"),
    Source("EMNLP2020", "conf/emnlp/emnlp2020-1"),
    *[
        Source(f"EMNLP{year}", f"conf/emnlp/emnlp{year}")
        for year in range(2021, 2026)
    ],
    *[
        Source(f"TMM{year}", f"journals/tmm/tmm{year - 1998}")
        for year in range(2019, 2027)
    ],
    *[
        Source(f"TKDE{year}", f"journals/tkde/tkde{year - 1988}")
        for year in range(2019, 2027)
    ],
    *conference_sources("CIKM", "cikm", 2019, 2025),
    *conference_sources("SIGIR", "sigir", 2019, 2026),
    *conference_sources("KDD", "kdd", 2019, 2024),
    *conference_sources("MM", "mm", 2019, 2025),
    *conference_sources("CVPR", "cvpr", 2019, 2025),
    *conference_sources("IJCAI", "ijcai", 2019, 2025),
    *conference_sources("AAAI", "aaai", 2019, 2026),
    *conference_sources("ICML", "icml", 2019, 2025),
    *conference_sources("ICLR", "iclr", 2019, 2025),
    *conference_sources("WWW", "www", 2019, 2026),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch paper titles from configured DBLP venue/year pages."
    )
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        help="Only process these years, for example: --years 2025 2026",
    )
    parser.add_argument(
        "--venues",
        nargs="+",
        type=str.upper,
        help="Only process these venues, for example: --venues AAAI ACL TKDE",
    )
    parser.add_argument(
        "--refresh-existing",
        action="store_true",
        help="Re-fetch and atomically replace existing files (needed for journals).",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("DBLP_BASE_URL", DEFAULT_BASE_URL),
        help="DBLP server or official mirror (default: %(default)s).",
    )
    parser.add_argument(
        "--out-dir",
        default=OUT_DIR,
        help="Output directory (default: %(default)s).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Read timeout in seconds for large DBLP pages (default: %(default)s).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Attempts per source page (default: %(default)s).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between successful DBLP requests in seconds (default: %(default)s).",
    )
    parser.add_argument(
        "--list-sources",
        action="store_true",
        help="Print the selected output names and DBLP paths without downloading.",
    )
    return parser.parse_args()


def selected_sources(args: argparse.Namespace) -> list[Source]:
    years = set(args.years or [])
    venues = set(args.venues or [])
    return [
        source
        for source in SOURCES
        if (not years or source.year in years)
        and (not venues or source.venue in venues)
    ]


def normalize_title(title_tag) -> str:
    # Keep inline markup such as <sub>/<sup>/<i> joined to surrounding text,
    # then normalize formatting whitespace introduced by the XML source.
    return " ".join(title_tag.get_text("", strip=False).split())


def fetch_titles(
    session: requests.Session,
    source: Source,
    base_url: str,
    timeout: float,
    retries: int,
) -> list[str]:
    url = f"{base_url.rstrip('/')}/db/{source.path}.xml"
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            print(f"抓取 {source.name}: {url} (尝试 {attempt}/{retries})")
            response = session.get(url, timeout=(20, timeout))
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "xml")
            if soup.find("bht") is None:
                raise ValueError("响应不是 DBLP table-of-contents XML")
            titles = [normalize_title(tag) for tag in soup.find_all("title")]
            titles = [title for title in titles if title]
            if not titles:
                raise ValueError("DBLP 页面中没有找到 title 元素")
            return titles
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt == retries:
                break
            backoff = min(30.0, 2.0 ** attempt)
            print(f"  失败: {exc}; {backoff:.0f} 秒后重试")
            time.sleep(backoff)

    raise RuntimeError(f"抓取失败: {url}: {last_error}")


def deduplicate(titles: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for title in titles:
        if title not in seen:
            seen.add(title)
            result.append(title)
    return result


def write_titles(out_path: str, titles: list[str]) -> None:
    tmp_path = f"{out_path}.tmp"
    with open(tmp_path, "w", encoding="utf-8", newline="\n") as file:
        for title in titles:
            file.write(f"{title}\n")
        file.flush()
        os.fsync(file.fileno())
    os.replace(tmp_path, out_path)


def main() -> int:
    args = parse_args()
    sources = selected_sources(args)
    if not sources:
        print("没有匹配的 DBLP 来源。", file=sys.stderr)
        return 2

    grouped: dict[str, list[Source]] = defaultdict(list)
    for source in sources:
        grouped[source.name].append(source)

    if args.list_sources:
        for name in sorted(grouped):
            for source in grouped[name]:
                print(f"{name}\t{args.base_url.rstrip('/')}/db/{source.path}.xml")
        return 0

    os.makedirs(args.out_dir, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    failures: list[str] = []

    for name in sorted(grouped):
        out_path = os.path.join(args.out_dir, f"{name}.txt")
        if os.path.exists(out_path) and not args.refresh_existing:
            print(f"跳过 {name}: {out_path} 已存在")
            continue

        combined: list[str] = []
        try:
            for source in grouped[name]:
                combined.extend(
                    fetch_titles(
                        session,
                        source,
                        args.base_url,
                        args.timeout,
                        max(1, args.retries),
                    )
                )
                if args.delay > 0:
                    time.sleep(args.delay)
        except RuntimeError as exc:
            print(exc, file=sys.stderr)
            failures.append(name)
            continue

        titles = deduplicate(combined)
        write_titles(out_path, titles)
        print(f"已写入 {len(titles)} 条到 {out_path}")

    if failures:
        print(f"失败的收录: {', '.join(failures)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
