from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory

from app.llm.client import get_llm
from app.llm.prompts.chat_prompt import CHAT_PROMPT
from app.services.chat_memory import (
    clear_user_chat_history,
    get_user_chat_history,
    get_user_history_size,
)


@lru_cache
def _get_chat_chain() -> RunnableWithMessageHistory:
    """构建并缓存聊天链（带会话历史能力）。"""

    # 基础链：提示词 -> 模型 -> 字符串解析。
    base_chain = CHAT_PROMPT | get_llm() | StrOutputParser()

    # 用 RunnableWithMessageHistory 包装后，链会自动读写历史消息。
    return RunnableWithMessageHistory(
        base_chain,
        get_session_history=get_user_chat_history,
        input_messages_key="input",
        history_messages_key="history",
    )


async def chat_with_user_memory(user_id: str, message: str) -> tuple[str, int]:
    """按 user_id 进行聊天，并返回回复与当前历史条数。"""

    chain = _get_chat_chain()
    # 通过 configurable.session_id 传递 user_id，作为历史隔离键。
    reply = await chain.ainvoke(
        {"input": message},
        config={"configurable": {"session_id": user_id}},
    )
    clean_reply = reply.strip()
    history_size = get_user_history_size(user_id)
    return clean_reply, history_size


def reset_user_memory(user_id: str) -> tuple[int, int]:
    """清空指定用户会话，并返回清空前后消息条数。"""

    previous_history_size = get_user_history_size(user_id)
    clear_user_chat_history(user_id)
    current_history_size = get_user_history_size(user_id)
    return previous_history_size, current_history_size
