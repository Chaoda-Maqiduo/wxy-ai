from langchain_core.prompts import ChatPromptTemplate

ABSTRACT_ZH_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "你是一位专业的学术论文助手。根据提供的论文内容片段，撰写规范的中文摘要。\n\n"
                "要求：\n"
                "1. 字数 300-500 字\n"
                "2. 涵盖：研究背景、研究目的、研究方法、主要结论\n"
                "3. 使用第三人称，不出现「本人」「我」\n"
                "4. 只输出摘要正文，不加「摘要」标题\n\n"
                "输出摘要正文后，另起一行输出关键词，格式严格为：\n"
                "关键词：词1；词2；词3；词4；词5"
            ),
        ),
        ("human", "{text_sample}"),
    ]
)

ABSTRACT_EN_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a professional academic writing assistant. "
                "Based on the provided thesis excerpts, write an English Abstract.\n\n"
                "Requirements:\n"
                "1. 200-300 words\n"
                "2. Cover: background, objective, methods, main conclusions\n"
                "3. Third person, past tense for methods\n"
                "4. Output abstract body only, no 'Abstract' heading\n\n"
                "After the abstract body, on a new line, output keywords in this exact format:\n"
                "Keywords: word1; word2; word3; word4; word5"
            ),
        ),
        ("human", "{text_sample}"),
    ]
)

ACKNOWLEDGMENT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "你是一位即将毕业的大学生，正在撰写本科毕业论文的致谢部分。\n\n"
                "要求：\n"
                "1. 字数 200-350 字\n"
                "2. 感谢对象包括：指导教师、同学、家人\n"
                "3. 语言真诚自然，不过度煽情，不使用模板套话\n"
                "4. 只输出致谢正文，不加「致谢」标题"
            ),
        ),
        ("human", "论文标题：{title}\n指导教师：{advisor}"),
    ]
)
