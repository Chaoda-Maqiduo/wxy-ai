from functools import lru_cache
from os import getenv

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# 启动时加载项目根目录下的 .env 文件，便于本地开发读取配置。
load_dotenv()

# 统一维护需要从环境变量读取的键，避免散落硬编码。
_ENV_KEYS = (
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_MODEL",
    "APP_HOST",
    "APP_PORT",
    "APP_DEBUG",
    "REDIS_URL",
    "REDIS_KEY_PREFIX",
    "CHAT_HISTORY_TTL_SECONDS",
    "NOTIFY_CALLBACK_URL",
    "THESIS_OUTLINE_MODEL",
    "THESIS_FULLTEXT_MODEL",
    "TWELVEAI_API_KEY",
    "TWELVEAI_IMAGE_MODEL",
)


class Settings(BaseModel):
    """全局配置对象：集中管理模型与服务运行参数。"""

    # DeepSeek API 密钥，留空时在调用模型阶段抛错。
    deepseek_api_key: str = Field(default="", validation_alias="DEEPSEEK_API_KEY")
    # DeepSeek 兼容 OpenAI 接口的基础 URL。
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com", validation_alias="DEEPSEEK_BASE_URL"
    )
    # 默认模型名称，可通过环境变量覆盖。
    deepseek_model: str = Field(
        default="deepseek-chat", validation_alias="DEEPSEEK_MODEL"
    )
    # FastAPI 对外监听地址。
    app_host: str = Field(default="0.0.0.0", validation_alias="APP_HOST")
    # FastAPI 对外监听端口。
    app_port: int = Field(default=10461, validation_alias="APP_PORT")
    # 是否开启调试模式（例如本地热重载场景）。
    app_debug: bool = Field(default=False, validation_alias="APP_DEBUG")
    # Redis 连接地址，用于存储聊天上下文。
    redis_url: str = Field(
        default="redis://localhost:6379/0", validation_alias="REDIS_URL"
    )
    # Redis 中聊天历史 key 前缀。
    redis_key_prefix: str = Field(
        default="chat_history", validation_alias="REDIS_KEY_PREFIX"
    )
    # 聊天历史过期时间（秒），<=0 表示不过期。
    chat_history_ttl_seconds: int = Field(
        default=86400, validation_alias="CHAT_HISTORY_TTL_SECONDS"
    )
    # 企微回调通知地址（本服务对外暴露的回调端点）。
    notify_callback_url: str = Field(
        default="https://ai.aibzy.com/api/wework/callback",
        validation_alias="NOTIFY_CALLBACK_URL",
    )
    # 论文系统大纲阶段模型（默认偏快、低成本）。
    thesis_outline_model: str = Field(
        default="deepseek-chat", validation_alias="THESIS_OUTLINE_MODEL"
    )
    # 论文系统全文阶段模型（默认偏长文推理能力）。
    thesis_fulltext_model: str = Field(
        default="deepseek-reasoner", validation_alias="THESIS_FULLTEXT_MODEL"
    )

    # --- 备份：OpenRouter API 生图大模型接入（如果需要可放开并注释下面12AI即可） ---
    # openrouter_api_key: str = Field(
    #     default="", validation_alias="OPENROUTER_API_KEY"
    # )
    # openrouter_image_model: str = Field(
    #     default="google/gemini-3.1-flash-image-preview", validation_alias="OPENROUTER_IMAGE_MODEL"
    # )

    # 12AI 中转站生图配置 (Gemini)
    twelveai_api_key: str = Field(
        default="", validation_alias="TWELVEAI_API_KEY"
    )
    twelveai_image_model: str = Field(
        default="gemini-3-pro-image-preview", validation_alias="TWELVEAI_IMAGE_MODEL"
    )


@lru_cache
def get_settings() -> Settings:
    """获取全局配置单例，避免重复解析环境变量。"""

    # 仅收集有值的环境变量；未设置项走 Settings 中的默认值。
    env_values = {key: value for key in _ENV_KEYS if (value := getenv(key)) is not None}
    # 用 Pydantic 完成类型转换与校验，例如端口转 int、debug 转 bool。
    return Settings.model_validate(env_values)
