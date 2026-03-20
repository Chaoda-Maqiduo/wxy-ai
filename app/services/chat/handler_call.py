"""2166 视频/语音电话事件处理。

当收到视频或语音通话邀请时触发此事件。
"""

import logging
from typing import Any

from app.schemas.wework import VoiceVideoCallData

logger = logging.getLogger(__name__)


async def handle_voice_video_call(guid: str, data: dict[str, Any]) -> str:
    """
    处理视频/语音电话回调 (2166)。

    Args:
        guid: 实例唯一标识。
        data: 事件数据体，包含 type、msgid、inviteMsg 等字段。

    Returns:
        处理结果描述。
    """

    call_data = VoiceVideoCallData.model_validate(data)

    logger.info(
        "[视频/语音电话] guid=%s, type=%s, msgid=%s, timestamp=%s",
        guid,
        call_data.type,
        call_data.msgid,
        call_data.timestamp,
    )

    # 解析邀请详情
    if call_data.inviteMsg:
        invite = call_data.inviteMsg
        member_count = len(invite.memlist) if invite.memlist else 0
        logger.info(
            "[视频/语音电话] 邀请详情: roomid=%s, inviteId=%s, members=%d",
            invite.roomid,
            invite.inviteId,
            member_count,
        )

    # ----------------------------------------------------------
    # TODO: 在此处添加业务逻辑，例如：
    #   - 记录来电信息
    #   - 自动拒接 / 通知管理员
    # ----------------------------------------------------------

    return f"视频/语音电话已处理, type={call_data.type}"
