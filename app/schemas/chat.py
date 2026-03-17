from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """聊天接口请求体。"""

    # 用户唯一标识：用于隔离不同用户的会话上下文。
    user_id: str = Field(..., min_length=1, description="用户唯一标识")
    # 本轮用户输入内容。
    message: str = Field(..., min_length=1, description="用户本轮消息")


class ChatResponse(BaseModel):
    """聊天接口响应体。"""

    # 用户唯一标识，便于前后端对齐会话。
    user_id: str = Field(..., description="用户唯一标识")
    # 模型回复内容。
    reply: str = Field(..., description="模型回复")
    # 当前会话累计消息条数（含人类消息与模型消息）。
    history_size: int = Field(..., ge=0, description="当前会话消息总条数")


class ChatResetRequest(BaseModel):
    """重置会话接口请求体。"""

    # 用户唯一标识：用于定位要清空的会话。
    user_id: str = Field(..., min_length=1, description="用户唯一标识")


class ChatResetResponse(BaseModel):
    """重置会话接口响应体。"""

    # 用户唯一标识。
    user_id: str = Field(..., description="用户唯一标识")
    # 清空前的会话消息条数。
    previous_history_size: int = Field(..., ge=0, description="清空前消息总条数")
    # 清空后的会话消息条数，正常应为 0。
    current_history_size: int = Field(..., ge=0, description="清空后消息总条数")
