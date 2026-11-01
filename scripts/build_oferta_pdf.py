"""Render assets/oferta.txt into assets/oferta.pdf.

Retention periods are taken from config_data.retention so the file matches the bot.
"""

from __future__ import annotations

import ast
import textwrap
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from matplotlib import font_manager  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "oferta.txt"
OUTPUT = ROOT / "assets" / "oferta.pdf"

PAGE_W = 8.27
PAGE_H = 11.69
LEFT = 0.75
TOP = 10.95
BOTTOM = 0.7
WRAP = 86


@dataclass(frozen=True)
class Block:
    kind: str
    text: str


def _font(bold: bool) -> font_manager.FontProperties:
    data = Path(matplotlib.get_data_path())
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    path = data / "fonts" / "ttf" / name
    if not path.is_file():
        raise FileNotFoundError(path)
    return font_manager.FontProperties(fname=str(path))


def _retention_days() -> tuple[int, int]:
    tree = ast.parse((ROOT / "config_data" / "retention.py").read_text(encoding="utf-8"))
    values: dict[str, int] = {}
    wanted = {"SEIZURE_RETENTION_DAYS", "USER_DATA_RETENTION_DAYS"}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id not in wanted:
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, int):
            values[target.id] = node.value.value
    return values["SEIZURE_RETENTION_DAYS"], values["USER_DATA_RETENTION_DAYS"]


def _load_blocks() -> list[Block]:
    seizure_days, user_days = _retention_days()
    raw = SOURCE.read_text(encoding="utf-8")
    raw = raw.replace("__SEIZURE_RETENTION_DAYS__", str(seizure_days))
    raw = raw.replace("__USER_RETENTION_DAYS__", str(user_days))
    blocks: list[Block] = []
    for paragraph in raw.split("\n\n"):
        text = " ".join(paragraph.split())
        if not text:
            continue
        if text.startswith("## "):
            blocks.append(Block("heading", text[3:].strip()))
        elif text.startswith("# "):
            blocks.append(Block("title", text[2:].strip()))
        else:
            blocks.append(Block("body", text))
    return blocks


def _lines(block: Block) -> list[tuple[str, str]]:
    if block.kind == "title":
        wrapped = textwrap.wrap(block.text, width=48) or [block.text]
        return [("title", line) for line in wrapped]
    if block.kind == "heading":
        wrapped = textwrap.wrap(block.text, width=70) or [block.text]
        return [("heading", line) for line in wrapped]
    wrapped = textwrap.wrap(block.text, width=WRAP) or [""]
    return [("body", line) for line in wrapped]


def _line_step(kind: str) -> float:
    if kind == "title":
        return 0.34
    if kind == "heading":
        return 0.30
    return 0.23


def build() -> Path:
    fonts = {
        "title": _font(True),
        "heading": _font(True),
        "body": _font(False),
    }
    sizes = {"title": 16, "heading": 12.5, "body": 10.5}
    pages: list[Figure] = []
    figure = Figure(figsize=(PAGE_W, PAGE_H))
    figure.patch.set_facecolor("white")
    pages.append(figure)
    y = TOP

    def new_page() -> float:
        nonlocal figure
        figure = Figure(figsize=(PAGE_W, PAGE_H))
        figure.patch.set_facecolor("white")
        pages.append(figure)
        return TOP

    for block in _load_blocks():
        lines = _lines(block)
        needed = sum(_line_step(kind) for kind, _ in lines) + (0.12 if block.kind == "heading" else 0.06)
        if y - needed < BOTTOM:
            y = new_page()
        if block.kind == "heading":
            y -= 0.12
        for kind, line in lines:
            if y - _line_step(kind) < BOTTOM:
                y = new_page()
            figure.text(
                LEFT / PAGE_W,
                y / PAGE_H,
                line,
                fontproperties=fonts[kind],
                fontsize=sizes[kind],
                color="#1c1c1c",
                ha="left",
                va="top",
            )
            y -= _line_step(kind)
        y -= 0.08

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(OUTPUT) as pdf:
        total = len(pages)
        for index, page in enumerate(pages, start=1):
            page.text(
                0.5,
                0.035,
                f"{index} / {total}",
                fontproperties=fonts["body"],
                fontsize=9,
                color="#666666",
                ha="center",
                va="bottom",
            )
            pdf.savefig(page)
    return OUTPUT


if __name__ == "__main__":
    path = build()
    print(path)
