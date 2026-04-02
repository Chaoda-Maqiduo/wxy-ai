"""11010 新消息事件处理。

这是最核心的回调事件——接收到企微新消息后，
可在此接入 AI 对话、自动回复等业务逻辑。
"""

import base64
import json
import logging
import re
from typing import Any

from app.schemas.wework import NewMessageData
from app.services.chat.wework_api_client import (
    activate_user,
    publish_text_post,
    trigger_meaningless_event,
    trigger_number_action,
)
from app.services.extract_service import extract_core_content

logger = logging.getLogger(__name__)

# ============================================================
# 发帖需求匹配关键词列表
# 覆盖用户常见的发帖意图表达方式
# ============================================================
_POST_KEYWORDS = [
    # 直接表达
    "投稿",
    "发帖",
    "发个帖子",
    "发一个帖子",
    "发条帖子",
    "发布",
    "帮我发布",
    "帮发布",
    "请帮我发布",
    # 委托表达
    "帮发",
    "帮我发",
    "帮忙发",
    "帮忙发一下",
    "帮转发",
    "代发",
    "代我发",
    "代替我发",
    "给我发",
    "替我发",
    "麻烦发一下",
    # 口语化表达
    "发一下",
    "发下",
    "帮我发下",
    "帮我投稿",
    "我要发帖",
    "我想发帖",
    "我要投稿",
    "我想投稿",
    "请帮忙发",
    "请帮我发",
    "请代发",
    # 简短指令
    "发这个",
    "发出去",
    "帮我发出去",
]


async def handle_new_message(guid: str, data: dict[str, Any]) -> str:
    """
    处理新消息回调 (11010)。

    流程：
        1. 解析消息数据并打印日志；
        2. 调用 analyze_message 分析消息意图；
        3. 根据分析结果执行对应操作（激活 / 发帖）。

    Args:
        guid: 实例唯一标识。
        data: 事件数据体，包含 sender、receiver、content 等字段。

    Returns:
        处理结果描述。
    """

    msg_data = NewMessageData.model_validate(data)

    # 区分单聊 / 群聊
    is_group = msg_data.roomid and msg_data.roomid != "0"
    chat_type = "群聊" if is_group else "单聊"

    logger.info(
        "\n"
        "╔══════════════════════════════════════════════════════════\n"
        "║ 📨 新消息回调\n"
        "╠══════════════════════════════════════════════════════════\n"
        "║  GUID        : %s\n"
        "║  聊天类型     : %s\n"
        "║  发送者       : %s (%s)\n"
        "║  接收者       : %s\n"
        "║  群聊 ID      : %s\n"
        "║  消息 ID      : %s\n"
        "║  消息序列号   : %s\n"
        "║  内容类型     : %s\n"
        "║  消息类型     : %s\n"
        "║  发送时间     : %s\n"
        "║  发送标志     : %s\n"
        "║  消息标志位   : %s\n"
        "║  @列表        : %s\n"
        "║  引用内容     : %s\n"
        "║  消息正文     : %s\n"
        "╚══════════════════════════════════════════════════════════\n",
        guid,
        chat_type,
        msg_data.sender,
        msg_data.sender_name,
        msg_data.receiver,
        msg_data.roomid,
        msg_data.id,
        msg_data.seq,
        msg_data.content_type,
        msg_data.msg_type,
        msg_data.sendtime,
        msg_data.send_flag,
        msg_data.flag,
        msg_data.at_list,
        msg_data.quote_content or "无",
        msg_data.content,
    )

    # ----------------------------------------------------------
    # 分析消息意图并执行对应操作
    # ----------------------------------------------------------
    analyze_info = await analyze_message(msg_data.content)

    # 使用消息发送者 ID 作为 uin（企微协议中 sender 即用户标识）
    sender_uin = msg_data.sender

    if analyze_info is None:
        # 无法识别任何事件时，降级为无意义事件
        analyze_info = {
            "event_type": "meaningless",
            "raw_message": msg_data.content,
        }

    action_result = await _execute_action(sender_uin, analyze_info)
    return action_result


