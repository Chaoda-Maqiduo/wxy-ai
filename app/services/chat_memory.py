import json
from functools import lru_cache
from os import getenv
from typing import Sequence

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict
from redis import Redis

from app.config import get_settings


def _history_key(user_id: str) -> str:
    """拼接 Redis 聊天历史 key。"""

    settings = get_settings()
    return f"{settings.redis_key_prefix}:{user_id}"


@lru_cache
def _get_redis_client() -> Redis:
    """创建并缓存 Redis 客户端单例。"""

    # Prefer REDIS_URL from environment/.env for easy runtime overrides.
    redis_url = getenv("REDIS_URL") or get_settings().redis_url
    return Redis.from_url(redis_url, decode_responses=True)


class RedisChatMessageHistory(BaseChatMessageHistory):
    """基于 Redis List 的聊天历史实现。"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.key = _history_key(user_id)
        self.client = _get_redis_client()

    @property
    def messages(self) -> list[BaseMessage]:
        """读取用户历史消息并反序列化为 BaseMessage 列表。"""

        message_str_list = self.client.lrange(self.key, 0, -1)
        if not message_str_list:
            return []
        message_dict_list = [json.loads(item) for item in message_str_list]
        return messages_from_dict(message_dict_list)

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        """批量写入消息到 Redis，并按配置刷新过期时间。"""

        if not messages:
            return

        payload = [
            json.dumps(message_to_dict(message), ensure_ascii=False)
            for message in messages
        ]
        ttl_seconds = get_settings().chat_history_ttl_seconds

        pipeline = self.client.pipeline()
        pipeline.rpush(self.key, *payload)
        if ttl_seconds > 0:
            pipeline.expire(self.key, ttl_seconds)
        pipeline.execute()

    def clear(self) -> None:
        """清空指定用户的聊天历史。"""

        self.client.delete(self.key)


def get_user_chat_history(user_id: str) -> BaseChatMessageHistory:
    """按 user_id 返回 Redis 版聊天历史对象。"""

    return RedisChatMessageHistory(user_id=user_id)


def get_user_history_size(user_id: str) -> int:
    """返回指定用户当前会话消息条数。"""

    return int(_get_redis_client().llen(_history_key(user_id)))


def clear_user_chat_history(user_id: str) -> int:
    """按 user_id 清空会话历史，返回删除的 key 数量。"""

    return int(_get_redis_client().delete(_history_key(user_id)))
