"""Spec 03: plot commands."""
import asyncio
import statistics
import struct
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from f1buddy import config, ctx
from f1buddy.cogs import plots as plots_cog
from f1buddy.data import plots
from f1buddy.errors import SourceError, UserError
from f1buddy.render import style
from f1buddy.render.plots import race, season, telemetry
from f1buddy.sources import fastf1_src, gemini, jolpica

from conftest import UTC, FakeInteraction, three_race_season

MID_SEASON = datetime(2026, 3, 20, tzinfo=UTC)
CODES = [f"D{i:02d}" for i in range(1, 21)]


def png_size(png: bytes):
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", png[16:24])


@pytest.fixture(autouse=True)
def fast_render(monkeypatch):
    monkeypatch.setattr(style, "DPI", 40)


def results_frame(n=20):
    return pd.DataFrame({
        "Abbreviation": [f"D{i:02d}" for i in range(1, n + 1)],
        "FullName": [f"Driver {i}" for i in range(1, n + 1)],
        "LastName": [f"Last{i}" for i in range(1, n + 1)],
        "TeamId": [f"team{(i + 1) // 2}" for i in range(1, n + 1)],
        "Position": [float(i) for i in range(1, n + 1)],
        "GridPosition": [float(n + 1 - i) for i in range(1, n + 1)],   # grid reversed
    })


def laps_frame(n=20, total=30, retire=None):
    """Every driver holds their finishing position; `retire` maps code -> last lap."""
    rows = []
    for i in range(1, n + 1):
        code = f"D{i:02d}"
        for lap in range(1, (retire or {}).get(code, total) + 1):
            rows.append({"Driver": code, "LapNumber": float(lap), "Position": float(i),
                         "LapTime": pd.Timedelta(seconds=90 + i * 0.1 + lap * 0.01),
                         "Stint": 1.0 if lap <= 12 else 2.0, "Compound": "MEDIUM" if lap <= 12 else "HARD",
                         "PitInTime": pd.NaT, "PitOutTime": pd.NaT, "TrackStatus": "1"})
    return pd.DataFrame(rows)


@pytest.fixture
def session(monkeypatch, seasons, clock):
    """Replace FastF1 with a hand-built session; returns the list of load calls."""
    seasons({2026: three_race_season(), 2018: three_race_season(2018)})
    clock(MID_SEASON)
    box = SimpleNamespace(results=results_frame(), laps=laps_frame(), calls=[])

    async def load(year, round, name, **flags):
        box.calls.append((year, round, name, flags))
        return box
    monkeypatch.setattr(fastf1_src, "load", load)
    return box


# ------------------------------------------------------------ shared rules

def test_png_has_the_expected_pixel_size(monkeypatch):
    monkeypatch.setattr(style, "DPI", 300)
    data = plots.compute_laptimes(laps_frame(), ("D01", "D02"), {}, "t")
    assert png_size(race.laptimes(data)) == (9 * 300, 6 * 300)


def test_no_pyplot_state_is_used():
    import matplotlib.pyplot as plt
    race.laptimes(plots.compute_laptimes(laps_frame(), ("D01", "D02"), {}, "t"))
    with pytest.raises(Exception):
        race.positions(SimpleNamespace(lines=None))    # a failing render must not leak a figure either
    assert plt.get_fignums() == []


def test_two_threads_render_correct_images():
    a = plots.compute_laptimes(laps_frame(), ("D01", "D02"), {}, "A")
    b = plots.compute_strategy(laps_frame(), results_frame(), 2026, "B")
    alone = (png_size(race.laptimes(a)), png_size(race.strategy(b)))
    with ThreadPoolExecutor(2) as pool:
        together = list(pool.map(lambda job: png_size(job[0](job[1])), [(race.laptimes, a), (race.strategy, b)] * 4))
    assert together == list(alone) * 4


