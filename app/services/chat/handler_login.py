"""11003 登录 / 11004 退出登录 事件处理。

两个事件逻辑关联紧密（登录 ↔ 登出），放在同一模块统一管理。
"""

import logging
from typing import Any

from app.schemas.wework import LoginData, LogoutData

logger = logging.getLogger(__name__)


async def handle_login(guid: str, data: dict[str, Any]) -> str:
    """
    处理登录回调 (11003)。

    Args:
        guid: 实例唯一标识。
        data: 事件数据体，包含 user_id、name、corp_id 等字段。

    Returns:
        处理结果描述。
    """

    login_data = LoginData.model_validate(data)

    logger.info(
        "[登录] guid=%s, user_id=%s, name=%s, corp=%s",
        guid,
        login_data.user_id,
        login_data.name,
        login_data.corp_full_name,
    )

    # ----------------------------------------------------------
    # TODO: 在此处添加业务逻辑，例如：
    #   - 记录登录状态到数据库
    #   - 通知前端登录成功
    #   - 初始化用户会话
    # ----------------------------------------------------------

    return f"登录已处理, user_id={login_data.user_id}"


async def handle_logout(guid: str, data: dict[str, Any]) -> str:
    """
    处理退出登录回调 (11004)。

    Args:
        guid: 实例唯一标识。
        data: 事件数据体，包含 error_code、error_message 字段。

    Returns:
        处理结果描述。
    """

    logout_data = LogoutData.model_validate(data)

    logger.info(
        "[退出登录] guid=%s, error_code=%s, error_message=%s",
        guid,
        logout_data.error_code,
        logout_data.error_message,
    )

    # ----------------------------------------------------------
    # TODO: 在此处添加业务逻辑，例如：
    #   - 清除用户会话
    #   - 更新数据库中实例在线状态
    #   - 通知前端用户已登出
    # ----------------------------------------------------------

    return f"退出登录已处理, error_code={logout_data.error_code}"