async def _execute_action(sender_uin: str, analyze_info: dict[str, Any]) -> str:
    """
    根据消息分析结果执行对应的业务操作。

    Args:
        sender_uin: 消息发送者 uin（用于调用 Java 后端接口）。
        analyze_info: analyze_message 返回的事件信息字典。

    Returns:
        操作结果描述。
    """

    event_type = analyze_info.get("event_type")

    # ----------------------------------------------------------
    # 激活事件：解析 base64 中的 u(uin) 和 p(phone)，调用激活接口
    # ----------------------------------------------------------
    if event_type == "activate":
        payload = analyze_info.get("payload", {})
        # base64 解码后的 JSON 格式：{"u": "29721224", "p": "18888888888"}
        phone = payload.get("p", "")
        unique_id = payload.get("u", "")

        if not unique_id or not phone:
            logger.warning(
                "激活事件缺少必要参数: unique_id=%s, phone=%s", unique_id, phone
            )
            return "激活失败: 缺少 unique_id 或 phone 参数"

        try:
            result = await activate_user(
                uin=sender_uin,
                phone=phone,
                unique_id=unique_id,
            )
            code = result.get("code")
            message = result.get("message", "")
            if code == 2000:
                return f"激活成功: uin={sender_uin}, message={message}"
            else:
                return f"激活失败: code={code}, message={message}"
        except Exception as exc:
            logger.error("调用激活接口异常: %s", exc)
            return f"激活异常: {exc}"

    # ----------------------------------------------------------
    # 发帖事件：使用 LLM 提取的内容调用发帖接口
    # ----------------------------------------------------------
    if event_type == "post":
        extracted_content = analyze_info.get("extracted_content")

        if not extracted_content:
            error_msg = analyze_info.get("error", "内容提取为空")
            logger.warning("发帖事件内容提取失败: %s", error_msg)
            return f"发帖失败: {error_msg}"

        try:
            result = await publish_text_post(
                uin=sender_uin,
                content=extracted_content,
            )
            code = result.get("code")
            message = result.get("message", "")
            data = result.get("data")

            if code == 2000:
                thread_id = data.get("threadId", "") if data else ""
                short_link = data.get("shortLink", "") if data else ""
                return (
                    f"发帖成功: threadId={thread_id}, "
                    f"shortLink={short_link}, message={message}"
                )
            elif code == 4101:
                return "发帖失败: 用户未绑定（请先发送激活指令）"
            elif code == 4104:
                return f"发帖失败: 内容审核未通过, message={message}"
            else:
                return f"发帖失败: code={code}, message={message}"
        except Exception as exc:
            logger.error("调用发帖接口异常: %s", exc)
            return f"发帖异常: {exc}"

    # ----------------------------------------------------------
    # 数字事件：用户发送单独数字（如 "1"、"2"、"3"），对应菜单选项
    # ----------------------------------------------------------
    if event_type == "number_action":
        number = analyze_info.get("number", "")

        try:
            result = await trigger_number_action(
                uin=sender_uin,
                number=number,
            )
            code = result.get("code")
            message = result.get("message", "")
            if code == 2000:
                return f"数字事件处理成功: number={number}, message={message}"
            else:
                return (
                    f"数字事件处理失败: number={number}, code={code}, message={message}"
                )
        except Exception as exc:
            logger.error("调用数字事件接口异常: %s", exc)
            return f"数字事件异常: {exc}"

    # ----------------------------------------------------------
    # 无意义事件：消息无法匹配任何已知事件，调用无意义事件接口
    # 后端会向用户发送使用教程（引导发送数字编号触发功能）
    # ----------------------------------------------------------
    if event_type == "meaningless":
        try:
            result = await trigger_meaningless_event(uin=sender_uin)
            code = result.get("code")
            message = result.get("message", "")
            if code == 2000:
                return f"无意义事件已通知后端: uin={sender_uin}, message={message}"
            else:
                return f"无意义事件接口响应异常: code={code}, message={message}"
        except Exception as exc:
            logger.error("调用无意义事件接口异常: %s", exc)
            return f"无意义事件异常: {exc}"

    # ----------------------------------------------------------
    # 未知事件类型（理论上不应到达这里）
    # ----------------------------------------------------------
    logger.warning("未处理的事件类型: %s", event_type)
    return f"未处理的事件类型: {event_type}"