async def test_second_request_is_served_from_cache(session, monkeypatch):
    calls = []
    real = plots.compute_positions
    monkeypatch.setattr(plots, "compute_positions", lambda *a: calls.append(1) or real(*a))
    first = await plots.positions(None, None)
    second = await plots.positions("2", 2026)          # same event, spelled out
    assert first == second and len(calls) == 1
    assert first[1] == {"title": "Driver Positions", "description": "2026 Chinese Grand Prix"}


async def test_symmetric_plots_share_a_cache_entry(session, monkeypatch):
    calls = []
    real = plots.compute_laptimes
    monkeypatch.setattr(plots, "compute_laptimes", lambda *a: calls.append(1) or real(*a))
    await plots.laptimes("D01", "D02", None, None)
    await plots.laptimes("last2", "driver 1", None, None)     # other order, matched by name
    assert len(calls) == 1


async def test_shared_errors(session):
    with pytest.raises(UserError, match="between 2018 and 2026"):
        await plots.positions(None, 2017)
    with pytest.raises(UserError, match="Use 2 different drivers!"):
        await plots.laptimes("D01", "d01", None, None)
    with pytest.raises(UserError, match="ZZZ didn't take part in 2026 Chinese Grand Prix Race."):
        await plots.consistency("zzz", None, None)
    session.laps = laps_frame().iloc[0:0]
    with pytest.raises(UserError, match="No lap data is available for 2026 Chinese Grand Prix Race."):
        await plots.strategy(None, None)


# ---------------------------------------------------------------- laptimes

def test_laptimes_lines():
    laps = laps_frame(retire={"D02": 20})
    laps.loc[(laps.Driver == "D01") & (laps.LapNumber == 5), "LapTime"] = pd.NaT     # untimed lap
    data = plots.compute_laptimes(laps, ("D01", "D02"), {"D01": "#0000ff", "D02": "0000FF"}, "t")
    one, two = data.lines
    assert len(one.x) == 30 and np.isnan(one.y[4]) and one.y[0] == pytest.approx(90.11)
    assert two.x[-1] == 20 and data.total_laps == 30          # the retired driver's line ends at lap 20
    assert (one.colour, two.colour) == ("#0000ff", "#ffffff")  # same colour: second drawn white
    assert png_size(race.laptimes(data))


def test_colour_clash_rule():
    assert style.clash("#ff0000", "#00ff00") == "#00ff00"
    assert style.clash("#ff0000", "#FF0000") == "#ffffff"
    assert style.clash("#ffffff", "#ffffff") == "#808080"
    assert style.colour(None) == ("#ffffff", True) and style.colour("27F4D2") == ("#27F4D2", False)


# --------------------------------------------------------------- positions

@pytest.mark.parametrize("n", [20, 22])
def test_positions_axis_follows_grid_size(n):
    data = plots.compute_positions(laps_frame(n), results_frame(n), {}, "t")
    assert data.n_drivers == n and len(data.lines) == n
    first = data.lines[0]
    assert (first.x[0], first.y[0]) == (0, n)                 # starts at the grid position, on lap 0
    assert [l.dashed for l in data.lines[:4]] == [False, True, False, True]   # second car of each team
    assert data.missing_colour and png_size(race.positions(data))


# ---------------------------------------------------------------- strategy

def test_strategy_stints_palette_and_unknown_compound():
    laps = laps_frame(retire={"D03": 18})
    laps.loc[(laps.Driver == "D02") & (laps.Stint == 2), "Compound"] = "WEIRD"
    y2018 = plots.compute_strategy(laps, results_frame(), 2018, "t")
    y2024 = plots.compute_strategy(laps, results_frame(), 2024, "t")
    assert y2018.palette["SOFT"] == "yellow" and y2024.palette["SOFT"] == "#da291c"   # no sticky 2018 palette
    stints = dict(y2024.drivers)
    assert stints["D01"] == (("MEDIUM", 12), ("HARD", 18))
    assert sum(n for _, n in stints["D03"]) == 18 and stints["D02"][1][0] == "WEIRD"
    assert [code for code, _ in y2024.drivers] == CODES       # finishing order
    assert png_size(race.strategy(y2024))                     # unknown compound draws, in the UNKNOWN colour


