"""
参考文献生成服务。

流程：
1. LLM 提取检索关键词
2. 并发调用 SerpAPI Google Scholar
3. LLM 进行相关性筛选
4. 使用实际返回字段格式化参考文献
5. 返回已编号字符串
"""

import asyncio
import json
import logging

import httpx
from langchain_core.output_parsers import StrOutputParser

from app.config import get_settings
from app.llm.client import create_llm
from app.llm.prompts.thesis_reference_prompt import (
    REFERENCE_FILTER_PROMPT,
    REFERENCE_KEYWORD_PROMPT,
)

logger = logging.getLogger(__name__)

SERPAPI_BASE = "https://serpapi.com/search"


async def _search_scholar(query: str, num: int = 8) -> list[dict]:
    """调用 SerpAPI Google Scholar，失败返回空列表。"""
    api_key = get_settings().serpapi_key
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                SERPAPI_BASE,
                params={
                    "engine": "google_scholar",
                    "q": query,
                    "num": num,
                    "api_key": api_key,
                },
            )
            response.raise_for_status()
            return response.json().get("organic_results", [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("SerpAPI 搜索失败 query=%r: %s", query, exc)
        return []


def _format_one_reference(item: dict, index: int, is_zh: bool) -> str:
    """使用 SerpAPI 实际字段格式化单条参考文献，不补造任何信息。"""
    title = item.get("title", "").strip()
    if not title:
        return ""

    publication_info = item.get("publication_info", {})
    summary = publication_info.get("summary", "")
    authors_list = publication_info.get("authors", [])

    if authors_list:
        authors = ", ".join(
            author.get("name", "").strip()
            for author in authors_list[:3]
            if author.get("name")
        )
        if len(authors_list) > 3 and authors:
            authors += ", 等" if is_zh else ", et al."
    elif summary and " - " in summary:
        authors = summary.split(" - ", 1)[0].strip()
    else:
        authors = ""

    journal = ""
    year = ""
    if " - " in summary:
        rest = summary.split(" - ", 1)[1]
        parts = [part.strip() for part in rest.split(",") if part.strip()]
        if parts:
            journal = parts[0]
        for part in reversed(parts[1:]):
            if part.isdigit() and len(part) == 4:
                year = part
                break

    segments: list[str] = []
    if authors:
        segments.append(authors)
    segments.append(f"{title}[J]")
    if journal:
        segments.append(journal)
    if year:
        segments.append(year)

    body = ". ".join(segments).strip()
    if not body.endswith("."):
        body += "."
    return f"[{index}] {body}"


async def _filter_results(
    llm,
    title: str,
    results: list[dict],
    label: str,
    fallback_num: int = 5,
) -> list[dict]:
    """基于标题和 summary 进行相关性筛选，失败则取前 N 条。"""
    if not results:
        return []

    try:
        chain = REFERENCE_FILTER_PROMPT | llm | StrOutputParser()
        results_json = json.dumps(
            [
                {
                    "index": i,
                    "title": item.get("title", ""),
                    "summary": item.get("publication_info", {}).get("summary", ""),
                }
                for i, item in enumerate(results)
            ],
            ensure_ascii=False,
        )
        raw = await chain.ainvoke({"title": title, "results_json": results_json})
        keep_indices = json.loads(raw.strip()).get("keep", [])
        return [results[i] for i in keep_indices if isinstance(i, int) and i < len(results)]
    except Exception as exc:  # noqa: BLE001
        logger.warning("%s 文献筛选失败，回退前几条: %s", label, exc)
        return results[:fallback_num]


async def generate_references(title: str, outline: str) -> str:
    """
    生成参考文献列表。
    SERPAPI_KEY 未配置时直接返回空字符串。
    """
    settings = get_settings()
    if not settings.serpapi_key:
        logger.info("SERPAPI_KEY 未配置，跳过参考文献生成")
        return ""

    llm = create_llm(model=settings.thesis_outline_model, temperature=0, max_tokens=512)

    try:
        keyword_chain = REFERENCE_KEYWORD_PROMPT | llm | StrOutputParser()
        raw_keywords = await keyword_chain.ainvoke(
            {"title": title, "outline": outline[:2000]}
        )
        keyword_data = json.loads(raw_keywords.strip())
        zh_query = keyword_data.get("zh") or title
        en_queries = keyword_data.get("en") or [title]
        if not isinstance(en_queries, list):
            en_queries = [title]
        en_queries = [str(query).strip() for query in en_queries[:1] if str(query).strip()]
        if not en_queries:
            en_queries = [title]
    except Exception as exc:  # noqa: BLE001
        logger.warning("参考文献关键词提取失败，使用标题兜底: %s", exc)
        zh_query = title
        en_queries = [title]

    search_tasks = [_search_scholar(zh_query, num=15)] + [
        _search_scholar(query, num=12) for query in en_queries
    ]
    grouped_results = await asyncio.gather(*search_tasks)

    zh_results = grouped_results[0]
    en_results: list[dict] = []
    for group in grouped_results[1:]:
        en_results.extend(group)

    seen_titles: set[str] = set()

    def _dedup(items: list[dict]) -> list[dict]:
        deduped: list[dict] = []
        for item in items:
            title_key = item.get("title", "").strip().lower()
            if not title_key or title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            deduped.append(item)
        return deduped

    zh_results = _dedup(zh_results)
    en_results = _dedup(en_results)

    if not zh_results and not en_results:
        logger.warning("参考文献搜索结果为空，跳过生成")
        return ""

    zh_filtered, en_filtered = await asyncio.gather(
        _filter_results(llm, title, zh_results, "中文", fallback_num=11),
        _filter_results(llm, title, en_results, "英文", fallback_num=6),
    )

    lines: list[str] = []
    idx = 1
    for item in zh_filtered[:11]:
        line = _format_one_reference(item, idx, is_zh=True)
        if line:
            lines.append(line)
            idx += 1
    for item in en_filtered[:6]:
        line = _format_one_reference(item, idx, is_zh=False)
        if line:
            lines.append(line)
            idx += 1

    return "\n".join(lines)
