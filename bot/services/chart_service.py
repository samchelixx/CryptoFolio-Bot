import io
import logging
from datetime import datetime
from typing import Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import numpy as np

logger = logging.getLogger(__name__)

DARK_BG = "#0d1117"
CARD_BG = "#161b22"
TEXT_COLOR = "#e6edf3"
GRID_COLOR = "#21262d"
GREEN = "#3fb950"
RED = "#f85149"
ACCENT = "#58a6ff"
ACCENT2 = "#bc8cff"
COLORS = ["#58a6ff", "#3fb950", "#bc8cff", "#f0883e", "#f85149", "#8b949e", "#d2a8ff", "#79c0ff", "#56d364", "#e3b341"]

plt.rcParams.update({
    "figure.facecolor": DARK_BG,
    "axes.facecolor": CARD_BG,
    "axes.edgecolor": GRID_COLOR,
    "axes.labelcolor": TEXT_COLOR,
    "text.color": TEXT_COLOR,
    "xtick.color": TEXT_COLOR,
    "ytick.color": TEXT_COLOR,
    "grid.color": GRID_COLOR,
    "grid.alpha": 0.3,
    "font.family": "sans-serif",
    "font.size": 11,
})


def _fig_to_bytes(fig: plt.Figure) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def generate_portfolio_pie(
    labels: list[str],
    values: list[float],
    currency: str = "USD",
) -> bytes:
    fig, ax = plt.subplots(figsize=(8, 6))

    total = sum(values)
    if len(labels) > 7:
        sorted_pairs = sorted(zip(values, labels), reverse=True)
        top = sorted_pairs[:7]
        other_val = sum(v for v, _ in sorted_pairs[7:])
        values = [v for v, _ in top] + [other_val]
        labels = [l for _, l in top] + ["Other"]

    colors = COLORS[:len(labels)]
    explode = [0.02] * len(labels)

    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=colors, explode=explode,
        autopct=lambda pct: f"{pct:.1f}%\n${pct * total / 100:,.0f}" if pct > 3 else "",
        pctdistance=0.75, startangle=90,
        textprops={"fontsize": 10, "color": TEXT_COLOR},
    )

    for autotext in autotexts:
        autotext.set_fontsize(8)
        autotext.set_fontweight("bold")

    ax.set_title(f"📊 Portfolio Distribution", fontsize=16, fontweight="bold", pad=20)

    centre_circle = plt.Circle((0, 0), 0.50, fc=CARD_BG)
    ax.add_artist(centre_circle)

    ax.text(0, 0.05, f"${total:,.2f}", ha="center", va="center",
            fontsize=14, fontweight="bold", color=ACCENT)
    ax.text(0, -0.12, currency.upper(), ha="center", va="center",
            fontsize=9, color="#8b949e")

    return _fig_to_bytes(fig)


def generate_price_chart(
    timestamps: list[float],
    prices: list[float],
    coin_name: str,
    symbol: str,
    currency: str = "USD",
    days: int = 30,
) -> bytes:
    fig, ax = plt.subplots(figsize=(10, 5))

    dates = [datetime.fromtimestamp(ts / 1000) for ts in timestamps]
    prices_arr = np.array(prices)

    color = GREEN if prices[-1] >= prices[0] else RED
    change_pct = ((prices[-1] - prices[0]) / prices[0]) * 100 if prices[0] > 0 else 0

    ax.plot(dates, prices_arr, color=color, linewidth=2, alpha=0.9)
    ax.fill_between(dates, prices_arr, alpha=0.15, color=color)

    max_idx = np.argmax(prices_arr)
    min_idx = np.argmin(prices_arr)
    ax.plot(dates[max_idx], prices_arr[max_idx], "^", color=GREEN, markersize=10, zorder=5)
    ax.plot(dates[min_idx], prices_arr[min_idx], "v", color=RED, markersize=10, zorder=5)
    ax.annotate(
        f"${prices_arr[max_idx]:,.2f}", (dates[max_idx], prices_arr[max_idx]),
        textcoords="offset points", xytext=(0, 12),
        ha="center", fontsize=8, color=GREEN, fontweight="bold",
    )
    ax.annotate(
        f"${prices_arr[min_idx]:,.2f}", (dates[min_idx], prices_arr[min_idx]),
        textcoords="offset points", xytext=(0, -15),
        ha="center", fontsize=8, color=RED, fontweight="bold",
    )

    ax.axhline(y=prices[-1], color=ACCENT, linestyle="--", alpha=0.4, linewidth=0.8)

    arrow = "📈" if change_pct >= 0 else "📉"
    sign = "+" if change_pct >= 0 else ""
    ax.set_title(
        f"{arrow} {coin_name} ({symbol.upper()}) — {days}D",
        fontsize=14, fontweight="bold", loc="left",
    )
    ax.text(
        0.98, 0.95, f"${prices[-1]:,.2f}  ({sign}{change_pct:.2f}%)",
        transform=ax.transAxes, ha="right", va="top",
        fontsize=12, fontweight="bold", color=color,
    )

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.grid(True, alpha=0.2)
    ax.tick_params(labelsize=9)
    fig.autofmt_xdate()

    return _fig_to_bytes(fig)


