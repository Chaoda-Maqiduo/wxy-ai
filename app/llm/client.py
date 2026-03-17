from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config import get_settings


@lru_cache
def get_llm() -> ChatOpenAI:
    """初始化并返回可复用的 LLM 客户端单例。"""

    # 读取全局配置（已通过缓存保证只初始化一次）。
    settings = get_settings()
    # 未配置密钥时尽早失败，避免在链路深处报错难以定位。
    if not settings.deepseek_api_key:
        raise ValueError("DEEPSEEK_API_KEY is not configured")

    # DeepSeek 兼容 OpenAI 协议，因此直接使用 ChatOpenAI 客户端。
    return ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        # 提取任务倾向稳定输出，温度设为 0。
        temperature=0,
    )