# ---------------------------------------------------------------- qualigap

def quali_frame(q3=True):
    def td(seconds):
        return pd.Timedelta(seconds=seconds) if seconds else pd.NaT
    return pd.DataFrame({
        "Abbreviation": ["AAA", "BBB", "CCC", "DDD"], "Position": [1.0, 2.0, 3.0, 4.0],
        "Q1": [td(92), td(92.5), td(93.1), td(None)], "Q2": [td(91), td(91.4), td(None), td(None)],
        "Q3": [td(90) if q3 else td(None), td(90.25) if q3 else td(None), td(None), td(None)]})


def test_qualigap_deltas():
    data = plots.compute_qualigap(quali_frame(), {"AAA": "#111111"}, "t")
    assert [(c, d) for c, _, d in data.rows] == [("AAA", 0.0), ("BBB", 0.25), ("CCC", pytest.approx(3.1)),
                                                 ("DDD", None)]
    assert data.missing_colour and png_size(race.qualigap(data))


def test_qualigap_without_q3_uses_q2():
    data = plots.compute_qualigap(quali_frame(q3=False), {}, "t")
    assert [d for _, _, d in data.rows][:2] == [0.0, pytest.approx(0.4)]


# ------------------------------------------------------------- consistency

def consistency_laps():
    times = [100, 90.0, 90.2, 90.4, 115, 112, 90.6, 91.0, 89.5, 130, 91.2, 90.8]
    none = pd.Series([pd.NaT] * 12, dtype="timedelta64[ns]")
    df = pd.DataFrame({"LapNumber": range(1, 13), "LapTime": pd.to_timedelta(times, unit="s"),
                       "PitInTime": none, "PitOutTime": none.copy(), "TrackStatus": "1", "Driver": "AAA"})
    df.loc[4, "PitInTime"] = pd.Timedelta(minutes=9)       # lap 5: in-lap
    df.loc[5, "PitOutTime"] = pd.Timedelta(minutes=10)     # lap 6: out-lap
    df.loc[9, "TrackStatus"] = "4"                         # lap 10: safety car
    return df


def test_consistency_outliers_and_sigma():
    data = plots.compute_consistency(consistency_laps(), "AAA", "t")
    kinds = {n: k for n, _, k in data.laps}
    assert sorted(n for n, k in kinds.items() if k == "outlier") == [1, 5, 6, 10]
    assert kinds[9] == "fastest" and kinds[2] == "quicker" and kinds[11] == "slower"
    clean = [90.0, 90.2, 90.4, 90.6, 91.0, 89.5, 91.2, 90.8]
    assert data.mean == pytest.approx(statistics.mean(clean), abs=1e-6)
    assert data.std == pytest.approx(statistics.stdev(clean), abs=1e-3)
    assert png_size(race.consistency(data))


def test_consistency_flags_slow_green_laps():
    laps = consistency_laps()
    laps.loc[7, "LapTime"] = pd.Timedelta(seconds=98)      # lap 8: more than 107% of the median
    assert dict((n, k) for n, _, k in plots.compute_consistency(laps, "AAA", "t").laps)[8] == "outlier"


def test_consistency_needs_three_clean_laps():
    with pytest.raises(UserError, match="Not enough clean laps"):
        plots.compute_consistency(consistency_laps().iloc[:3], "AAA", "t")


async def test_consistency_embed_text(session):
    png, meta = await plots.consistency("d05", None, None)
    assert meta["title"] == "D05 Laptime Consistency"
    assert meta["description"].startswith("2026 Chinese Grand Prix\nσ = 0.") and meta["description"].endswith(" s")
    assert "excluding outliers" in meta["footer"]


# --------------------------------------------------------------- telemetry

