from functools import lru_cache

from langchain_core.language_models import BaseChatModel
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


def create_llm(
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> BaseChatModel:
    """创建通用 LLM 客户端，支持按场景覆盖模型参数。"""

    settings = get_settings()
    if not settings.deepseek_api_key:
        raise ValueError("DEEPSEEK_API_KEY is not configured")

    resolved_model = model or settings.deepseek_model
    
    if "claude" in resolved_model.lower():
        from langchain_anthropic import ChatAnthropic
        anthropic_kwargs = {
            "model_name": resolved_model,
            "anthropic_api_key": settings.twelveai_api_key,
            "anthropic_api_url": "https://cdn.12ai.org",
            "max_tokens": max_tokens if max_tokens is not None else 4096,
            "timeout": 3600,
        }
        if temperature is not None:
            anthropic_kwargs["temperature"] = temperature
        return ChatAnthropic(**anthropic_kwargs)
        
    # 动态路由：如果是 gemini 等通过 12AI 提供的模型，切换 provider
    if "gemini" in resolved_model.lower():
        api_key = settings.twelveai_api_key
        base_url = "https://api.12ai.org/v1"
    else:
        api_key = settings.deepseek_api_key
        base_url = settings.deepseek_base_url

    kwargs: dict[str, object] = {
        "model": resolved_model,
        "api_key": api_key,
        "base_url": base_url,
    }

    # deepseek-reasoner 不支持 temperature / top_p 等采样参数。
    if temperature is not None and "reasoner" not in resolved_model:
        kwargs["temperature"] = temperature
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    return ChatOpenAI(**kwargs)
