"""Telemetry plots: speed/throttle/brake traces, track dominance, and the circuit outline."""
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from .. import style


def telemetry(data) -> bytes:
    fig = style.figure(13, 9)
    speed, throttle, brake = (style.style_axes(ax) for ax in fig.subplots(3, 1, sharex=True,
                                                                           height_ratios=[3, 1.5, 1]))
    top = 0.0
    for trace in data.traces:
        speed.plot(trace.distance, trace.speed, color=trace.colour, linewidth=1.2)
        speed.axhline(float(np.mean(trace.speed)), color=trace.colour, linestyle="--", linewidth=0.8)
        throttle.plot(trace.distance, trace.throttle, color=trace.colour, linewidth=1.2)
        brake.plot(trace.distance, trace.brake, color=trace.colour, linewidth=1.2)
        top = max(top, max(trace.speed))
    speed.set_ylim(0, top + 10)
    throttle.set_ylim(0, 105)
    brake.set_ylim(0, 1.1)
    brake.set_yticks([0, 1], ["Off", "On"])
    length = max(max(t.distance) for t in data.traces)
    for distance, name in data.corners:
        if distance <= length:
            speed.axvline(distance, color="#444444", linewidth=0.5, zorder=0)
            speed.text(distance, top + 12, name, color="#aaaaaa", fontsize=6, ha="center",
                       fontproperties=style.REGULAR)
    speed.set_xlim(0, length)
    style.label(speed, y="Speed (km/h)")
    style.label(throttle, y="Throttle %")
    style.label(brake, x="Distance (m)", y="Brake")
    fig.suptitle(data.title, fontproperties=style.BOLD, color="white", fontsize=16)
    handles = [Patch(color=t.colour, label=t.code) for t in data.traces]
    style.legend(speed, handles=handles, loc="lower right")
    fig.subplots_adjust(top=0.9, hspace=0.12)
    return style.finish(fig, colour_note=data.missing_colour)


def _rotate(x, y, degrees):
    angle = np.deg2rad(degrees)
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    return x * np.cos(angle) - y * np.sin(angle), x * np.sin(angle) + y * np.cos(angle)


def segment_colours(data) -> list[str]:
    """Colour of each outline segment: the winner of the mini-sector its first point falls in."""
    palette = [data.drivers[0][1], data.drivers[1][1]]
    return [palette[w] for w in data.point_winner[:-1]]


def dominance(data) -> bytes:
    fig = style.figure(7.5, 6)
    ax = fig.add_axes([0.05, 0.08, 0.9, 0.72])
    ax.set_facecolor("black")
    x, y = _rotate(data.x, data.y, data.rotation)
    points = np.column_stack([x, y]).reshape(-1, 1, 2)
    ax.add_collection(LineCollection(np.concatenate([points[:-1], points[1:]], axis=1),
                                     colors=segment_colours(data), linewidths=2))
    ax.autoscale()
    ax.margins(0.05)
    ax.set_aspect("equal", adjustable="datalim")
    ax.axis("off")
    fig.suptitle(data.title, fontproperties=style.BOLD, color="white", fontsize=11)
    handles = [Line2D([], [], color=colour, linewidth=3, label=code) for code, colour in data.drivers]
    fig.legend(handles=handles, loc="lower right", prop=style.BOLD, facecolor="black", edgecolor="white",
               labelcolor="white")
    return style.finish(fig, corner="bottom-left")


def circuit(data) -> bytes:
    fig = style.figure(6, 4.5)
    ax = fig.add_axes([0.05, 0.12, 0.9, 0.83])
    ax.set_facecolor("black")
    x, y = _rotate(data.x, data.y, data.rotation)
    ax.plot(np.append(x, x[0]), np.append(y, y[0]), color="white", linewidth=3)
    ax.set_aspect("equal", adjustable="datalim")
    ax.axis("off")
    return style.finish(fig, corner="bottom-left")
