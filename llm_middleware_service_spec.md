# LLM 中转服务开发说明文档

## 一、项目概述

本项目是一个基于 **Python + LangChain + FastAPI** 构建的大模型中转服务（LLM Middleware Service）。

- 对外暴露 HTTP REST API，供其他服务调用
- 内部集成 DeepSeek 大模型 API
- 基于 LangChain 实现提示词构造、上下文管理、输出优化等能力
- 架构清晰，便于持续扩展新功能

---

## 二、技术栈

| 组件 | 选型 |
|------|------|
| 语言 | Python 3.11+ |
| Web 框架 | FastAPI |
| ASGI 服务器 | Uvicorn |
| LLM 框架 | LangChain |
| 大模型 API | DeepSeek（兼容 OpenAI 接口规范） |
| 包管理 | uv |
| 环境管理 | uv venv（虚拟环境） |
| 数据校验 | Pydantic v2 |
| 配置管理 | python-dotenv |

---

## 三、项目目录结构

```
llm_middleware/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI 应用入口，注册路由
│   ├── config.py                # 全局配置（读取 .env）
│   │
│   ├── api/                     # 路由层：对外暴露的接口
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── extract.py       # 文本核心内容提取接口
│   │
│   ├── schemas/                 # 请求/响应数据结构（Pydantic）
│   │   ├── __init__.py
│   │   └── extract.py
│   │
│   ├── services/                # 业务逻辑层
│   │   ├── __init__.py
│   │   └── extract_service.py   # 核心内容提取业务逻辑
│   │
│   └── llm/                     # LLM 层：模型初始化、提示词、链
│       ├── __init__.py
│       ├── client.py            # DeepSeek LLM 客户端初始化
│       └── prompts/
│           ├── __init__.py
│           └── extract_prompt.py  # 提取任务的提示词模板
│
├── .env                         # 环境变量（不提交 git）
├── .env.example                 # 环境变量示例（提交 git）
├── .gitignore
├── pyproject.toml               # uv 项目配置
└── README.md
```

---

## 四、环境变量配置（.env）

```env
# DeepSeek API 配置
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 服务配置
APP_HOST=0.0.0.0
APP_PORT=8000
APP_DEBUG=false
```

---

## 五、依赖包清单

使用 `uv add` 安装以下依赖：

```bash
uv add fastapi uvicorn langchain langchain-openai pydantic python-dotenv
```

`pyproject.toml` 中 dependencies 部分如下：

```toml
[project]
name = "llm-middleware"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi",
    "uvicorn",
    "langchain",
    "langchain-openai",
    "pydantic>=2.0",
    "python-dotenv",
]
```

---

## 六、各模块实现说明

### 6.1 配置模块 `app/config.py`

使用 `pydantic-settings`（或 `python-dotenv`）读取 `.env` 文件，提供全局配置单例：

```python
# 需包含字段：
# - deepseek_api_key: str
# - deepseek_base_url: str
# - deepseek_model: str
# - app_host: str
# - app_port: int
# - app_debug: bool
```

### 6.2 LLM 客户端 `app/llm/client.py`

DeepSeek 兼容 OpenAI 接口规范，使用 `langchain-openai` 中的 `ChatOpenAI` 初始化：

```python
# 关键参数：
# - model: 从配置读取（如 "deepseek-chat"）
# - api_key: DEEPSEEK_API_KEY
# - base_url: DEEPSEEK_BASE_URL
# 返回一个可复用的 llm 实例（单例模式）
```

### 6.3 提示词模板 `app/llm/prompts/extract_prompt.py`

使用 LangChain 的 `ChatPromptTemplate` 定义提取任务提示词：

```python
# 系统提示词要求模型：
# - 仅提取核心内容，不添加额外信息
# - 输出简洁、结构化
# - 语言与输入文本一致

# 用户提示词包含一个变量：{text}（待提取的原始文本）
```

### 6.4 业务服务层 `app/services/extract_service.py`

组装 LangChain Chain，实现提取逻辑：

```python
# 使用 LCEL（LangChain Expression Language）组装链：
# chain = prompt | llm | StrOutputParser()

# 对外暴露一个异步函数：
# async def extract_core_content(text: str) -> str
```

### 6.5 数据结构 `app/schemas/extract.py`

使用 Pydantic 定义请求体与响应体：

```python
# 请求体 ExtractRequest：
# - text: str（必填，待处理文本）
# - max_length: int | None（可选，期望输出最大字符数）

# 响应体 ExtractResponse：
# - core_content: str（提取后的核心内容）
# - original_length: int（原始文本长度）
# - extracted_length: int（提取后文本长度）
```

### 6.6 路由层 `app/api/v1/extract.py`

定义 FastAPI 路由，调用服务层：

```python
# POST /api/v1/extract
# - 接收 ExtractRequest
# - 调用 extract_service.extract_core_content()
# - 返回 ExtractResponse
# - 包含异常处理（HTTPException）
```

### 6.7 应用入口 `app/main.py`

```python
# 创建 FastAPI app 实例
# 注册路由前缀：/api/v1
# 添加健康检查接口：GET /health
# 加载 .env 配置
```

---

## 七、接口规范

### 7.1 健康检查

```
GET /health

Response 200:
{
  "status": "ok",
  "service": "llm-middleware"
}
```

### 7.2 文本核心内容提取

```
POST /api/v1/extract
Content-Type: application/json

Request Body:
{
  "text": "这里是需要提取核心内容的一段文字...",
  "max_length": 200   // 可选
}

Response 200:
{
  "core_content": "提取后的核心内容...",
  "original_length": 500,
  "extracted_length": 150
}

Response 422: 参数校验失败
Response 500: 模型调用失败
```

---

## 八、启动方式

```bash
# 1. 激活虚拟环境
source .venv/bin/activate

# 2. 复制并填写环境变量
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 3. 启动服务（开发模式）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 4. 访问自动生成的 API 文档
# http://localhost:8000/docs
```

---

## 九、后续扩展建议

本项目结构设计支持以下方向的平滑扩展，无需重构：

| 功能 | 扩展位置 |
|------|----------|
| 新增业务接口（如摘要、翻译、问答） | 在 `app/api/v1/` 和 `app/services/` 新增文件 |
| 上下文/多轮对话管理 | 在 `app/llm/` 新增 memory 模块，使用 LangChain Memory |
| 提示词版本管理 | 在 `app/llm/prompts/` 按功能维护多个模板 |
| 切换或新增模型（如 GPT-4、Claude） | 修改 `app/llm/client.py`，支持多模型路由 |
| 请求日志与追踪 | 在 `app/main.py` 添加 FastAPI 中间件 |
| 限流与鉴权 | 在 `app/api/` 添加依赖注入（FastAPI Depends） |
| 数据库持久化（保存对话历史） | 新增 `app/db/` 模块 |

---

## 十、注意事项

1. `.env` 文件包含密钥，**必须加入 `.gitignore`，不能提交到代码仓库**
2. DeepSeek API 兼容 OpenAI 接口规范，`langchain-openai` 的 `ChatOpenAI` 可直接使用，只需修改 `base_url` 和 `api_key`
3. 所有 LLM 调用建议使用 `async` 异步方式，避免阻塞 FastAPI 事件循环
4. 生产部署时，`APP_DEBUG` 设为 `false`，并使用 `gunicorn` 配合 `uvicorn workers` 提升并发能力