async def analyze_message(msg: str) -> dict | None:
    """
    根据消息内容分析出需要进行的事件。

    Args:
        msg: 消息内容。

    Returns:
        匹配到的事件信息字典，未匹配到任何事件时返回 None。

    支持的事件：
        1. 激活事件 — 文本示例："激活码: eyJ1IjoiMjk3MjEyMjQiLCAicCI6IjE4ODg4ODg4ODg4In0="
           "激活" 关键词 + 冒号 + 一段 base64 编码
        2. 发帖事件 — 包含"投稿"、"帮发"、"发帖"等关键词，
           调用 LLM 提取用户真正想发布的内容
        3. 数字事件 — 用户单独发送一个数字（如 "1"、"2"），
           对应后端菜单选项，由后端执行对应操作
    """

    if msg is None:
        return None

    text = msg.strip()

    # ----------------------------------------------------------
    # 1. 匹配激活需求
    #    文本特征：激活: <base64> / 激活码：<base64> / 激活码 <base64>
    #    兼容中英文冒号、纯空格、多个空格等分隔方式
    # ----------------------------------------------------------
    activate_match = re.match(r"^激活码\s*[:：]?\s+(.+)$|^激活码[:：]\s*(.+)$", text)
    if activate_match:
        # 两个分支只有一个会匹配到，取非 None 的那个
        b64_str = (activate_match.group(1) or activate_match.group(2)).strip()
        try:
            # 解码 base64 → JSON 字符串 → dict
            decoded_bytes = base64.b64decode(b64_str)
            payload = json.loads(decoded_bytes.decode("utf-8"))
        except (base64.binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning("激活事件 base64 解码失败: raw=%s, error=%s", b64_str, exc)
            return None

        logger.info(
            "\n"
            "╔══════════════════════════════════════════════════════════\n"
            "║ 🔑 识别到激活事件\n"
            "╠══════════════════════════════════════════════════════════\n"
            "║  原始消息     : %s\n"
            "║  解码数据     : %s\n"
            "╚══════════════════════════════════════════════════════════\n",
            text,
            payload,
        )

        return {
            "event_type": "activate",
            "raw_message": text,
            "payload": payload,
        }

    # ----------------------------------------------------------
    # 2. 匹配发帖需求
    #    文本特征词：投稿、帮发、给我发、发帖、发个帖子 ...
    #    匹配逻辑：检查消息中是否包含任一关键词
    # ----------------------------------------------------------
    matched_keyword = None
    for keyword in _POST_KEYWORDS:
        if keyword in text:
            matched_keyword = keyword
            break

    if matched_keyword:
        logger.info(
            "\n"
            "╔══════════════════════════════════════════════════════════\n"
            "║ 📝 识别到发帖需求\n"
            "╠══════════════════════════════════════════════════════════\n"
            "║  匹配关键词   : %s\n"
            "║  原始消息     : %s\n"
            "║  正在调用 LLM 提取发布内容...\n"
            "╚══════════════════════════════════════════════════════════\n",
            matched_keyword,
            text,
        )

        try:
            # 调用 LLM 提取用户真正想发布的核心内容
            extracted_content = await extract_core_content(text)
        except Exception as exc:
            logger.error("LLM 提取发帖内容失败: %s", exc)
            return {
                "event_type": "post",
                "raw_message": text,
                "matched_keyword": matched_keyword,
                "extracted_content": None,
                "error": str(exc),
            }

        logger.info(
            "\n"
            "╔══════════════════════════════════════════════════════════\n"
            "║ ✅ 发帖内容提取完成\n"
            "╠══════════════════════════════════════════════════════════\n"
            "║  匹配关键词   : %s\n"
            "║  原始消息     : %s\n"
            "╠══════════════════════════════════════════════════════════\n"
            "║  提取结果:\n"
            "%s\n"
            "╚══════════════════════════════════════════════════════════\n",
            matched_keyword,
            text,
            extracted_content,
        )

        return {
            "event_type": "post",
            "raw_message": text,
            "matched_keyword": matched_keyword,
            "extracted_content": extracted_content,
        }

    # ----------------------------------------------------------
    # 3. 匹配数字事件
    #    文本特征：消息去除首尾空格后，整体为一个正整数（如 "1"、"2"、"10"）
    #    匹配逻辑：完整匹配，避免含有其他字符的消息误触发
    # ----------------------------------------------------------
    number_match = re.fullmatch(r"[1-9]\d*", text)
    if number_match:
        number_str = number_match.group()
        logger.info(
            "\n"
            "╔══════════════════════════════════════════════════════════\n"
            "║ 🔢 识别到数字事件\n"
            "╠══════════════════════════════════════════════════════════\n"
            "║  原始消息     : %s\n"
            "║  识别数字     : %s\n"
            "╚══════════════════════════════════════════════════════════\n",
            text,
            number_str,
        )
        return {
            "event_type": "number_action",
            "raw_message": text,
            "number": number_str,
        }

    # ----------------------------------------------------------
    # 未匹配到任何已知事件
    # ----------------------------------------------------------
    return None
