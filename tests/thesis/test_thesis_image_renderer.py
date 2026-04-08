import asyncio
from pathlib import Path

from app.services.thesis.image_renderer import PlaceholderImageGenerator, render_all_figures, render_chart


def _chart_spec(chart_type: str) -> dict:
    base = {
        "caption": "图表",
        "render_method": "chart",
        "chart_type": chart_type,
        "title": "测试图表",
        "x_label": "X",
        "y_label": "Y",
        "categories": ["A", "B", "C"],
    }
    if chart_type == "pie":
        return base | {
            "series": [{"name": "占比", "data": [45, 35, 20]}],
        }
    return base | {
        "series": [{"name": "值", "data": [1, 3, 2]}],
    }


def test_render_chart_line_creates_png(tmp_path: Path) -> None:
    output = tmp_path / "line.png"
    path = asyncio.run(render_chart(_chart_spec("line"), str(output)))
    assert Path(path).exists()
    assert Path(path).stat().st_size > 0


def test_render_chart_bar_creates_png(tmp_path: Path) -> None:
    output = tmp_path / "bar.png"
    path = asyncio.run(render_chart(_chart_spec("bar"), str(output)))
    assert Path(path).exists()
    assert Path(path).stat().st_size > 0


def test_render_chart_pie_creates_png(tmp_path: Path) -> None:
    output = tmp_path / "pie.png"
    path = asyncio.run(render_chart(_chart_spec("pie"), str(output)))
    assert Path(path).exists()
    assert Path(path).stat().st_size > 0


def test_render_all_figures_dispatches_chart(tmp_path: Path) -> None:
    output_dir = tmp_path / "images"
    placeholders = [
        _chart_spec("line") | {"index": 0},
    ]

    result = asyncio.run(
        render_all_figures(
            placeholders=placeholders,
            image_generator=PlaceholderImageGenerator(),
            output_dir=str(output_dir),
        )
    )

    assert 0 in result
    assert result[0] is not None
    assert Path(result[0]).exists()
