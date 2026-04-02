from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# 聊天提示词模板：
# - system：统一约束助手行为
# - history：由 RunnableWithMessageHistory 自动注入历史消息
# - human：当前轮用户输入
CHAT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "你是一个专业、简洁、友好的 AI 助手。"
                "请基于历史上下文回答用户当前问题。"
                "如果用户信息不足，请明确提出需要补充的信息。"
            ),
        ),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ]
)
