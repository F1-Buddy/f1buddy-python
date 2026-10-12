"""Shared plot style: fonts, watermark, colours. Object-oriented matplotlib only, so plots are thread-safe."""
import io

import matplotlib.image as mpimg
from matplotlib import font_manager
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from ..util import ASSETS

DPI = 300
_FONTS = ASSETS / "fonts"
font_manager.fontManager.addfont(str(_FONTS / "Formula1-Regular.ttf"))
REGULAR = font_manager.FontProperties(fname=str(_FONTS / "Formula1-Regular.ttf"))
BOLD = font_manager.FontProperties(fname=str(_FONTS / "Formula1-Bold.ttf"))
FAMILY = REGULAR.get_name()
_WATERMARK = mpimg.imread(str(ASSETS / "watermark.png"))
COLOUR_NOTE = "*Some color data is unavailable"

LAP_FORMAT = FuncFormatter(lambda s, _: f"{int(s // 60)}:{int(s % 60):02d}")


def figure(width, height) -> Figure:
    fig = Figure(figsize=(width, height), facecolor="black")
    FigureCanvasAgg(fig)
    return fig


def style_axes(ax):
    ax.set_facecolor("black")
    ax.tick_params(colors="white", which="both", labelfontfamily=FAMILY)
    for spine in ax.spines.values():
        spine.set_color("white")
    return ax


def axes(fig, *args, **kwargs):
    return style_axes(fig.add_subplot(*args, **kwargs))


def label(ax, x=None, y=None):
    if x:
        ax.set_xlabel(x, fontproperties=REGULAR, color="white")
    if y:
        ax.set_ylabel(y, fontproperties=REGULAR, color="white")


def legend(ax, *args, **kwargs):
    kwargs.setdefault("prop", BOLD)
    kwargs.setdefault("facecolor", "black")
    kwargs.setdefault("edgecolor", "white")
    kwargs.setdefault("labelcolor", "white")
    return ax.legend(*args, **kwargs)


def add_watermark(fig, corner="top-left"):
    """Logo plus credit text at a fixed margin from the chosen corner."""
    width, height = fig.get_size_inches()
    h = 0.5 / height            # half an inch tall on every plot
    w = 0.5 / width
    bottom = 0.99 - h if corner == "top-left" else 0.01
    logo = fig.add_axes([0.01, bottom, w, h])
    logo.imshow(_WATERMARK)
    logo.axis("off")
    fig.text(0.01 + w + 0.005, bottom + h / 2, "Made by F1Buddy Discord Bot",
             fontproperties=BOLD, color="white", fontsize=8, va="center", ha="left")


def finish(fig, corner="top-left", colour_note=False) -> bytes:
    """Add the watermark and return the figure as PNG bytes."""
    add_watermark(fig, corner)
    if colour_note:
        fig.text(0.99, 0.01, COLOUR_NOTE, fontproperties=REGULAR, color="white", fontsize=8, ha="right")
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=DPI, facecolor="black")
    return buffer.getvalue()


def colour(value) -> tuple[str, bool]:
    """(usable colour, was it missing?) for a colour that may be None or a bare hex string."""
    if not value or str(value).lower() in ("nan", "none"):
        return "#ffffff", True
    value = str(value)
    return (value if value.startswith("#") else f"#{value}"), False


def clash(first: str, second: str) -> str:
    """Two-driver plots: if both resolve to the same colour, draw the second white (grey if the first is white)."""
    if first.lower() != second.lower():
        return second
    return "#808080" if first.lower() in ("#ffffff", "white") else "#ffffff"
