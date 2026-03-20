import logging

from fastapi import FastAPI

from app.api.v1 import api_router
from app.api.chat.set_notify import router as set_notify_router
from app.api.chat.callback import router as callback_router
from app.config import get_settings

# 配置日志级别为 INFO，确保 logger.info() 能正常输出。
# 默认级别为 WARNING，会导致 INFO 级别日志被静默丢弃。
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# 读取配置单例，用于控制应用启动参数（如 debug）。
settings = get_settings()

# 创建 FastAPI 应用实例。
app = FastAPI(
    title="LLM Middleware Service",
    version="0.1.0",
    debug=settings.app_debug,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """健康检查接口，用于探活和监控。"""

    return {"status": "ok", "service": "llm-middleware"}


# 挂载 v1 路由，最终路径前缀为 /api/v1。
app.include_router(api_router, prefix="/api/v1")

# ============================================================
# 企微回调相关路由，前缀为 /api/wework
# ============================================================
# 设置回调地址：POST /api/wework/set_notify_url
app.include_router(set_notify_router, prefix="/api/wework", tags=["企微回调"])
# 接收回调通知：POST /api/wework/callback
app.include_router(callback_router, prefix="/api/wework", tags=["企微回调"])
