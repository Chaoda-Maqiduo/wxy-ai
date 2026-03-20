"""回调事件分发器。

根据 notify_type 将事件路由到对应的 handler 函数。
"""

import json
import logging
from typing import Any, Callable, Coroutine

from app.schemas.wework import WeworkCallbackPayload

from app.services.chat.handler_login import handle_login, handle_logout
from app.services.chat.handler_message import handle_new_message
from app.services.chat.handler_qrcode import handle_qrcode_change
from app.services.chat.handler_device import handle_other_device_login
from app.services.chat.handler_call import handle_voice_video_call

logger = logging.getLogger(__name__)

# ============================================================
# 事件类型 -> 处理函数 映射表
# ============================================================

# 类型别名：每个 handler 接受 (guid, data_dict)，返回处理结果描述
HandlerFunc = Callable[[str, dict[str, Any]], Coroutine[Any, Any, str]]

_HANDLER_MAP: dict[int, HandlerFunc] = {
    11002: handle_qrcode_change,       # 二维码变化
    11003: handle_login,               # 登录
    11004: handle_logout,              # 退出登录
    11010: handle_new_message,         # 新消息
    11011: handle_other_device_login,  # 其他设备登录
    2166:  handle_voice_video_call,    # 视频/语音电话
}


async def dispatch_callback(payload: WeworkCallbackPayload) -> str:
    """
    根据回调事件类型分发到对应 handler。

    Args:
        payload: 已解析的企微回调请求体。

    Returns:
        handler 执行后返回的结果描述字符串。
    """

    notify_type = payload.notify_type
    handler = _HANDLER_MAP.get(notify_type)

    if handler is None:
        data_pretty = json.dumps(payload.data, ensure_ascii=False, indent=4)
        logger.warning(
            "\n"
            "╔══════════════════════════════════════════════════════════\n"
            "║ ⚠️  未注册的回调事件类型\n"
            "╠══════════════════════════════════════════════════════════\n"
            "║  GUID         : %s\n"
            "║  notify_type   : %s\n"
            "╠══════════════════════════════════════════════════════════\n"
            "║  完整 data 数据:\n"
            "%s\n"
            "╚══════════════════════════════════════════════════════════\n",
            payload.guid,
            notify_type,
            data_pretty,
        )
        return f"未知事件类型: {notify_type}"

    logger.info(
        "分发回调事件: notify_type=%s, guid=%s",
        notify_type,
        payload.guid,
    )

    try:
        result = await handler(payload.guid, payload.data)
        logger.info(
            "事件处理完成: notify_type=%s, guid=%s, result=%s",
            notify_type,
            payload.guid,
            result,
        )
        return result
    except Exception:
        logger.exception(
            "事件处理异常: notify_type=%s, guid=%s",
            notify_type,
            payload.guid,
        )
        raise