@pytest.fixture
def car_data(monkeypatch):
    def fake(lap):
        distance = np.linspace(0, 5000, 50)
        return pd.DataFrame({"Distance": distance, "Speed": 200 + 50 * np.sin(distance / 500),
                             "Throttle": 80.0, "Brake": distance % 1000 < 100,
                             "X": np.cos(distance / 800) * 1000, "Y": np.sin(distance / 800) * 1000})
    monkeypatch.setattr(fastf1_src, "car_data", fake)
    monkeypatch.setattr(fastf1_src, "position_data", fake)
    monkeypatch.setattr(fastf1_src, "circuit_info", lambda s: None)


async def test_telemetry_two_and_one_driver(session, car_data):
    png, meta = await plots.telemetry("D01", "D02", None, None, None, None)
    assert png_size(png) and meta["title"] == "Fastest Lap Race Telemetry"
    # each driver's own fastest lap: lap 1 in the fixture (90 + i*0.1 + 0.01)
    assert meta["description"] == "2026 Chinese Grand Prix\nD01: 1:30.110\nD02: 1:30.210"
    assert session.calls[-1][3] == {"laps": True, "telemetry": True}
    png, meta = await plots.telemetry("D03", None, None, None, None, 7)
    assert meta["title"] == "Lap 7 Race Telemetry" and meta["description"].endswith("D03: 1:30.370")
    with pytest.raises(UserError, match="D03 has no lap 99 in this session."):
        await plots.telemetry("D03", None, None, None, None, 99)


async def run_telemetry(ai):
    interaction = FakeInteraction()
    cog = plots_cog.Plots()
    await cog.telemetry.callback(cog, interaction, "D01", "D02", ai_analysis=ai)
    return interaction.followup.sent[0]


async def test_ai_without_key_never_calls_gemini(session, car_data, monkeypatch):
    async def forbidden(*a):
        raise AssertionError("Gemini must not be called without a key")
    monkeypatch.setattr(gemini, "analyse_telemetry", forbidden)
    reply = await run_telemetry(True)
    assert reply["embed"].description.endswith("AI analysis isn't configured on this bot.")
    assert reply["file"].filename == "plot.png" and reply["embed"].image.url == "attachment://plot.png"
    assert "AI" not in (await run_telemetry(False))["embed"].description


async def test_ai_is_cached_truncated_and_optional(session, car_data, monkeypatch):
    ctx.config = config.Config(token="x", admin_ids=frozenset(), data_dir=ctx.config.data_dir, gemini_key="k")
    calls = []

    async def analyse(png, context):
        calls.append(context)
        return "x" * 6000
    monkeypatch.setattr(gemini, "analyse_telemetry", analyse)
    first = await run_telemetry(True)
    await run_telemetry(True)
    assert len(calls) == 1 and "2026 Chinese Grand Prix" in calls[0]
    assert "**AI Analysis**" in first["embed"].description and len(first["embed"].description) == 4096


async def test_ai_failure_still_sends_the_plot(session, car_data, monkeypatch):
    ctx.config = config.Config(token="x", admin_ids=frozenset(), data_dir=ctx.config.data_dir, gemini_key="k")

    async def boom(png, context):
        raise SourceError("Gemini", "quota")
    monkeypatch.setattr(gemini, "analyse_telemetry", boom)
    reply = await run_telemetry(True)
    assert reply["embed"].description.endswith("AI analysis is unavailable right now.") and reply["file"]


# ---------------------------------------------------------- trackdominance

def lap_positions(speed_fn, samples=200, length=5000.0):
    distance = np.linspace(0, length, samples)
    return pd.DataFrame({"Distance": distance, "Speed": speed_fn(distance / length),
                         "X": np.cos(distance / length * 6.28) * 1000, "Y": np.sin(distance / length * 6.28) * 1000})


