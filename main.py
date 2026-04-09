import uvicorn

from app.config import get_settings


def main() -> None:
    """本地启动入口：根据配置运行 uvicorn。"""

    settings = get_settings()
    uvicorn.run(
        # 指向 FastAPI 应用对象路径：app.main:app
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        # debug 模式下启用热重载，便于开发调试。
        reload=settings.app_debug,
    )


if __name__ == "__main__":
    main()
