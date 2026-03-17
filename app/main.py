from fastapi import FastAPI

from app.api.v1 import api_router
from app.config import get_settings

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
