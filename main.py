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

COALITIONS = [
    ("Union + AfD", ["CDU/CSU", "AfD"]),
    ("Union + SPD + Grüne", ["CDU/CSU", "SPD", "Grüne"]),
    ("Union + Grüne", ["CDU/CSU", "Grüne"]),
    ("Union + SPD", ["CDU/CSU", "SPD"]),
    ("SPD + Grüne + Linke", ["SPD", "Grüne", "Linke"]),
    ("AfD + BSW", ["AfD", "BSW"]),
]


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


def latest_averages(df: pd.DataFrame) -> dict[str, float]:
    """Latest rolling-average share per party, from the most recent polls."""
    return {
        party: float(df[party].dropna().rolling(ROLLING_WINDOW).mean().iloc[-1])
        for party in PARTIES
        if df[party].notna().any()
    }


def plot_coalitions(df: pd.DataFrame, out_path: str) -> None:
    avg = latest_averages(df)
    # Only parties clearing the 5% threshold enter parliament; a majority
    # needs half the combined share of those parties, not half of all votes.
    in_parliament = {
        p: v for p, v in avg.items() if p != "Sonstige" and v >= 5
    }
    majority = sum(in_parliament.values()) / 2

    rows = [
        (name, members)
        for name, members in COALITIONS
        if all(p in in_parliament for p in members)
    ]
    rows.sort(key=lambda r: sum(in_parliament[p] for p in r[1]))

    fig, ax = plt.subplots(figsize=(14, 0.9 * len(rows) + 2.4), dpi=200)
    fig.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    for y, (name, members) in enumerate(rows):
        left = 0.0
        for party in sorted(members, key=lambda p: -in_parliament[p]):
            share = in_parliament[party]
            ax.barh(y, share, left=left, height=0.62, color=PARTIES[party],
                    edgecolor=SURFACE, linewidth=2)
            if share >= 6:
                ax.annotate(
                    f"{party}  {share:.0f}", (left + share / 2, y),
                    ha="center", va="center", fontsize=9.5, color=SURFACE,
                )
            left += share
        total = f"{left:.1f}".replace(".", ",")
        ax.annotate(
            f"{total} %", (left, y), xytext=(8, 0), textcoords="offset points",
            va="center", fontsize=11, color=INK,
            fontweight="bold" if left >= majority else "normal",
        )
        ax.annotate(
            name, (0, y), xytext=(0, 24), textcoords="offset points",
            va="center", fontsize=10.5, color=INK,
        )

    ax.axvline(majority, color=INK, linewidth=1, linestyle=(0, (4, 3)))
    ax.annotate(
        f"Mehrheit ab {majority:.1f} %".replace(".", ","), (majority, 1.0),
        xycoords=("data", "axes fraction"), xytext=(0, 6),
        textcoords="offset points", ha="center", fontsize=9.5, color=INK,
    )

    ax.set_xlim(0, max(55.0, majority + 10))
    ax.set_ylim(-0.55, len(rows) - 0.1)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_yticks([])
    ax.grid(axis="x", color="#e6e3e0", linewidth=0.7)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#d5d1cd")
    ax.tick_params(colors=MUTED, labelsize=10, length=0)

    fig.text(
        0.03, 0.945, "Mögliche Koalitionen: rechnerische Mehrheiten",
        fontsize=16, color=INK, fontweight="bold", va="top",
    )
    fig.text(
        0.03, 0.885,
        f"Basis: 21-Tage-Durchschnitt zum {df.index.max():%d.%m.%Y} · "
        "Parteien unter 5 % bleiben unberücksichtigt · "
        "rein rechnerisch, unabhängig von politischer Wahrscheinlichkeit",
        fontsize=10, color=MUTED, va="top",
    )
    fig.text(
        0.99, 0.02,
        "Quelle: german_polls_bundestag.csv (Forsa, INSA, Infratest dimap, Verian u. a.)",
        ha="right", fontsize=8.5, color=MUTED,
    )

    fig.subplots_adjust(left=0.03, right=0.93, top=0.78, bottom=0.11)
    fig.savefig(out_path, facecolor=SURFACE)
    print(f"Wrote {out_path}")


def plot(df: pd.DataFrame, out_path: str, title: str) -> None:
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
        if not (df.index.min() < ts < df.index.max()):
            continue
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
    ymax = df[[p for p in PARTIES if p in df.columns]].max().max() + 2
    labeled_ys = spread_labels(
        [label_targets[p] for p in parties], ymax * 0.04, ymax * 0.01, ymax * 0.99
    )
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
    if (df.index.max() - df.index.min()).days > 3 * 365:
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    else:
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.grid(axis="y", color="#e6e3e0", linewidth=0.7)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#d5d1cd")
    ax.tick_params(colors=MUTED, labelsize=10, length=0)

    n_polls = len(df)
    ax.set_title(title, fontsize=16, color=INK, loc="left", pad=28, fontweight="bold")
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
    parser.add_argument("--out-recent", default="german_polls_recent.png")
    parser.add_argument("--out-coalitions", default="german_polls_coalitions.png")
    args = parser.parse_args()
    df = load_polls(args.csv)
    plot(df, args.out, "Sonntagsfrage: Wenn am Sonntag Bundestagswahl wäre …")
    plot(
        df[df.index > "2025-02-23"],
        args.out_recent,
        "Sonntagsfrage seit der Bundestagswahl 2025",
    )
    plot_coalitions(df, args.out_coalitions)


if __name__ == "__main__":
    main()
