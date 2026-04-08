from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser

from app.config import get_settings
from app.llm.client import create_llm
from app.llm.prompts.thesis_fulltext_prompt import THESIS_FULLTEXT_PROMPT


@lru_cache
def _build_fulltext_chain():
    settings = get_settings()
    llm = create_llm(
        model=settings.thesis_fulltext_model,
        # deepseek-reasoner 不支持 temperature；create_llm 内部会自动过滤。
        max_tokens=32768,
    )
    return THESIS_FULLTEXT_PROMPT | llm | StrOutputParser()


async def generate_fulltext(outline: str, target_word_count: int = 8000) -> str:
    """阶段②：根据大纲生成论文正文（含图片占位符）。"""

    chain = _build_fulltext_chain()
    result = await chain.ainvoke(
        {
            "outline": outline,
            "target_word_count": target_word_count,
            "target_word_count_max": target_word_count + 1000,
        }
    )
    return result.strip()
