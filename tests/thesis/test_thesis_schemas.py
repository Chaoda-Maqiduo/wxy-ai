import json

from app.schemas.thesis import (
    extract_figure_placeholders,
    split_by_render_method,
    validate_figure_payload,
)


def _figure_block(payload: dict) -> str:
    return f"<<FIGURE>>{json.dumps(payload, ensure_ascii=False)}<</FIGURE>>"


def test_validate_figure_payload_mermaid() -> None:
    result = validate_figure_payload(
        {
            "caption": "系统架构图",
            "render_method": "mermaid",
            "mermaid_code": "graph TD; A-->B;",
        },
        index=0,
    )

    assert result["render_method"] == "mermaid"
    assert result["caption"] == "系统架构图"
    assert result["index"] == 0


def test_validate_figure_payload_ai_image() -> None:
    result = validate_figure_payload(
        {
            "caption": "概念图",
            "render_method": "ai_image",
            "description": "A modern AI lab",
        },
        index=1,
    )

    assert result["render_method"] == "ai_image"
    assert result["style"] == "concept_illustration"
    assert result["aspect_ratio"] == "16:9"
    assert result["index"] == 1


def test_extract_figure_placeholders_json_parse_error_fallback() -> None:
    text = "前文\n<<FIGURE>>{bad json}<</FIGURE>>\n后文"

    placeholders = extract_figure_placeholders(text)

    assert len(placeholders) == 1
    assert placeholders[0]["render_method"] == "fallback"
    assert placeholders[0]["index"] == 0
    assert "JSON 解析失败" in placeholders[0]["error"]


def test_extract_figure_placeholders_missing_required_field_fallback() -> None:
    text = _figure_block(
        {
            "caption": "缺少代码",
            "render_method": "mermaid",
        }
    )

    placeholders = extract_figure_placeholders(text)

    assert len(placeholders) == 1
    assert placeholders[0]["render_method"] == "fallback"
    assert placeholders[0]["index"] == 0


def test_extract_figure_placeholders_unknown_method_fallback() -> None:
    text = _figure_block(
        {
            "caption": "未知渲染类型",
            "render_method": "xyz",
            "description": "anything",
        }
    )

    placeholders = extract_figure_placeholders(text)

    assert len(placeholders) == 1
    assert placeholders[0]["render_method"] == "fallback"
    assert placeholders[0]["index"] == 0


def test_extract_figure_placeholders_empty_text() -> None:
    placeholders = extract_figure_placeholders("这是一段没有占位符的正文。")
    assert placeholders == []


def test_split_by_render_method() -> None:
    text = "\n".join(
        [
            _figure_block(
                {
                    "caption": "流程图",
                    "render_method": "mermaid",
                    "mermaid_code": "graph TD; A-->B;",
                }
            ),
            _figure_block(
                {
                    "caption": "插画",
                    "render_method": "ai_image",
                    "description": "A city skyline",
                }
            ),
            "<<FIGURE>>{broken}<</FIGURE>>",
        ]
    )

    placeholders = extract_figure_placeholders(text)
    mermaid, ai_image, fallback = split_by_render_method(placeholders)

    assert len(placeholders) == 3
    assert len(mermaid) == 1
    assert len(ai_image) == 1
    assert len(fallback) == 1