def test_dominance_sectors_and_segment_colours():
    fast_first_half = lap_positions(lambda f: np.where(f < 0.5, 300.0, 200.0))
    steady = lap_positions(lambda f: np.full_like(f, 250.0), samples=137, length=5020.0)
    drivers = (("AAA", "#ff0000"), ("BBB", "#0000ff"))
    data = plots.compute_dominance(fast_first_half, steady, drivers, "t")
    assert len(data.sectors) == 25 and set(data.sectors) == {0, 1}
    assert data.sectors[:12] == (0,) * 12 and data.sectors[13:] == (1,) * 12
    colours = telemetry.segment_colours(data)
    fractions = fast_first_half["Distance"] / fast_first_half["Distance"].max()
    for i, colour in enumerate(colours):       # each segment takes the colour of its own mini-sector's winner
        sector = min(int(fractions[i] * 25), 24)
        assert colour == ("#ff0000", "#0000ff")[data.sectors[sector]]
    swapped = plots.compute_dominance(steady, fast_first_half, drivers[::-1], "t")
    mirrored = tuple(1 - w for w in swapped.sectors)
    assert mirrored[:12] == data.sectors[:12] and mirrored[13:] == data.sectors[13:]   # 12 is an exact tie
    assert png_size(telemetry.dominance(data)) and png_size(telemetry.circuit(plots.CircuitData(data.x, data.y, 30)))


async def test_trackdominance_command(session, car_data):
    session.results = results_frame()
    png, meta = await plots.trackdominance("D02", "D01", None, None, None)
    assert meta == {"title": "Track Dominance During Qualifying", "description": "2026 Chinese Grand Prix\nD01 vs D02"}
    assert session.calls[0][2] == "Qualifying"


# ------------------------------------------------------------------ avgpos

def entry(code, team, position, status="Finished"):
    return {"position": str(position), "status": status, "Driver": {"driverId": code.lower(), "code": code},
            "Constructor": {"constructorId": team, "name": team.title()}}


SEASON = [
    {"round": "1", "Results": [entry("AAA", "red", 1), entry("BBB", "red", 2), entry("CCC", "blue", 3),
                               entry("DDD", "blue", 4, "Engine")]},
    {"round": "2", "Results": [entry("BBB", "red", 1), entry("CCC", "blue", 2), entry("AAA", "red", 3, "Collision"),
                               entry("DDD", "blue", 4, "+1 Lap")]},
    {"round": "3", "Results": [entry("CCC", "blue", 1), entry("AAA", "red", 2, "Lapped"), entry("DDD", "blue", 3),
                               entry("BBB", "red", 4, "Did not start")]},
]


def averages(category, exclude):
    rows, grid = plots.compute_avgpos(SEASON, "Results", category, exclude)
    assert grid == 4
    return {label: round(value, 3) for label, value, _ in rows}


def test_avgpos_under_each_setting():
    assert averages("Drivers", "none") == {"AAA": 2.0, "BBB": 2.333, "CCC": 2.0, "DDD": 3.667}
    # mechanical only: DDD's engine failure is dropped; AAA's collision and BBB's DNS still count
    assert averages("Drivers", "mechanical") == {"AAA": 2.0, "BBB": 2.333, "CCC": 2.0, "DDD": 3.5}
    assert averages("Drivers", "all") == {"AAA": 1.5, "BBB": 1.5, "CCC": 2.0, "DDD": 3.5}
    assert averages("Teams", "none") == {"Red": round(13 / 6, 3), "Blue": round(17 / 6, 3)}
    rows, _ = plots.compute_avgpos(SEASON, "Results", "Drivers", "none")
    assert [r[1] for r in rows] == sorted(r[1] for r in rows)      # best first


def test_dnf_classification():
    assert plots.is_mechanical_dnf("Engine") and plots.is_mechanical_dnf("Gearbox")
    assert plots.is_dnf("Collision") and not plots.is_mechanical_dnf("Collision")
    assert not plots.is_dnf("Finished") and not plots.is_dnf("+2 Laps") and not plots.is_dnf("Lapped")


