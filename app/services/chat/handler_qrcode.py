"""11002 二维码变化事件处理。

当实例二维码发生变化时（例如新生成、已扫码等），
由 dispatcher 调用此 handler 进行处理。
"""

import logging
from typing import Any

from app.schemas.wework import QrCodeChangeData

logger = logging.getLogger(__name__)


async def handle_qrcode_change(guid: str, data: dict[str, Any]) -> str:
    """
    处理二维码变化回调。

    Args:
        guid: 实例唯一标识。
        data: 事件数据体，包含 status、vid、nickname 等字段。

    Returns:
        处理结果描述。
    """

    # 将原始 dict 解析为强类型模型，方便后续取值
    qr_data = QrCodeChangeData.model_validate(data)

    logger.info(
        "[二维码变化] guid=%s, status=%s, vid=%s, nickname=%s",
        guid,
        qr_data.status,
        qr_data.vid,
        qr_data.nickname,
    )

    # ----------------------------------------------------------
    # TODO: 在此处添加业务逻辑，例如：
    #   - 将二维码推送到前端 WebSocket 让用户扫码
    #   - 更新数据库中实例状态
    # ----------------------------------------------------------

    return f"二维码变化已处理, status={qr_data.status}"