def generate_pnl_chart(
    symbols: list[str],
    pnl_values: list[float],
    pnl_percents: list[float],
) -> bytes:
    fig, ax = plt.subplots(figsize=(10, max(4, len(symbols) * 0.6 + 1)))

    colors = [GREEN if v >= 0 else RED for v in pnl_values]
    y_pos = np.arange(len(symbols))
    bars = ax.barh(y_pos, pnl_values, color=colors, height=0.5, alpha=0.85, edgecolor="none")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(symbols, fontsize=11, fontweight="bold")
    ax.invert_yaxis()

    for i, (bar, val, pct) in enumerate(zip(bars, pnl_values, pnl_percents)):
        sign = "+" if val >= 0 else ""
        text = f" {sign}${val:,.2f} ({sign}{pct:.1f}%)"
        x_pos = bar.get_width()
        ax.text(
            x_pos, i, text,
            ha="left" if val >= 0 else "right",
            va="center", fontsize=9, color=colors[i], fontweight="bold",
        )

    ax.axvline(x=0, color=TEXT_COLOR, linewidth=0.8, alpha=0.3)
    ax.set_title("💰 Profit & Loss", fontsize=14, fontweight="bold", loc="left")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.grid(True, axis="x", alpha=0.15)

    return _fig_to_bytes(fig)


def generate_candlestick(
    ohlc_data: list[list],
    coin_name: str,
    symbol: str,
    days: int = 30,
) -> bytes:
    fig, ax = plt.subplots(figsize=(12, 5))

    for candle in ohlc_data:
        ts, o, h, l, c = candle
        dt = mdates.date2num(datetime.fromtimestamp(ts / 1000))

        color = GREEN if c >= o else RED

        ax.plot([dt, dt], [l, h], color=color, linewidth=0.8, alpha=0.7)
        body_h = abs(c - o)
        body_bottom = min(o, c)
        ax.bar(
            dt, body_h, bottom=body_bottom,
            width=0.6, color=color, alpha=0.85, edgecolor="none",
        )

    ax.set_title(
        f"🕯 {coin_name} ({symbol.upper()}) — {days}D Candlestick",
        fontsize=14, fontweight="bold", loc="left",
    )

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.grid(True, alpha=0.15)
    fig.autofmt_xdate()

    return _fig_to_bytes(fig)


def generate_dca_chart(
    dates: list[datetime],
    portfolio_values: list[float],
    total_invested: list[float],
    lump_sum_values: Optional[list[float]] = None,
    coin_name: str = "",
) -> bytes:
    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(dates, portfolio_values, color=ACCENT, linewidth=2, label="DCA Portfolio", zorder=3)
    ax.plot(dates, total_invested, color="#8b949e", linewidth=1.5, linestyle="--", label="Total Invested", alpha=0.7)

    if lump_sum_values:
        ax.plot(dates, lump_sum_values, color=ACCENT2, linewidth=1.5, label="Lump Sum", alpha=0.8)

    ax.fill_between(dates, total_invested, portfolio_values, alpha=0.1,
                     color=GREEN if portfolio_values[-1] >= total_invested[-1] else RED)

    final_pnl = portfolio_values[-1] - total_invested[-1]
    sign = "+" if final_pnl >= 0 else ""
    pnl_pct = (final_pnl / total_invested[-1] * 100) if total_invested[-1] > 0 else 0
    color = GREEN if final_pnl >= 0 else RED

    ax.text(
        0.98, 0.95,
        f"DCA Result: ${portfolio_values[-1]:,.2f} ({sign}{pnl_pct:.1f}%)",
        transform=ax.transAxes, ha="right", va="top",
        fontsize=11, fontweight="bold", color=color,
    )

    ax.set_title(f"📐 DCA Simulation — {coin_name}", fontsize=14, fontweight="bold", loc="left")

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.legend(loc="upper left", fontsize=9, facecolor=CARD_BG, edgecolor=GRID_COLOR)
    ax.grid(True, alpha=0.15)
    fig.autofmt_xdate()

    return _fig_to_bytes(fig)
