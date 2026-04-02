"""企微协议回调相关的请求 / 响应数据模型。"""

from typing import Any, Optional

from pydantic import BaseModel, Field

# ============================================================
# 设置回调地址 - 请求 / 响应
# ============================================================


class SetNotifyUrlRequest(BaseModel):
    """设置实例通知地址的请求体。"""

    # 实例唯一标识
    guid: str = Field(..., min_length=1, description="实例唯一标识 (GUID)")
    # 回调通知地址 (本服务对外暴露的 URL)
    notify_url: str = Field(..., min_length=1, description="回调通知地址")


class SetNotifyUrlResponse(BaseModel):
    """设置回调地址的响应体（仅返回操作结果）。"""

    success: bool = Field(..., description="操作是否成功")
    message: str = Field(default="", description="提示信息")


# ============================================================
# 回调事件 - 通用结构
# ============================================================


class WeworkCallbackPayload(BaseModel):
    """
    企微协议 SAAS 回调通知的通用结构。

    所有回调事件共享此顶层格式：
    {
        "guid": "xxx",
        "notify_type": 11010,
        "data": { ... }
    }
    """

    # 实例唯一标识
    guid: str = Field(..., description="实例唯一标识")
    # 回调事件类型编号
    notify_type: int = Field(..., description="回调事件类型编号")
    # 事件数据体（不同类型结构不同，先用 dict 接收后分类解析）
    data: dict[str, Any] = Field(default_factory=dict, description="事件数据体")


class CallbackResponse(BaseModel):
    """回调接口统一响应格式。"""

    success: bool = Field(default=True, description="是否处理成功")
    message: str = Field(default="ok", description="处理结果描述")


# ============================================================
# 各回调事件的 data 子模型
# ============================================================


class QrCodeChangeData(BaseModel):
    """11002 二维码变化事件 data。"""

    status: int = Field(default=0, description="二维码状态")
    vid: Optional[int] = Field(default=None, description="VID")
    nickname: Optional[str] = Field(default=None, description="昵称")
    avatar: Optional[str] = Field(default=None, description="头像 URL")
    logo: Optional[str] = Field(default=None, description="Logo URL")
    corp_id: Optional[int] = Field(default=None, description="企业 ID")


class LoginData(BaseModel):
    """11003 登录事件 data。"""

    user_id: Optional[str] = Field(default=None, description="用户 ID")
    name: Optional[str] = Field(default=None, description="用户名")
    real_name: Optional[str] = Field(default=None, description="真实姓名")
    corp_id: Optional[str] = Field(default=None, description="企业 ID")
    gender: Optional[int] = Field(default=None, description="性别 (1=男, 2=女)")
    party_id: Optional[str] = Field(default=None, description="部门 ID")
    avatar: Optional[str] = Field(default=None, description="头像 URL")
    corp_short_name: Optional[str] = Field(default=None, description="企业简称")
    corp_full_name: Optional[str] = Field(default=None, description="企业全称")


class LogoutData(BaseModel):
    """11004 退出登录事件 data。"""

    error_code: Optional[int] = Field(default=None, description="错误码")
    error_message: Optional[str] = Field(default=None, description="错误信息")


class NewMessageData(BaseModel):
    """11010 新消息事件 data。"""

    seq: Optional[str] = Field(default=None, description="消息序列号")
    id: Optional[str] = Field(default=None, description="消息 ID")
    appinfo: Optional[str] = Field(default=None, description="应用信息")
    sender: Optional[str] = Field(default=None, description="发送者 ID")
    receiver: Optional[str] = Field(default=None, description="接收者 ID")
    roomid: Optional[str] = Field(default=None, description="群聊 ID (0 表示单聊)")
    sendtime: Optional[int] = Field(default=None, description="发送时间 (Unix 时间戳)")
    sender_name: Optional[str] = Field(default=None, description="发送者名称")
    content_type: Optional[int] = Field(default=None, description="消息内容类型")
    referid: Optional[str] = Field(default=None, description="引用 ID")
    flag: Optional[int] = Field(default=None, description="消息标志位")
    content: Optional[str] = Field(default=None, description="消息正文内容")
    at_list: Optional[list[str]] = Field(default=None, description="@列表")
    quote_content: Optional[str] = Field(default=None, description="引用内容")
    quote_appinfo: Optional[str] = Field(default=None, description="引用应用信息")
    send_flag: Optional[int] = Field(default=None, description="发送标志")
    msg_type: Optional[int] = Field(default=None, description="消息类型")


class OtherDeviceLoginData(BaseModel):
    """11011 其他设备登录事件 data (通常为空对象)。"""

    pass


class VoiceVideoCallMember(BaseModel):
    """2166 视频/语音电话 - 成员信息。"""

    xid: Optional[str] = Field(default=None, description="成员 XID")
    name: Optional[str] = Field(default=None, description="成员名称 (Base64)")
    headUrl: Optional[str] = Field(default=None, description="头像 URL (Base64)")
    openid: Optional[str] = Field(default=None, description="OpenID")


class VoiceVideoCallInviteMsg(BaseModel):
    """2166 视频/语音电话 - 邀请消息。"""

    roomid: Optional[str] = Field(default=None, description="房间 ID")
    roomkey: Optional[str] = Field(default=None, description="房间密钥")
    memlist: Optional[list[VoiceVideoCallMember]] = Field(
        default=None, description="成员列表"
    )
    inviteId: Optional[str] = Field(default=None, description="邀请者 ID")
    inviteType: Optional[int] = Field(default=None, description="邀请类型")
    actType: Optional[int] = Field(default=None, description="操作类型")
    sdkBuff: Optional[str] = Field(default=None, description="SDK Buffer")


class VoiceVideoCallData(BaseModel):
    """2166 视频/语音电话事件 data。"""

    type: Optional[int] = Field(default=None, description="通话类型")
    msgid: Optional[str] = Field(default=None, description="消息 ID")
    timestamp: Optional[int] = Field(default=None, description="时间戳")
    inviteMsg: Optional[VoiceVideoCallInviteMsg] = Field(
        default=None, description="邀请消息详情"
    )
