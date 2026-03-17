from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser

from app.llm.client import get_llm
from app.llm.prompts.extract_prompt import EXTRACT_PROMPT


@lru_cache
def _get_extract_chain():
    """构建提取链并缓存，避免每次请求重复组装对象。"""

    # LCEL 链路：提示词 -> 模型 -> 字符串解析。
    return EXTRACT_PROMPT | get_llm() | StrOutputParser()


async def extract_core_content(text: str) -> str:
    """调用 LLM 提取文本核心内容。"""

    chain = _get_extract_chain()
    # 使用异步调用，避免阻塞 FastAPI 事件循环。
    result = await chain.ainvoke({"text": text})
    # 去除首尾空白，统一返回格式。
    return result.strip()
