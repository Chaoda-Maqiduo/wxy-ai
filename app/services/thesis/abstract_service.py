import asyncio
import logging

from langchain_core.output_parsers import StrOutputParser

from app.config import get_settings
from app.llm.client import create_llm
from app.llm.prompts.thesis_abstract_prompt import (
    ABSTRACT_EN_PROMPT,
    ABSTRACT_ZH_PROMPT,
    ACKNOWLEDGMENT_PROMPT,
)

logger = logging.getLogger(__name__)


def _sample_text(full_text: str) -> str:
    """
    采样策略：前 3000 字 + 后 2000 字，避免结论段丢失。
    """
    head = full_text[:3000]
    tail = full_text[-2000:] if len(full_text) > 5000 else ""
    if tail:
        return head + "\n\n[...（中间内容省略）...]\n\n" + tail
    return head


def _parse_body_and_keywords(raw: str, kw_prefix: str) -> tuple[str, str]:
    """从模型输出中拆分正文与关键词。"""
    lines = raw.strip().splitlines()
    keywords = ""
    body_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(kw_prefix):
            keywords = stripped[len(kw_prefix):].strip()
        else:
            body_lines.append(line)
    return "\n".join(body_lines).strip(), keywords


async def generate_abstracts(full_text: str) -> dict[str, str]:
    """
    生成中英文摘要及关键词。
    """
    settings = get_settings()
    llm = create_llm(
        model=settings.thesis_outline_model,
        temperature=0.3,
        max_tokens=2048,
    )
    sample = _sample_text(full_text)

    chain_zh = ABSTRACT_ZH_PROMPT | llm | StrOutputParser()
    chain_en = ABSTRACT_EN_PROMPT | llm | StrOutputParser()

    raw_zh, raw_en = await asyncio.gather(
        chain_zh.ainvoke({"text_sample": sample}),
        chain_en.ainvoke({"text_sample": sample}),
    )

    abstract_zh, keywords_zh = _parse_body_and_keywords(raw_zh, "关键词：")
    abstract_en, keywords_en = _parse_body_and_keywords(raw_en, "Keywords:")

    logger.info("摘要生成完成: zh=%d字 en=%d字", len(abstract_zh), len(abstract_en))
    return {
        "abstract_zh": abstract_zh,
        "keywords_zh": keywords_zh,
        "abstract_en": abstract_en,
        "keywords_en": keywords_en,
    }


async def generate_acknowledgment(title: str, advisor: str) -> str:
    """生成致谢正文。"""
    settings = get_settings()
    llm = create_llm(
        model=settings.thesis_outline_model,
        temperature=0.7,
        max_tokens=1024,
    )
    chain = ACKNOWLEDGMENT_PROMPT | llm | StrOutputParser()
    result = await chain.ainvoke({"title": title, "advisor": advisor})
    return result.strip()