@pytest.fixture
def season_data(monkeypatch, seasons, clock):
    seasons({2026: three_race_season()})
    clock(MID_SEASON)
    box = SimpleNamespace(races=SEASON[:2])

    async def results(year):
        return box.races

    async def standings(year, round=None):
        return {"round": 2, "rows": [{"Constructor": {"constructorId": "blue"}},
                                     {"Constructor": {"constructorId": "red"}}]}
    monkeypatch.setattr(jolpica, "season_results", results)

    async def qualifying(year):
        return [{"round": r["round"], "QualifyingResults": r["Results"]} for r in box.races]
    monkeypatch.setattr(jolpica, "season_qualifying", qualifying)
    monkeypatch.setattr(jolpica, "constructor_standings", standings)
    return box


async def test_avgpos_command_cache_and_missing_colours(season_data, monkeypatch):
    calls = []
    real = plots.compute_avgpos
    monkeypatch.setattr(plots, "compute_avgpos", lambda *a: calls.append(1) or real(*a))
    png, meta = await plots.avgpos("Teams", "Race", "all", 1990)      # pre-2018: no colour data
    assert png_size(png) and meta == {"title": "Average Teams Race Finish Position 1990",
                                      "description": "DNF/DNS excluded from calculation"}
    await plots.avgpos("Teams", "Race", "all", 1990)
    assert len(calls) == 1
    season_data.races = SEASON                                         # a new round completes
    await plots.avgpos("Teams", "Race", "all", 1990)
    assert len(calls) == 2


def test_avgpos_renders_with_missing_colours():
    data = plots.BarsData("t", (("Red", 2.0, "#ffffff"), ("Blue", 3.0, "#ffffff")), 22, False, True)
    assert png_size(season.avgpos(data))


# --------------------------------------------------------------------- h2h

def pairs(exclude, races=SEASON):
    return {(team, left, right): (lw, rw)
            for team, _, left, lw, right, rw in plots.compute_h2h(races, "Results", exclude, ["blue", "red"])}


def test_h2h_scores():
    assert pairs(False) == {("blue", "CCC", "DDD"): (3, 0), ("red", "AAA", "BBB"): (2, 1)}
    # excluding retirements: blue loses round 1 (engine); red loses rounds 2 (collision) and 3 (DNS)
    assert pairs(True) == {("blue", "CCC", "DDD"): (2, 0), ("red", "AAA", "BBB"): (1, 0)}
    assert [t for t, *_ in plots.compute_h2h(SEASON, "Results", False, ["blue", "red"])] == ["blue", "red"]


def test_h2h_single_car_team_and_driver_swap():
    races = [
        {"round": "1", "Results": [entry("AAA", "red", 1), entry("BBB", "red", 2), entry("CCC", "blue", 3)]},
        {"round": "2", "Results": [entry("AAA", "red", 1), entry("EEE", "red", 2), entry("CCC", "blue", 3),
                                   entry("DDD", "blue", 4)]},
    ]
    assert pairs(False, races) == {("blue", "CCC", "DDD"): (1, 0),      # round 1 had one blue car
                                   ("red", "AAA", "BBB"): (1, 0), ("red", "AAA", "EEE"): (1, 0)}


async def test_h2h_command_and_render_without_colour_or_logo(season_data):
    png, meta = await plots.h2h("Race", True, 1990)
    assert png_size(png) and meta == {"title": "1990 Race Head to Head", "footer": "All retirements excluded"}
    png, meta = await plots.h2h("Qualifying", True, 1995)               # exclude has no effect on qualifying
    assert meta["footer"] == "Retirements included"
    data = plots.H2HData("t", (("ferrari", "Ferrari", "#ff0000", "LEC", 3, "HAM", 0),
                               ("nologo", "No Logo", "#ffffff", "AAA", 0, "BBB", 0)), True)
    assert png_size(season.h2h(data))
