"""设置回调通知地址接口。

调用企微协议 SAAS 的 /client/set_notify_url 端点,
将回调地址指向本服务的 /api/wework/callback 路由。

本接口为 GET 请求，触发即自动完成设置，无需传参。
"""

import logging

import httpx
from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.schemas.wework import SetNotifyUrlResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================
# 企微协议 SAAS 配置（固定参数）
# ============================================================

# 企微协议 SAAS 服务基础地址
WEWORK_API_BASE_URL = "https://chat-api.juhebot.com/open/GuidRequest"

# 认证凭证
APP_KEY = "appjCgGB7XrJ6PleZZN"
APP_SECRET = "3SLmJmA6lBlKAvCabCbWtHUouUZgG4ERUARtCIxSxvhENu2DsjCknHpniwdV1Fow"

# 实例唯一标识（固定值）
INSTANCE_GUID = "0f38aeb3-db40-3887-8dfa-24e716547e98"


@router.get(
    "/set_notify_url",
    response_model=SetNotifyUrlResponse,
    summary="设置实例回调通知地址",
    description="一键触发：调用企微协议 SAAS 接口，将回调通知地址设置为本服务的回调端点。无需传参。",
)
async def set_notify_url() -> SetNotifyUrlResponse:
    """
    设置实例的回调通知地址（GET 触发即执行）。

    1. 使用预配置的 app_key / app_secret / guid；
    2. 向企微协议 SAAS 发送 POST /client/set_notify_url；
    3. 返回操作结果。
    """

    # 从配置中读取回调通知地址
    notify_url = get_settings().notify_callback_url

    logger.info(
        "设置回调地址: guid=%s, notify_url=%s",
        INSTANCE_GUID,
        notify_url,
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{WEWORK_API_BASE_URL}",
                json={
                    "app_key": APP_KEY,
                    "app_secret": APP_SECRET,
                    "path": "/client/set_notify_url",
                    "data": {
                        "guid": INSTANCE_GUID,
                        "notify_url": notify_url,
                    },
                },
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "设置回调地址失败 (HTTP %s): %s",
            exc.response.status_code,
            exc.response.text,
        )
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"企微接口返回错误: {exc.response.text}",
        ) from exc
    except httpx.RequestError as exc:
        logger.error("设置回调地址请求异常: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=f"无法连接企微服务: {exc}",
        ) from exc

    logger.info("回调地址设置成功: guid=%s", INSTANCE_GUID)
    return SetNotifyUrlResponse(success=True, message="回调地址设置成功")
