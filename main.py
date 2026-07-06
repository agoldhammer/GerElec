"""Visualize German Bundestag polling data as a PNG chart.

Reads german_polls_bundestag.csv (one row per poll, party shares in percent)
and renders individual polls as faint dots with a 21-day rolling-average
trend line per party, in each party's conventional color.

Usage: uv run main.py [--csv PATH] [--out PATH]
"""

import argparse

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

# Conventional party colors, adjusted for contrast on a light surface and
# color-vision-deficiency separation (FDP gold vs FW orange pushed apart in
# lightness). Order = label order by recent support.
PARTIES = {
    "AfD": "#007FBF",
    "CDU/CSU": "#1a1a1a",
    "Grüne": "#46962B",
    "SPD": "#E3000F",
    "Linke": "#E6007E",
    "BSW": "#63307D",
    "Sonstige": "#75797E",
    "FDP": "#A38F00",
    "Freie Wähler": "#8F4400",
}

ELECTIONS = {
    "2017-09-24": "BTW 2017",
    "2021-09-26": "BTW 2021",
    "2025-02-23": "BTW 2025",
}

INK = "#33302e"
MUTED = "#77716c"
SURFACE = "#fcfcfb"
ROLLING_WINDOW = "21D"


def load_polls(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, parse_dates=["date"])
    return df.sort_values("date").set_index("date")


def spread_labels(positions: list[float], min_gap: float, lo: float, hi: float) -> list[float]:
    """Nudge label y-positions apart until no pair is closer than min_gap."""
    order = sorted(range(len(positions)), key=lambda i: positions[i])
    ys = [positions[i] for i in order]
    for _ in range(100):
        moved = False
        for a in range(len(ys) - 1):
            overlap = min_gap - (ys[a + 1] - ys[a])
            if overlap > 0:
                ys[a] -= overlap / 2
                ys[a + 1] += overlap / 2
                moved = True
        ys[0] = max(ys[0], lo)
        ys[-1] = min(ys[-1], hi)
        if not moved:
            break
    out = positions[:]
    for rank, i in enumerate(order):
        out[i] = ys[rank]
    return out


def plot(df: pd.DataFrame, out_path: str) -> None:
    fig, ax = plt.subplots(figsize=(14, 8), dpi=200)
    fig.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    label_targets = {}
    for party, color in PARTIES.items():
        series = df[party].dropna()
        if series.empty:
            continue
        ax.scatter(series.index, series.values, s=5, color=color, alpha=0.12, linewidths=0)
        smoothed = series.rolling(ROLLING_WINDOW).mean()
        ax.plot(smoothed.index, smoothed.values, color=color, linewidth=2, solid_capstyle="round")
        label_targets[party] = float(smoothed.iloc[-1])

    for date, name in ELECTIONS.items():
        ts = pd.Timestamp(date)
        ax.axvline(ts, color=MUTED, linewidth=0.8, linestyle=(0, (4, 4)), alpha=0.6)
        ax.annotate(
            name, (ts, 0.995), xycoords=("data", "axes fraction"),
            xytext=(0, -2), textcoords="offset points",
            ha="center", va="top", fontsize=8.5, color=MUTED,
        )

    ax.axhline(5, color=MUTED, linewidth=0.8, linestyle=(0, (1, 3)), alpha=0.8)
    ax.annotate(
        "5%-Hürde", (0.001, 5), xycoords=("axes fraction", "data"),
        xytext=(2, 3), textcoords="offset points", fontsize=8.5, color=MUTED,
    )

    # Direct labels at the right edge: party name + latest smoothed value,
    # in ink (not series color) with a colored dash tying label to line.
    parties = list(label_targets)
    ymax = max(df[list(PARTIES)].max().max() + 2, 42)
    labeled_ys = spread_labels([label_targets[p] for p in parties], 1.6, 0.5, ymax - 0.5)
    x_end = df.index.max()
    for party, y_label in zip(parties, labeled_ys):
        ax.annotate(
            "", (x_end, label_targets[party]),
            xytext=(14, 0), textcoords="offset points",
            arrowprops=dict(arrowstyle="-", color=PARTIES[party], linewidth=2,
                            shrinkA=0, shrinkB=3),
            annotation_clip=False,
        )
        ax.annotate(
            f"{party}  {label_targets[party]:.0f}", (x_end, y_label),
            xytext=(18, 0), textcoords="offset points",
            va="center", fontsize=10, color=INK,
            annotation_clip=False,
        )

    ax.set_ylim(0, ymax)
    ax.set_xlim(df.index.min(), x_end)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(axis="y", color="#e6e3e0", linewidth=0.7)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#d5d1cd")
    ax.tick_params(colors=MUTED, labelsize=10, length=0)

    n_polls = len(df)
    ax.set_title(
        "Sonntagsfrage: Wenn am Sonntag Bundestagswahl wäre …",
        fontsize=16, color=INK, loc="left", pad=28, fontweight="bold",
    )
    ax.text(
        0, 1.025,
        f"{n_polls} Umfragen, {df.index.min():%b %Y} – {df.index.max():%b %Y} · "
        f"Punkte: einzelne Umfragen · Linien: gleitender 21-Tage-Durchschnitt",
        transform=ax.transAxes, fontsize=10.5, color=MUTED,
    )
    fig.text(
        0.99, 0.01,
        "Quelle: german_polls_bundestag.csv (Forsa, INSA, Infratest dimap, Verian u. a.)",
        ha="right", fontsize=8.5, color=MUTED,
    )

    fig.subplots_adjust(left=0.045, right=0.885, top=0.895, bottom=0.07)
    fig.savefig(out_path, facecolor=SURFACE)
    print(f"Wrote {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default="german_polls_bundestag.csv")
    parser.add_argument("--out", default="german_polls_bundestag.png")
    args = parser.parse_args()
    plot(load_polls(args.csv), args.out)


if __name__ == "__main__":
    main()
