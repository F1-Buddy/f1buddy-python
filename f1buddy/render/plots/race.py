"""Session plots: lap times, positions, tyre strategy, qualifying gap, consistency. Data in, PNG bytes out."""
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import MultipleLocator

from .. import style


def laptimes(data) -> bytes:
    fig = style.figure(9, 6)
    ax = style.axes(fig)
    for line in data.lines:
        ax.plot(line.x, line.y, color=line.colour, label=line.code)
    ax.set_xlim(0, data.total_laps)
    ax.yaxis.set_major_formatter(style.LAP_FORMAT)
    style.label(ax, f"Lap Number (of {data.total_laps})", "Lap Time")
    ax.set_title(data.title, fontproperties=style.BOLD, color="white")
    style.legend(ax, loc="upper right")
    fig.subplots_adjust(top=0.86)
    return style.finish(fig, colour_note=data.missing_colour)


def positions(data) -> bytes:
    fig = style.figure(10.6, 6.5)
    ax = style.axes(fig)
    for line in data.lines:
        ax.plot(line.x, line.y, color=line.colour, label=line.code, linestyle="--" if line.dashed else "-")
    ax.set_ylim(data.n_drivers + 1, 0)
    ax.set_yticks(range(1, data.n_drivers + 1))
    ax.set_xlim(0, max(data.total_laps, 1))
    ax.xaxis.set_major_locator(MultipleLocator(5))
    ax.xaxis.set_minor_locator(MultipleLocator(1))
    style.label(ax, "Lap", "Position")
    ax.set_title(data.title, fontproperties=style.BOLD, color="white")
    style.legend(ax, bbox_to_anchor=(1.0, 1.02), loc="upper left")
    fig.subplots_adjust(top=0.86, right=0.87, left=0.06)
    return style.finish(fig, colour_note=data.missing_colour)


def strategy(data) -> bytes:
    fig = style.figure(10, 10)
    ax = style.axes(fig)
    used = []
    for code, stints in data.drivers:
        start = 0
        for compound, laps in stints:
            colour = data.palette.get(compound, data.palette["UNKNOWN"])
            ax.barh(code, laps, left=start, color=colour, edgecolor="black")
            start += laps
            if compound not in used:
                used.append(compound)
    ax.invert_yaxis()
    ax.set_xlim(0, max(data.total_laps, 1))
    ax.xaxis.set_major_locator(MultipleLocator(10))
    ax.xaxis.set_minor_locator(MultipleLocator(2))
    style.label(ax, "Lap")
    ax.set_title(data.title, fontproperties=style.BOLD, color="white", fontsize=20)
    handles = [Patch(facecolor=data.palette.get(c, data.palette["UNKNOWN"]), edgecolor="black", label=c.title())
               for c in used]
    style.legend(ax, handles=handles, loc="lower right")
    fig.subplots_adjust(top=0.88)
    return style.finish(fig)


def qualigap(data) -> bytes:
    fig = style.figure(8.25, 5.5)
    ax = style.axes(fig)
    gaps = [delta for _, _, delta in data.rows if delta]
    cap = min(max(gaps, default=1.0), 5.0)
    for i, (code, colour, delta) in enumerate(data.rows):
        if delta is None:
            text = "No Time"
        else:
            ax.barh(i, min(max(delta, 0.0), cap), color=colour)
            text = "Pole" if delta == 0 and i == 0 else f"{delta:+.3f}"
        width = 0 if delta is None else min(max(delta, 0.0), cap)
        ax.text(width + cap * 0.01, i, text, va="center", color="white", fontproperties=style.REGULAR, fontsize=7)
    ax.set_yticks(range(len(data.rows)), [code for code, _, _ in data.rows])
    ax.set_ylim(len(data.rows), -1)
    ax.set_xlim(0, cap * 1.12)
    style.label(ax, "Gap to pole (s)")
    ax.set_title(data.title, fontproperties=style.BOLD, color="white")
    fig.subplots_adjust(top=0.84)
    return style.finish(fig, colour_note=data.missing_colour)


CONSISTENCY = {"quicker": ("#00ff00", "Quicker"), "slower": ("#ffaf00", "Slower"),
               "fastest": ("#B138DD", "Fastest"), "outlier": ("#F91536", "Outlier")}


def consistency(data) -> bytes:
    fig = style.figure(9, 6)
    ax = style.axes(fig)
    for kind, (colour, _) in CONSISTENCY.items():
        points = [(n, t) for n, t, k in data.laps if k == kind]
        if points:
            ax.scatter(*zip(*points), color=colour, s=18, zorder=3)
    ax.axhline(data.mean, color="#969696", linestyle="--")
    ax.yaxis.set_major_formatter(style.LAP_FORMAT)
    style.label(ax, "Lap Number", "Lap Time")
    ax.set_title(data.title, fontproperties=style.BOLD, color="white")
    handles = [Line2D([], [], color="#969696", linestyle="--", label="Average")]
    handles += [Line2D([], [], color=CONSISTENCY[k][0], marker="o", linestyle="", label=CONSISTENCY[k][1])
                for k in ("fastest", "quicker", "slower", "outlier")]
    style.legend(ax, handles=handles, bbox_to_anchor=(1.01, 1), loc="upper left")
    fig.subplots_adjust(top=0.84, right=0.82)
    return style.finish(fig)
