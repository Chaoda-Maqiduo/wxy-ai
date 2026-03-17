from langchain_core.prompts import ChatPromptTemplate

# 提取任务提示词模板：
# - system 约束模型行为
# - human 注入待处理文本变量 {text}
EXTRACT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "你是一个用户发帖助手。"
                "信息来自于用户和你的聊天对话，用户需要你帮他在社交论坛中发布帖子，请从输入的文本中提取出用户需要发布的内容"
                "不改动用户发给的内容，不添加任何多余的文字，完整的提取出用户想要发布的内容，不要遗漏语气词、标点符号、特殊符号"
                "特别提醒，用户的发帖内容可能在：: 换行\n 这些符号后面，前面是你好，投稿；请帮我发布；发布；投稿；帮发"
                "输出要简介、完整、结构化，且与输入文本保持同一语言"
            ),
        ),
        (
            "human",
            "请提取以下文本内用户需要发布的内容：\n\n{text}",
        ),
    ]
)
