"""Season-wide plots: average position and teammate head-to-head."""
import matplotlib.patheffects as path_effects
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from PIL import Image

from ...util import ASSETS
from .. import style

STROKE = [path_effects.withStroke(linewidth=3, foreground="black")]


def avgpos(data) -> bytes:
    fig = style.figure(16.8, 10.5)
    ax = style.axes(fig)
    labels = [label for label, _, _ in data.rows]
    values = [value for _, value, _ in data.rows]
    ax.barh(range(len(labels)), values, color=[colour for _, _, colour in data.rows])
    for i, value in enumerate(values):
        ax.text(value + 0.1, i, f"{value:.2f}", va="center", color="white", fontproperties=style.REGULAR,
                fontsize=12)
    ax.set_yticks(range(len(labels)), labels)
    ax.tick_params(axis="y", labelsize=20 if data.large_labels and len(labels) <= 24 else 10)
    ax.tick_params(axis="x", labelsize=14)
    ax.set_xlim(0, data.x_max + 1.1)
    ax.invert_yaxis()
    style.label(ax, "Average position")
    ax.set_title(data.title, fontproperties=style.BOLD, color="white", fontsize=20)
    fig.subplots_adjust(top=0.9, left=0.14)
    return style.finish(fig, colour_note=data.missing_colour)


def _logo(team_id):
    path = ASSETS / "logos" / f"{team_id}.webp"
    if not path.exists():
        return None
    image = Image.open(path).convert("RGBA")
    image.thumbnail((64, 64))
    return image


def h2h(data) -> bytes:
    rows = len(data.pairs)
    fig = style.figure(13, max(9, rows * 0.75))
    ax = fig.add_axes([0.08, 0.04, 0.84, 0.8])
    ax.set_facecolor("black")
    reach = max(max(left, right) for *_, left, _, right in data.pairs) or 1
    for i, (team_id, name, colour, left_code, left, right_code, right) in enumerate(data.pairs):
        ax.barh(i, -left, color=colour, height=0.7)
        ax.barh(i, right, color=colour, height=0.7, alpha=0.6)
        ax.text(-max(left, reach * 0.06) - reach * 0.03, i, str(left), ha="right", va="center", color="white", fontsize=20,
                fontproperties=style.BOLD, path_effects=STROKE)
        ax.text(max(right, reach * 0.06) + reach * 0.03, i, str(right), ha="left", va="center", color="white", fontsize=20,
                fontproperties=style.BOLD, path_effects=STROKE)
        ax.text(-reach * 1.32, i, left_code, ha="left", va="center", color="white", fontsize=14,
                fontproperties=style.BOLD)
        ax.text(reach * 1.32, i, right_code, ha="right", va="center", color="white", fontsize=14,
                fontproperties=style.BOLD)
        logo = _logo(team_id)
        if logo is not None:
            ax.add_artist(AnnotationBbox(OffsetImage(logo, zoom=0.5), (0, i), frameon=False))
        else:
            ax.text(0, i, name, ha="center", va="center", color="white", fontsize=9,
                    fontproperties=style.BOLD, path_effects=STROKE)
    ax.set_xlim(-reach * 1.35, reach * 1.35)
    ax.set_ylim(rows - 0.5, -0.5)
    ax.axis("off")
    fig.suptitle(data.title, fontproperties=style.BOLD, color="white", fontsize=18, y=0.9)
    return style.finish(fig, colour_note=data.missing_colour)
