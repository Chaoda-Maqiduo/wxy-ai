"""企微回调接收接口。

企微协议 SAAS 在触发事件时，会向此端点 POST 回调数据。
本接口负责验证、解析并分发事件到对应的 handler。
"""

import logging

from fastapi import APIRouter

from app.schemas.wework import CallbackResponse, WeworkCallbackPayload
from app.services.chat.dispatcher import dispatch_callback

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/callback",
    response_model=CallbackResponse,
    summary="企微回调接收端点",
    description="接收企微协议 SAAS 推送的回调事件，根据 notify_type 分发到对应处理器。",
)
async def wework_callback(payload: WeworkCallbackPayload) -> CallbackResponse:
    """
    企微回调统一入口。

    1. 接收企微协议 SAAS 推送的 JSON 请求体；
    2. 解析 notify_type 确定事件类型；
    3. 调用 dispatcher 分发到对应的事件 handler；
    4. 返回统一格式的响应。
    """

    logger.info(
        "收到企微回调: notify_type=%s, guid=%s",
        payload.notify_type,
        payload.guid,
    )

    try:
        result = await dispatch_callback(payload)
        return CallbackResponse(success=True, message=result)
    except Exception as exc:
        logger.exception("回调处理异常: %s", exc)
        # 即使处理失败，也返回 200 以避免企微重复推送
        # 具体错误通过日志追踪
        return CallbackResponse(success=False, message=f"处理异常: {exc}")
