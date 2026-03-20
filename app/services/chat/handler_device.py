"""11011 其他设备登录事件处理。

当检测到同一账号在其他设备登录时触发此事件。
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def handle_other_device_login(guid: str, data: dict[str, Any]) -> str:
    """
    处理其他设备登录回调 (11011)。

    Args:
        guid: 实例唯一标识。
        data: 事件数据体（通常为空对象 {}）。

    Returns:
        处理结果描述。
    """

    logger.warning(
        "[其他设备登录] guid=%s, data=%s",
        guid,
        data,
    )

    # ----------------------------------------------------------
    # TODO: 在此处添加业务逻辑，例如：
    #   - 发出安全告警
    #   - 标记当前实例为 "已被挤下线"
    #   - 通知管理员
    # ----------------------------------------------------------

    return "其他设备登录已处理"
