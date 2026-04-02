"""企微机器人 Java 后端接口调用客户端。

封装对 Java 后端的 HTTP 请求，包括：
- 激活用户 (POST /api/wework/bot/user/activate)
- 发纯文字帖子 (POST /api/wework/bot/thread/publish-text)

所有接口需携带 X-Internal-Secret 鉴权头。
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ============================================================
# Java 后端配置
# ============================================================

# Java 后端服务基础地址（根据实际部署情况调整）
# JAVA_API_BASE_URL = "http://192.168.5.160:10458"
JAVA_API_BASE_URL = "https://social.aibzy.com"

# 内部鉴权密钥
INTERNAL_SECRET = "yJrHvxyPFb5ixfJgQtfCXE1qSPmOm77DwThnj7g"

# 请求超时（秒）—— 发帖接口涉及审核 + 短链生成，建议 ≥ 15 秒
REQUEST_TIMEOUT = 20.0

# 公共请求头
_HEADERS = {
    "Content-Type": "application/json",
    "X-Internal-Secret": INTERNAL_SECRET,
}


async def activate_user(uin: str, phone: str, unique_id: str) -> dict[str, Any]:
    """
    激活用户：将微信 uin 与小程序用户绑定。

    Args:
        uin: 微信 uin（必须以 788 开头）。
        phone: 11 位大陆手机号。
        unique_id: 小程序用户唯一标识。

    Returns:
        Java 后端返回的完整响应 JSON（包含 code、message、data）。
    """

    url = f"{JAVA_API_BASE_URL}/api/wework/bot/user/activate"
    payload = {
        "uin": uin,
        "phone": phone,
        "uniqueId": unique_id,
    }

    logger.info(
        "\n"
        "╔══════════════════════════════════════════════════════════\n"
        "║ 🔗 调用 Java 后端：激活用户\n"
        "╠══════════════════════════════════════════════════════════\n"
        "║  URL          : %s\n"
        "║  uin          : %s\n"
        "║  phone        : %s\n"
        "║  uniqueId     : %s\n"
        "╚══════════════════════════════════════════════════════════\n",
        url, uin, phone, unique_id,
    )

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.post(url, json=payload, headers=_HEADERS)
        result = response.json()

    logger.info(
        "\n"
        "╔══════════════════════════════════════════════════════════\n"
        "║ 📋 激活用户响应\n"
        "╠══════════════════════════════════════════════════════════\n"
        "║  HTTP Status  : %s\n"
        "║  code         : %s\n"
        "║  message      : %s\n"
        "║  data         : %s\n"
        "╚══════════════════════════════════════════════════════════\n",
        response.status_code,
        result.get("code"),
        result.get("message"),
        result.get("data"),
    )

    return result


async def publish_text_post(uin: str, content: str) -> dict[str, Any]:
    """
    发纯文字帖子。

    Args:
        uin: 微信 uin（需先调激活接口绑定）。
        content: 帖子文本内容（最多 2000 字）。

    Returns:
        Java 后端返回的完整响应 JSON（包含 code、message、data）。
    """

    url = f"{JAVA_API_BASE_URL}/api/wework/bot/thread/publish-text"
    payload = {
        "uin": uin,
        "content": content,
    }

    logger.info(
        "\n"
        "╔══════════════════════════════════════════════════════════\n"
        "║ 🔗 调用 Java 后端：发纯文字帖子\n"
        "╠══════════════════════════════════════════════════════════\n"
        "║  URL          : %s\n"
        "║  uin          : %s\n"
        "║  content      : %s\n"
        "╚══════════════════════════════════════════════════════════\n",
        url, uin, content[:100],
    )

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.post(url, json=payload, headers=_HEADERS)
        result = response.json()

    logger.info(
        "\n"
        "╔══════════════════════════════════════════════════════════\n"
        "║ 📋 发帖响应\n"
        "╠══════════════════════════════════════════════════════════\n"
        "║  HTTP Status  : %s\n"
        "║  code         : %s\n"
        "║  message      : %s\n"
        "║  data         : %s\n"
        "╚══════════════════════════════════════════════════════════\n",
        response.status_code,
        result.get("code"),
        result.get("message"),
        result.get("data"),
    )

    return result


async def trigger_meaningless_event(uin: str) -> dict[str, Any]:
    """
    无意义事件通知接口。

    当用户发送的消息无法匹配任何已知事件时调用。
    后端收到请求后，会向用户发送使用教程，引导用户发送数字编号触发对应功能。

    示例教程内容（由后端控制）：
        发送"1"拉你进校园圈群
        发送"2"进入本校社区
        发送"3"人工客服
        ……

    Args:
        uin: 微信 uin（消息发送者标识）。

    Returns:
        Java 后端返回的完整响应 JSON（包含 code、message、data）。

    TODO: 接口路径待后端确认，当前为占位 URL，上线前需替换。
    """

    # TODO: 替换为实际的后端接口路径
    url = f"{JAVA_API_BASE_URL}/api/wework/bot/event/meaningless"
    payload = {
        "uin": uin,
    }

    logger.info(
        "\n"
        "╔══════════════════════════════════════════════════════════\n"
        "║ 🔗 调用 Java 后端：无意义事件通知\n"
        "╠══════════════════════════════════════════════════════════\n"
        "║  URL          : %s\n"
        "║  uin          : %s\n"
        "╚══════════════════════════════════════════════════════════\n",
        url, uin,
    )

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.post(url, json=payload, headers=_HEADERS)
        result = response.json()

    logger.info(
        "\n"
        "╔══════════════════════════════════════════════════════════\n"
        "║ 📋 无意义事件响应\n"
        "╠══════════════════════════════════════════════════════════\n"
        "║  HTTP Status  : %s\n"
        "║  code         : %s\n"
        "║  message      : %s\n"
        "║  data         : %s\n"
        "╚══════════════════════════════════════════════════════════\n",
        response.status_code,
        result.get("code"),
        result.get("message"),
        result.get("data"),
    )

    return result


async def trigger_number_action(uin: str, number: str) -> dict[str, Any]:
    """
    数字菜单事件接口。

    用户发送单独数字（如 "1"、"2"、"3"）时调用，将数字传给后端，
    由后端根据数字执行对应操作（进群、进入社区、发送客服二维码等）。

    Args:
        uin: 微信 uin（消息发送者标识）。
        number: 用户发送的数字字符串（如 "1"、"2"、"3"）。

    Returns:
        Java 后端返回的完整响应 JSON（包含 code、message、data）。

    TODO: 接口路径待后端确认，当前为占位 URL，上线前需替换。
    """

    # TODO: 替换为实际的后端接口路径
    url = f"{JAVA_API_BASE_URL}/api/wework/bot/event/number-action"
    payload = {
        "uin": uin,
        "number": number,
    }

    logger.info(
        "\n"
        "╔══════════════════════════════════════════════════════════\n"
        "║ 🔗 调用 Java 后端：数字菜单事件\n"
        "╠══════════════════════════════════════════════════════════\n"
        "║  URL          : %s\n"
        "║  uin          : %s\n"
        "║  number       : %s\n"
        "╚══════════════════════════════════════════════════════════\n",
        url, uin, number,
    )

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.post(url, json=payload, headers=_HEADERS)
        result = response.json()

    logger.info(
        "\n"
        "╔══════════════════════════════════════════════════════════\n"
        "║ 📋 数字菜单事件响应\n"
        "╠══════════════════════════════════════════════════════════\n"
        "║  HTTP Status  : %s\n"
        "║  code         : %s\n"
        "║  message      : %s\n"
        "║  data         : %s\n"
        "╚══════════════════════════════════════════════════════════\n",
        response.status_code,
        result.get("code"),
        result.get("message"),
        result.get("data"),
    )

    return result
