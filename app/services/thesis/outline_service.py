from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser

from app.config import get_settings
from app.llm.client import create_llm
from app.llm.prompts.thesis_outline_prompt import THESIS_OUTLINE_PROMPT


@lru_cache
def _build_outline_chain():
    settings = get_settings()
    llm = create_llm(
        model=settings.thesis_outline_model,
        temperature=0.4,
        max_tokens=2048,
    )
    return THESIS_OUTLINE_PROMPT | llm | StrOutputParser()


async def generate_outline(title: str, target_word_count: int = 8000) -> str:
    """阶段①：根据论文标题生成结构化大纲。"""

    chain = _build_outline_chain()
    result = await chain.ainvoke({
        "title": title,
        "target_word_count": target_word_count
    })
    return result.strip()
